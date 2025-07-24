import os
import mimetypes
from flask import Blueprint, request, Response, render_template_string, jsonify, send_file, abort
from src.services.auth_service import AuthService
from src.models.file import File
from src.models.user import User
import logging

logger = logging.getLogger(__name__)

streaming_bp = Blueprint('streaming', __name__)
auth_service = AuthService()

@streaming_bp.route('/stream/<token>')
def stream_file(token):
    """Stream file with secure token"""
    try:
        # Verify token
        result, error = auth_service.verify_stream_token(token)
        if error:
            return render_error_page(error), 403
        
        file = result['file']
        user_id = result['user_id']
        session = result['session']
        
        # Log access
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        user_agent = request.headers.get('User-Agent')
        auth_service.log_access(user_id, file.id, 'stream', ip_address, user_agent)
        
        # Increment stream count
        file.increment_stream_count()
        
        # Check if it's a video/audio file for streaming player
        if file.is_video() or file.is_audio():
            return render_streaming_player(file, session, token)
        else:
            # For other files, redirect to download
            return send_file_response(file)
            
    except Exception as e:
        logger.error(f"Error streaming file: {e}")
        return render_error_page("Internal server error"), 500

@streaming_bp.route('/download/<token>')
def download_file(token):
    """Download file with secure token"""
    try:
        # Verify token
        result, error = auth_service.verify_download_token(token)
        if error:
            return render_error_page(error), 403
        
        file = result['file']
        user_id = result['user_id']
        
        # Log access
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        user_agent = request.headers.get('User-Agent')
        auth_service.log_access(user_id, file.id, 'download', ip_address, user_agent)
        
        # Increment download count
        file.increment_download_count()
        
        # Send file
        return send_file_response(file, as_attachment=True)
        
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return render_error_page("Internal server error"), 500

@streaming_bp.route('/api/stream/<token>/data')
def stream_file_data(token):
    """Stream file data for video/audio player"""
    try:
        # Verify token
        result, error = auth_service.verify_stream_token(token)
        if error:
            return jsonify({'error': error}), 403
        
        file = result['file']
        user_id = result['user_id']
        
        # Get range header for partial content support
        range_header = request.headers.get('Range', None)
        
        if not os.path.exists(file.file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Get file size
        file_size = os.path.getsize(file.file_path)
        
        # Handle range requests for video streaming
        if range_header:
            byte_start = 0
            byte_end = file_size - 1
            
            # Parse range header
            range_match = range_header.replace('bytes=', '').split('-')
            if range_match[0]:
                byte_start = int(range_match[0])
            if range_match[1]:
                byte_end = int(range_match[1])
            
            # Ensure valid range
            byte_start = max(0, byte_start)
            byte_end = min(file_size - 1, byte_end)
            content_length = byte_end - byte_start + 1
            
            # Create response with partial content
            def generate():
                with open(file.file_path, 'rb') as f:
                    f.seek(byte_start)
                    remaining = content_length
                    while remaining:
                        chunk_size = min(8192, remaining)
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk
            
            response = Response(
                generate(),
                206,  # Partial Content
                headers={
                    'Content-Range': f'bytes {byte_start}-{byte_end}/{file_size}',
                    'Accept-Ranges': 'bytes',
                    'Content-Length': str(content_length),
                    'Content-Type': file.mime_type or 'application/octet-stream'
                }
            )
            
        else:
            # Full file response
            response = Response(
                open(file.file_path, 'rb'),
                headers={
                    'Content-Length': str(file_size),
                    'Content-Type': file.mime_type or 'application/octet-stream',
                    'Accept-Ranges': 'bytes'
                }
            )
        
        return response
        
    except Exception as e:
        logger.error(f"Error streaming file data: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@streaming_bp.route('/api/stream/<token>/position', methods=['POST'])
def update_position(token):
    """Update current playback position"""
    try:
        # Verify token
        result, error = auth_service.verify_stream_token(token)
        if error:
            return jsonify({'error': error}), 403
        
        session = result['session']
        data = request.get_json()
        position = data.get('position', 0)
        
        # Update position
        success = auth_service.update_streaming_position(session.session_token, position)
        
        if success:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': 'Failed to update position'}), 400
            
    except Exception as e:
        logger.error(f"Error updating position: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@streaming_bp.route('/api/stream/<token>/position', methods=['GET'])
def get_position(token):
    """Get current playback position"""
    try:
        # Verify token
        result, error = auth_service.verify_stream_token(token)
        if error:
            return jsonify({'error': error}), 403
        
        session = result['session']
        position = auth_service.get_streaming_position(session.session_token)
        
        return jsonify({'position': position})
        
    except Exception as e:
        logger.error(f"Error getting position: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@streaming_bp.route('/thumbnail/<int:file_id>')
def get_thumbnail(file_id):
    """Get file thumbnail"""
    try:
        file = File.query.get(file_id)
        if not file or not file.thumbnail_path:
            abort(404)
        
        if not os.path.exists(file.thumbnail_path):
            abort(404)
        
        return send_file(file.thumbnail_path, mimetype='image/jpeg')
        
    except Exception as e:
        logger.error(f"Error getting thumbnail: {e}")
        abort(500)

def send_file_response(file, as_attachment=False):
    """Send file response with proper headers"""
    if not os.path.exists(file.file_path):
        abort(404)
    
    # Get MIME type
    mime_type = file.mime_type or mimetypes.guess_type(file.file_path)[0] or 'application/octet-stream'
    
    return send_file(
        file.file_path,
        mimetype=mime_type,
        as_attachment=as_attachment,
        download_name=file.original_filename if as_attachment else None
    )

def render_streaming_player(file, session, token):
    """Render HTML5 streaming player"""
    player_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>StreamFlix - {file.original_filename}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                background: #000;
                color: #fff;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                overflow: hidden;
            }}
            
            .player-container {{
                position: relative;
                width: 100vw;
                height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            
            .video-player, .audio-player {{
                max-width: 100%;
                max-height: 100%;
                outline: none;
            }}
            
            .video-player {{
                width: 100%;
                height: 100%;
                object-fit: contain;
            }}
            
            .audio-player {{
                width: 80%;
                max-width: 600px;
            }}
            
            .info-overlay {{
                position: absolute;
                top: 20px;
                left: 20px;
                background: rgba(0, 0, 0, 0.7);
                padding: 15px;
                border-radius: 8px;
                max-width: 300px;
                opacity: 0;
                transition: opacity 0.3s;
            }}
            
            .player-container:hover .info-overlay {{
                opacity: 1;
            }}
            
            .file-title {{
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 5px;
                word-break: break-word;
            }}
            
            .file-info {{
                font-size: 12px;
                color: #ccc;
            }}
            
            .controls-overlay {{
                position: absolute;
                bottom: 20px;
                right: 20px;
                background: rgba(0, 0, 0, 0.7);
                padding: 10px;
                border-radius: 8px;
                opacity: 0;
                transition: opacity 0.3s;
            }}
            
            .player-container:hover .controls-overlay {{
                opacity: 1;
            }}
            
            .control-btn {{
                background: #e50914;
                color: white;
                border: none;
                padding: 8px 16px;
                margin: 0 5px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
            }}
            
            .control-btn:hover {{
                background: #f40612;
            }}
            
            .audio-container {{
                text-align: center;
                padding: 40px;
            }}
            
            .audio-info {{
                margin-bottom: 30px;
            }}
            
            .audio-title {{
                font-size: 24px;
                margin-bottom: 10px;
            }}
            
            .audio-details {{
                color: #ccc;
                font-size: 14px;
            }}
            
            @media (max-width: 768px) {{
                .info-overlay {{
                    position: static;
                    opacity: 1;
                    margin-bottom: 20px;
                    max-width: none;
                }}
                
                .controls-overlay {{
                    position: static;
                    opacity: 1;
                    margin-top: 20px;
                }}
                
                .player-container {{
                    flex-direction: column;
                    padding: 20px;
                }}
                
                .video-player {{
                    height: auto;
                    max-height: 70vh;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="player-container">
            <div class="info-overlay">
                <div class="file-title">{file.original_filename}</div>
                <div class="file-info">
                    Size: {format_file_size(file.file_size)}<br>
                    Type: {file.file_type.value.title()}<br>
                    Duration: {format_duration(file.duration) if file.duration else 'Unknown'}
                </div>
            </div>
            
            {'<video class="video-player" controls preload="metadata" id="mediaPlayer">' if file.is_video() else '<div class="audio-container"><div class="audio-info"><div class="audio-title">' + file.original_filename + '</div><div class="audio-details">Duration: ' + (format_duration(file.duration) if file.duration else 'Unknown') + '</div></div><audio class="audio-player" controls preload="metadata" id="mediaPlayer">'}
                <source src="/api/stream/{token}/data" type="{file.mime_type}">
                Your browser does not support the {'video' if file.is_video() else 'audio'} tag.
            {'</video>' if file.is_video() else '</audio></div>'}
            
            <div class="controls-overlay">
                <button class="control-btn" onclick="toggleFullscreen()">
                    {'Fullscreen' if file.is_video() else 'Focus'}
                </button>
                <button class="control-btn" onclick="downloadFile()">Download</button>
            </div>
        </div>
        
        <script>
            const player = document.getElementById('mediaPlayer');
            const token = '{token}';
            let positionUpdateInterval;
            
            // Load saved position
            fetch(`/api/stream/${{token}}/position`)
                .then(response => response.json())
                .then(data => {{
                    if (data.position > 0) {{
                        player.currentTime = data.position;
                    }}
                }})
                .catch(console.error);
            
            // Save position periodically
            player.addEventListener('loadedmetadata', () => {{
                positionUpdateInterval = setInterval(() => {{
                    if (!player.paused) {{
                        fetch(`/api/stream/${{token}}/position`, {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json'
                            }},
                            body: JSON.stringify({{
                                position: player.currentTime
                            }})
                        }}).catch(console.error);
                    }}
                }}, 5000); // Update every 5 seconds
            }});
            
            // Clean up interval
            window.addEventListener('beforeunload', () => {{
                if (positionUpdateInterval) {{
                    clearInterval(positionUpdateInterval);
                }}
            }});
            
            function toggleFullscreen() {{
                if (document.fullscreenElement) {{
                    document.exitFullscreen();
                }} else {{
                    document.documentElement.requestFullscreen();
                }}
            }}
            
            function downloadFile() {{
                // Create download link
                const downloadToken = '{token}'.replace('/stream/', '/download/');
                window.open(`/download/${{downloadToken}}`, '_blank');
            }}
            
            // Keyboard shortcuts
            document.addEventListener('keydown', (e) => {{
                switch(e.code) {{
                    case 'Space':
                        e.preventDefault();
                        if (player.paused) {{
                            player.play();
                        }} else {{
                            player.pause();
                        }}
                        break;
                    case 'ArrowLeft':
                        e.preventDefault();
                        player.currentTime = Math.max(0, player.currentTime - 10);
                        break;
                    case 'ArrowRight':
                        e.preventDefault();
                        player.currentTime = Math.min(player.duration, player.currentTime + 10);
                        break;
                    case 'KeyF':
                        e.preventDefault();
                        toggleFullscreen();
                        break;
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    return player_html

def render_error_page(error_message):
    """Render error page"""
    error_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>StreamFlix - Error</title>
        <style>
            body {{
                background: #000;
                color: #fff;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
            }}
            
            .error-container {{
                text-align: center;
                max-width: 500px;
                padding: 40px;
            }}
            
            .error-icon {{
                font-size: 64px;
                margin-bottom: 20px;
            }}
            
            .error-title {{
                font-size: 24px;
                margin-bottom: 10px;
                color: #e50914;
            }}
            
            .error-message {{
                font-size: 16px;
                color: #ccc;
                margin-bottom: 30px;
            }}
            
            .back-btn {{
                background: #e50914;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                text-decoration: none;
                display: inline-block;
            }}
            
            .back-btn:hover {{
                background: #f40612;
            }}
        </style>
    </head>
    <body>
        <div class="error-container">
            <div class="error-icon">🚫</div>
            <div class="error-title">Access Denied</div>
            <div class="error-message">{error_message}</div>
            <a href="#" onclick="window.close()" class="back-btn">Close</a>
        </div>
    </body>
    </html>
    """
    
    return error_html

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def format_duration(duration_seconds):
    """Format duration in human readable format"""
    if not duration_seconds:
        return "Unknown"
    
    hours = int(duration_seconds // 3600)
    minutes = int((duration_seconds % 3600) // 60)
    seconds = int(duration_seconds % 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

