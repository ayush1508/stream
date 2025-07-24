from flask import Blueprint, request, jsonify
from src.models.user import db, User, UserRole
from src.models.file import File, FileType
from src.models.access import AccessRequest, AccessLog, StreamingSession, RequestStatus
from src.services.auth_service import AuthService
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)
auth_service = AuthService()

def require_admin(f):
    """Decorator to require admin authentication"""
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        result, error = auth_service.verify_admin_token(token)
        
        if error:
            return jsonify({'error': error}), 403
        
        request.admin_user_id = result['user_id']
        return f(*args, **kwargs)
    
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin_bp.route('/login', methods=['POST'])
def admin_login():
    """Admin login endpoint"""
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        
        if not telegram_id:
            return jsonify({'error': 'Telegram ID required'}), 400
        
        # Find user
        user = User.query.filter_by(telegram_id=telegram_id).first()
        if not user or not user.is_admin():
            return jsonify({'error': 'Invalid admin credentials'}), 403
        
        # Generate admin token
        token = auth_service.generate_admin_token(user.id)
        if not token:
            return jsonify({'error': 'Failed to generate token'}), 500
        
        return jsonify({
            'token': token,
            'user': user.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Admin login error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/users', methods=['GET'])
@require_admin
def get_users():
    """Get all users"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        
        query = User.query
        
        if search:
            query = query.filter(
                db.or_(
                    User.username.contains(search),
                    User.first_name.contains(search),
                    User.last_name.contains(search)
                )
            )
        
        users = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'users': [user.to_dict() for user in users.items],
            'total': users.total,
            'pages': users.pages,
            'current_page': page
        })
        
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_admin
def update_user(user_id):
    """Update user details"""
    try:
        data = request.get_json()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Update allowed fields
        if 'is_approved' in data:
            user.is_approved = data['is_approved']
        
        if 'role' in data:
            if data['role'] in ['user', 'admin']:
                user.role = UserRole.ADMIN if data['role'] == 'admin' else UserRole.USER
        
        db.session.commit()
        
        return jsonify({
            'message': 'User updated successfully',
            'user': user.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@require_admin
def delete_user(user_id):
    """Delete user (soft delete by revoking access)"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if user.is_admin():
            return jsonify({'error': 'Cannot delete admin user'}), 400
        
        # Revoke access instead of deleting
        user.is_approved = False
        db.session.commit()
        
        return jsonify({'message': 'User access revoked successfully'})
        
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/access-requests', methods=['GET'])
@require_admin
def get_access_requests():
    """Get access requests"""
    try:
        status = request.args.get('status', 'pending')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = AccessRequest.query
        
        if status != 'all':
            status_enum = RequestStatus.PENDING if status == 'pending' else \
                         RequestStatus.APPROVED if status == 'approved' else \
                         RequestStatus.REJECTED
            query = query.filter_by(status=status_enum)
        
        requests = query.order_by(AccessRequest.requested_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        result = []
        for req in requests.items:
            req_dict = req.to_dict()
            req_dict['user'] = req.user.to_dict()
            result.append(req_dict)
        
        return jsonify({
            'requests': result,
            'total': requests.total,
            'pages': requests.pages,
            'current_page': page
        })
        
    except Exception as e:
        logger.error(f"Error getting access requests: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/access-requests/<int:request_id>/approve', methods=['POST'])
@require_admin
def approve_access_request(request_id):
    """Approve access request"""
    try:
        access_request = AccessRequest.query.get(request_id)
        
        if not access_request:
            return jsonify({'error': 'Request not found'}), 404
        
        if access_request.status != RequestStatus.PENDING:
            return jsonify({'error': 'Request already processed'}), 400
        
        # Approve user
        user = User.query.get(access_request.user_id)
        user.is_approved = True
        
        # Update request
        access_request.status = RequestStatus.APPROVED
        access_request.processed_at = datetime.utcnow()
        access_request.processed_by = request.admin_user_id
        
        db.session.commit()
        
        return jsonify({
            'message': 'Access request approved successfully',
            'request': access_request.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error approving access request: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/access-requests/<int:request_id>/reject', methods=['POST'])
@require_admin
def reject_access_request(request_id):
    """Reject access request"""
    try:
        data = request.get_json()
        admin_notes = data.get('notes', '')
        
        access_request = AccessRequest.query.get(request_id)
        
        if not access_request:
            return jsonify({'error': 'Request not found'}), 404
        
        if access_request.status != RequestStatus.PENDING:
            return jsonify({'error': 'Request already processed'}), 400
        
        # Update request
        access_request.status = RequestStatus.REJECTED
        access_request.processed_at = datetime.utcnow()
        access_request.processed_by = request.admin_user_id
        access_request.admin_notes = admin_notes
        
        db.session.commit()
        
        return jsonify({
            'message': 'Access request rejected successfully',
            'request': access_request.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error rejecting access request: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/files', methods=['GET'])
@require_admin
def get_files():
    """Get all files"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        file_type = request.args.get('type', '')
        uploader_id = request.args.get('uploader_id', type=int)
        
        query = File.query
        
        if search:
            query = query.filter(File.original_filename.contains(search))
        
        if file_type:
            try:
                file_type_enum = FileType(file_type)
                query = query.filter_by(file_type=file_type_enum)
            except ValueError:
                pass
        
        if uploader_id:
            query = query.filter_by(uploader_id=uploader_id)
        
        files = query.order_by(File.uploaded_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        result = []
        for file in files.items:
            file_dict = file.to_dict()
            file_dict['uploader'] = file.uploader.to_dict()
            result.append(file_dict)
        
        return jsonify({
            'files': result,
            'total': files.total,
            'pages': files.pages,
            'current_page': page
        })
        
    except Exception as e:
        logger.error(f"Error getting files: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/files/<int:file_id>', methods=['DELETE'])
@require_admin
def delete_file(file_id):
    """Delete file"""
    try:
        from src.services.file_service import FileService
        file_service = FileService()
        
        admin_user = User.query.get(request.admin_user_id)
        success, message = file_service.delete_file(file_id, admin_user.id)
        
        if success:
            return jsonify({'message': message})
        else:
            return jsonify({'error': message}), 400
        
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/stats', methods=['GET'])
@require_admin
def get_stats():
    """Get system statistics"""
    try:
        # Basic counts
        total_users = User.query.count()
        approved_users = User.query.filter_by(is_approved=True).count()
        admin_users = User.query.filter_by(role=UserRole.ADMIN).count()
        
        total_files = File.query.count()
        total_downloads = db.session.query(db.func.sum(File.download_count)).scalar() or 0
        total_streams = db.session.query(db.func.sum(File.stream_count)).scalar() or 0
        
        pending_requests = AccessRequest.query.filter_by(status=RequestStatus.PENDING).count()
        
        # File type breakdown
        file_types = db.session.query(
            File.file_type,
            db.func.count(File.id).label('count'),
            db.func.sum(File.file_size).label('total_size')
        ).group_by(File.file_type).all()
        
        file_type_stats = {}
        for file_type, count, total_size in file_types:
            file_type_stats[file_type.value] = {
                'count': count,
                'total_size': total_size or 0
            }
        
        # Recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_uploads = File.query.filter(File.uploaded_at >= week_ago).count()
        recent_users = User.query.filter(User.created_at >= week_ago).count()
        
        # Top uploaders
        top_uploaders = db.session.query(
            User.id,
            User.username,
            User.first_name,
            db.func.count(File.id).label('file_count'),
            db.func.sum(File.file_size).label('total_size')
        ).join(File).group_by(User.id).order_by(
            db.func.count(File.id).desc()
        ).limit(10).all()
        
        top_uploaders_list = []
        for user_id, username, first_name, file_count, total_size in top_uploaders:
            top_uploaders_list.append({
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'file_count': file_count,
                'total_size': total_size or 0
            })
        
        # Most popular files
        popular_files = File.query.order_by(
            (File.download_count + File.stream_count).desc()
        ).limit(10).all()
        
        popular_files_list = []
        for file in popular_files:
            file_dict = file.to_dict()
            file_dict['uploader'] = file.uploader.to_dict()
            file_dict['total_access'] = file.download_count + file.stream_count
            popular_files_list.append(file_dict)
        
        return jsonify({
            'overview': {
                'total_users': total_users,
                'approved_users': approved_users,
                'admin_users': admin_users,
                'total_files': total_files,
                'total_downloads': total_downloads,
                'total_streams': total_streams,
                'pending_requests': pending_requests
            },
            'file_types': file_type_stats,
            'recent_activity': {
                'recent_uploads': recent_uploads,
                'recent_users': recent_users
            },
            'top_uploaders': top_uploaders_list,
            'popular_files': popular_files_list
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/access-logs', methods=['GET'])
@require_admin
def get_access_logs():
    """Get access logs"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        file_id = request.args.get('file_id', type=int)
        user_id = request.args.get('user_id', type=int)
        action = request.args.get('action', '')
        
        query = AccessLog.query
        
        if file_id:
            query = query.filter_by(file_id=file_id)
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        if action:
            query = query.filter_by(action=action)
        
        logs = query.order_by(AccessLog.accessed_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        result = []
        for log in logs.items:
            log_dict = log.to_dict()
            log_dict['user'] = log.user.to_dict()
            log_dict['file'] = log.file.to_dict()
            result.append(log_dict)
        
        return jsonify({
            'logs': result,
            'total': logs.total,
            'pages': logs.pages,
            'current_page': page
        })
        
    except Exception as e:
        logger.error(f"Error getting access logs: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/streaming-sessions', methods=['GET'])
@require_admin
def get_streaming_sessions():
    """Get active streaming sessions"""
    try:
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        
        query = StreamingSession.query
        
        if active_only:
            query = query.filter_by(is_active=True).filter(
                StreamingSession.expires_at > datetime.utcnow()
            )
        
        sessions = query.order_by(StreamingSession.started_at.desc()).limit(100).all()
        
        result = []
        for session in sessions:
            session_dict = session.to_dict()
            session_dict['user'] = session.user.to_dict()
            session_dict['file'] = session.file.to_dict()
            result.append(session_dict)
        
        return jsonify({'sessions': result})
        
    except Exception as e:
        logger.error(f"Error getting streaming sessions: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/streaming-sessions/<session_token>/revoke', methods=['POST'])
@require_admin
def revoke_streaming_session(session_token):
    """Revoke streaming session"""
    try:
        success = auth_service.revoke_streaming_session(session_token)
        
        if success:
            return jsonify({'message': 'Session revoked successfully'})
        else:
            return jsonify({'error': 'Session not found or already inactive'}), 404
        
    except Exception as e:
        logger.error(f"Error revoking session: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/cleanup', methods=['POST'])
@require_admin
def cleanup_system():
    """Clean up expired sessions and logs"""
    try:
        # Clean up expired sessions
        auth_service.cleanup_expired_sessions()
        
        # Clean up old access logs (older than 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        old_logs = AccessLog.query.filter(AccessLog.accessed_at < thirty_days_ago).delete()
        
        db.session.commit()
        
        return jsonify({
            'message': 'System cleanup completed',
            'deleted_logs': old_logs
        })
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

