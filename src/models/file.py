from src.models.user import db
from datetime import datetime
from enum import Enum
import os

class FileType(Enum):
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"
    DOCUMENT = "document"
    IMAGE = "image"
    ARCHIVE = "archive"
    APK = "apk"
    OTHER = "other"

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    file_type = db.Column(db.Enum(FileType), nullable=False)
    mime_type = db.Column(db.String(100), nullable=True)
    
    # Video/Audio specific fields
    duration = db.Column(db.Float, nullable=True)  # in seconds
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    thumbnail_path = db.Column(db.String(500), nullable=True)
    
    # Upload info
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Access control
    is_public = db.Column(db.Boolean, default=False)
    password_protected = db.Column(db.Boolean, default=False)
    password_hash = db.Column(db.String(255), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # Stats
    download_count = db.Column(db.Integer, default=0)
    stream_count = db.Column(db.Integer, default=0)
    last_accessed = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    access_logs = db.relationship('AccessLog', backref='file', lazy=True)
    streaming_sessions = db.relationship('StreamingSession', backref='file', lazy=True)

    def __repr__(self):
        return f'<File {self.original_filename}>'

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'file_type': self.file_type.value,
            'mime_type': self.mime_type,
            'duration': self.duration,
            'width': self.width,
            'height': self.height,
            'uploader_id': self.uploader_id,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'is_public': self.is_public,
            'password_protected': self.password_protected,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'download_count': self.download_count,
            'stream_count': self.stream_count,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None
        }

    def get_file_extension(self):
        return os.path.splitext(self.original_filename)[1].lower()

    def is_video(self):
        return self.file_type == FileType.VIDEO

    def is_audio(self):
        return self.file_type == FileType.AUDIO

    def is_expired(self):
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False

    def increment_download_count(self):
        self.download_count += 1
        self.last_accessed = datetime.utcnow()
        db.session.commit()

    def increment_stream_count(self):
        self.stream_count += 1
        self.last_accessed = datetime.utcnow()
        db.session.commit()

