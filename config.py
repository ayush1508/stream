import os
from datetime import timedelta

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'streamflix-secret-key-change-in-production'
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///streamflix.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Telegram Bot configuration
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN') or 'YOUR_BOT_TOKEN_HERE'
    TELEGRAM_WEBHOOK_URL = os.environ.get('TELEGRAM_WEBHOOK_URL')
    
    # File storage configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024  # 2GB max file size
    
    # Security configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    # Streaming configuration
    STREAM_CHUNK_SIZE = 8192
    STREAM_TOKEN_EXPIRES = timedelta(hours=6)
    DOWNLOAD_TOKEN_EXPIRES = timedelta(hours=1)
    
    # File processing configuration
    FFMPEG_PATH = os.environ.get('FFMPEG_PATH') or 'ffmpeg'
    THUMBNAIL_SIZE = (320, 240)
    
    # Admin configuration
    ADMIN_TELEGRAM_IDS = [
        int(id.strip()) for id in os.environ.get('ADMIN_TELEGRAM_IDS', '').split(',') 
        if id.strip().isdigit()
    ]
    
    # CORS configuration
    CORS_ORIGINS = ['*']  # Allow all origins for development
    
    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    
class ProductionConfig(Config):
    DEBUG = False
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Log to stderr
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

