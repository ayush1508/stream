import os
import magic
import hashlib
import ffmpeg
from datetime import datetime
from pathlib import Path
from PIL import Image
from src.models.user import db
from src.models.file import File, FileType
from telegram import Update
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)

class FileService:
    def __init__(self):
        self.upload_base_path = "uploads"
        self.thumbnail_base_path = "thumbnails"
        self.ensure_directories()
    
    def ensure_directories(self):
        """Ensure upload and thumbnail directories exist"""
        os.makedirs(self.upload_base_path, exist_ok=True)
        os.makedirs(self.thumbnail_base_path, exist_ok=True)
    
    async def process_upload(self, file_obj, user, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process file upload from Telegram"""
        try:
            # Get file info
            file_id = file_obj.file_id
            filename = file_obj.file_name or f"file_{file_id}"
            file_size = file_obj.file_size
            
            # Download file from Telegram
            telegram_file = await context.bot.get_file(file_id)
            
            # Generate unique filename
            file_hash = hashlib.md5(f"{file_id}_{user.id}_{datetime.now().isoformat()}".encode()).hexdigest()
            file_extension = os.path.splitext(filename)[1].lower()
            unique_filename = f"{file_hash}{file_extension}"
            
            # Create user directory structure
            user_dir = self.create_user_directory(user)
            file_path = os.path.join(user_dir, unique_filename)
            
            # Download file
            await telegram_file.download_to_drive(file_path)
            
            # Detect file type and MIME type
            file_type = self.detect_file_type(file_path, filename)
            mime_type = self.get_mime_type(file_path)
            
            # Process file based on type
            duration = None
            width = None
            height = None
            thumbnail_path = None
            
            if file_type in [FileType.VIDEO, FileType.AUDIO]:
                duration, width, height = self.get_media_info(file_path)
                if file_type == FileType.VIDEO:
                    thumbnail_path = await self.generate_thumbnail(file_path, unique_filename)
            elif file_type == FileType.IMAGE:
                width, height = self.get_image_dimensions(file_path)
                thumbnail_path = await self.generate_image_thumbnail(file_path, unique_filename)
            
            # Create file record in database
            file_record = File(
                filename=unique_filename,
                original_filename=filename,
                file_path=file_path,
                file_size=file_size,
                file_type=file_type,
                mime_type=mime_type,
                duration=duration,
                width=width,
                height=height,
                thumbnail_path=thumbnail_path,
                uploader_id=user.id
            )
            
            db.session.add(file_record)
            db.session.commit()
            
            logger.info(f"File uploaded successfully: {filename} by user {user.id}")
            return file_record
            
        except Exception as e:
            logger.error(f"Error processing file upload: {e}")
            db.session.rollback()
            return None
    
    def create_user_directory(self, user):
        """Create directory structure for user files"""
        # Create directory: uploads/username_userid/YYYY/MM/
        username = user.username or f"user_{user.id}"
        current_date = datetime.now()
        
        user_dir = os.path.join(
            self.upload_base_path,
            f"{username}_{user.id}",
            str(current_date.year),
            f"{current_date.month:02d}"
        )
        
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    def detect_file_type(self, file_path, filename):
        """Detect file type based on extension and content"""
        extension = os.path.splitext(filename)[1].lower()
        
        # Video extensions
        video_extensions = ['.mp4', '.mkv', '.webm', '.avi', '.mov', '.wmv', '.flv', '.m4v']
        if extension in video_extensions:
            return FileType.VIDEO
        
        # Audio extensions
        audio_extensions = ['.mp3', '.aac', '.wav', '.flac', '.ogg', '.m4a', '.wma']
        if extension in audio_extensions:
            return FileType.AUDIO
        
        # Subtitle extensions
        subtitle_extensions = ['.srt', '.vtt', '.ass', '.ssa', '.sub']
        if extension in subtitle_extensions:
            return FileType.SUBTITLE
        
        # Document extensions
        document_extensions = ['.pdf', '.doc', '.docx', '.txt', '.epub', '.rtf', '.odt']
        if extension in document_extensions:
            return FileType.DOCUMENT
        
        # Image extensions
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff']
        if extension in image_extensions:
            return FileType.IMAGE
        
        # Archive extensions
        archive_extensions = ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2']
        if extension in archive_extensions:
            return FileType.ARCHIVE
        
        # APK files
        if extension == '.apk':
            return FileType.APK
        
        return FileType.OTHER
    
    def get_mime_type(self, file_path):
        """Get MIME type of file"""
        try:
            mime = magic.Magic(mime=True)
            return mime.from_file(file_path)
        except Exception as e:
            logger.warning(f"Could not determine MIME type for {file_path}: {e}")
            return "application/octet-stream"
    
    def get_media_info(self, file_path):
        """Get media information using ffmpeg"""
        try:
            probe = ffmpeg.probe(file_path)
            
            # Get duration
            duration = float(probe['format']['duration'])
            
            # Get video dimensions
            width = None
            height = None
            
            for stream in probe['streams']:
                if stream['codec_type'] == 'video':
                    width = stream.get('width')
                    height = stream.get('height')
                    break
            
            return duration, width, height
            
        except Exception as e:
            logger.warning(f"Could not get media info for {file_path}: {e}")
            return None, None, None
    
    def get_image_dimensions(self, file_path):
        """Get image dimensions"""
        try:
            with Image.open(file_path) as img:
                return img.width, img.height
        except Exception as e:
            logger.warning(f"Could not get image dimensions for {file_path}: {e}")
            return None, None
    
    async def generate_thumbnail(self, video_path, unique_filename):
        """Generate thumbnail for video file"""
        try:
            thumbnail_filename = f"thumb_{os.path.splitext(unique_filename)[0]}.jpg"
            thumbnail_path = os.path.join(self.thumbnail_base_path, thumbnail_filename)
            
            # Generate thumbnail at 10% of video duration
            (
                ffmpeg
                .input(video_path, ss='00:00:10')
                .output(thumbnail_path, vframes=1, s='320x240')
                .overwrite_output()
                .run(quiet=True)
            )
            
            return thumbnail_path
            
        except Exception as e:
            logger.warning(f"Could not generate thumbnail for {video_path}: {e}")
            return None
    
    async def generate_image_thumbnail(self, image_path, unique_filename):
        """Generate thumbnail for image file"""
        try:
            thumbnail_filename = f"thumb_{os.path.splitext(unique_filename)[0]}.jpg"
            thumbnail_path = os.path.join(self.thumbnail_base_path, thumbnail_filename)
            
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Create thumbnail
                img.thumbnail((320, 240), Image.Resampling.LANCZOS)
                img.save(thumbnail_path, 'JPEG', quality=85)
            
            return thumbnail_path
            
        except Exception as e:
            logger.warning(f"Could not generate image thumbnail for {image_path}: {e}")
            return None
    
    def organize_files_by_type(self, user_id):
        """Get files organized by type for a user"""
        files = File.query.filter_by(uploader_id=user_id).all()
        
        organized = {
            'videos': [],
            'audio': [],
            'documents': [],
            'images': [],
            'archives': [],
            'other': []
        }
        
        for file in files:
            if file.file_type == FileType.VIDEO:
                organized['videos'].append(file)
            elif file.file_type == FileType.AUDIO:
                organized['audio'].append(file)
            elif file.file_type == FileType.DOCUMENT:
                organized['documents'].append(file)
            elif file.file_type == FileType.IMAGE:
                organized['images'].append(file)
            elif file.file_type == FileType.ARCHIVE:
                organized['archives'].append(file)
            else:
                organized['other'].append(file)
        
        return organized
    
    def get_file_stats(self, file_id):
        """Get statistics for a specific file"""
        file = File.query.get(file_id)
        if not file:
            return None
        
        return {
            'file': file.to_dict(),
            'total_downloads': file.download_count,
            'total_streams': file.stream_count,
            'last_accessed': file.last_accessed,
            'uploader': file.uploader.username or file.uploader.first_name
        }
    
    def search_files(self, query, user_id=None, file_type=None, limit=20):
        """Search files with filters"""
        query_obj = File.query
        
        # Filter by filename
        if query:
            query_obj = query_obj.filter(File.original_filename.contains(query))
        
        # Filter by uploader
        if user_id:
            query_obj = query_obj.filter(File.uploader_id == user_id)
        
        # Filter by file type
        if file_type:
            query_obj = query_obj.filter(File.file_type == file_type)
        
        # Order by upload date (newest first)
        query_obj = query_obj.order_by(File.uploaded_at.desc())
        
        return query_obj.limit(limit).all()
    
    def delete_file(self, file_id, user_id):
        """Delete a file (only by uploader or admin)"""
        file = File.query.get(file_id)
        if not file:
            return False, "File not found"
        
        # Check permissions
        user = User.query.get(user_id)
        if file.uploader_id != user_id and not user.is_admin():
            return False, "Permission denied"
        
        try:
            # Delete physical file
            if os.path.exists(file.file_path):
                os.remove(file.file_path)
            
            # Delete thumbnail
            if file.thumbnail_path and os.path.exists(file.thumbnail_path):
                os.remove(file.thumbnail_path)
            
            # Delete database record
            db.session.delete(file)
            db.session.commit()
            
            logger.info(f"File deleted: {file.original_filename} by user {user_id}")
            return True, "File deleted successfully"
            
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {e}")
            db.session.rollback()
            return False, f"Error deleting file: {str(e)}"
    
    def get_user_storage_stats(self, user_id):
        """Get storage statistics for a user"""
        files = File.query.filter_by(uploader_id=user_id).all()
        
        total_size = sum(file.file_size for file in files)
        file_count = len(files)
        
        type_stats = {}
        for file in files:
            file_type = file.file_type.value
            if file_type not in type_stats:
                type_stats[file_type] = {'count': 0, 'size': 0}
            type_stats[file_type]['count'] += 1
            type_stats[file_type]['size'] += file.file_size
        
        return {
            'total_files': file_count,
            'total_size': total_size,
            'type_breakdown': type_stats
        }

