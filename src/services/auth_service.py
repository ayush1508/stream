import jwt
import secrets
from datetime import datetime, timedelta
from src.models.user import db
from src.models.file import File
from src.models.access import StreamingSession, AccessLog
from config import Config
import logging

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        self.jwt_secret = Config.JWT_SECRET_KEY
        self.stream_expires = Config.STREAM_TOKEN_EXPIRES
        self.download_expires = Config.DOWNLOAD_TOKEN_EXPIRES
    
    def generate_stream_link(self, file_id, user_id, base_url="http://localhost:5000"):
        """Generate secure streaming link with JWT token"""
        try:
            # Create streaming session
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + self.stream_expires
            
            streaming_session = StreamingSession(
                user_id=user_id,
                file_id=file_id,
                session_token=session_token,
                expires_at=expires_at
            )
            
            db.session.add(streaming_session)
            db.session.commit()
            
            # Generate JWT token
            payload = {
                'file_id': file_id,
                'user_id': user_id,
                'session_token': session_token,
                'type': 'stream',
                'exp': expires_at,
                'iat': datetime.utcnow()
            }
            
            token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
            
            # Return streaming URL
            return f"{base_url}/stream/{token}"
            
        except Exception as e:
            logger.error(f"Error generating stream link: {e}")
            db.session.rollback()
            return None
    
    def generate_download_link(self, file_id, user_id, base_url="http://localhost:5000"):
        """Generate secure download link with JWT token"""
        try:
            expires_at = datetime.utcnow() + self.download_expires
            
            # Generate JWT token
            payload = {
                'file_id': file_id,
                'user_id': user_id,
                'type': 'download',
                'exp': expires_at,
                'iat': datetime.utcnow()
            }
            
            token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
            
            # Return download URL
            return f"{base_url}/download/{token}"
            
        except Exception as e:
            logger.error(f"Error generating download link: {e}")
            return None
    
    def verify_stream_token(self, token):
        """Verify streaming token and return session info"""
        try:
            # Decode JWT token
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            
            if payload.get('type') != 'stream':
                return None, "Invalid token type"
            
            file_id = payload.get('file_id')
            user_id = payload.get('user_id')
            session_token = payload.get('session_token')
            
            # Verify streaming session
            session = StreamingSession.query.filter_by(
                session_token=session_token,
                file_id=file_id,
                user_id=user_id,
                is_active=True
            ).first()
            
            if not session:
                return None, "Invalid or expired session"
            
            if session.is_expired():
                session.is_active = False
                db.session.commit()
                return None, "Session expired"
            
            # Get file info
            file = File.query.get(file_id)
            if not file:
                return None, "File not found"
            
            return {
                'file': file,
                'user_id': user_id,
                'session': session
            }, None
            
        except jwt.ExpiredSignatureError:
            return None, "Token expired"
        except jwt.InvalidTokenError:
            return None, "Invalid token"
        except Exception as e:
            logger.error(f"Error verifying stream token: {e}")
            return None, "Token verification failed"
    
    def verify_download_token(self, token):
        """Verify download token and return file info"""
        try:
            # Decode JWT token
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            
            if payload.get('type') != 'download':
                return None, "Invalid token type"
            
            file_id = payload.get('file_id')
            user_id = payload.get('user_id')
            
            # Get file info
            file = File.query.get(file_id)
            if not file:
                return None, "File not found"
            
            return {
                'file': file,
                'user_id': user_id
            }, None
            
        except jwt.ExpiredSignatureError:
            return None, "Token expired"
        except jwt.InvalidTokenError:
            return None, "Invalid token"
        except Exception as e:
            logger.error(f"Error verifying download token: {e}")
            return None, "Token verification failed"
    
    def log_access(self, user_id, file_id, action, ip_address=None, user_agent=None, success=True, error_message=None):
        """Log file access for monitoring"""
        try:
            access_log = AccessLog(
                user_id=user_id,
                file_id=file_id,
                action=action,
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                error_message=error_message
            )
            
            db.session.add(access_log)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error logging access: {e}")
            db.session.rollback()
    
    def update_streaming_position(self, session_token, position):
        """Update current position in streaming session"""
        try:
            session = StreamingSession.query.filter_by(session_token=session_token).first()
            if session and session.is_active and not session.is_expired():
                session.update_position(position)
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error updating streaming position: {e}")
            return False
    
    def get_streaming_position(self, session_token):
        """Get current position in streaming session"""
        try:
            session = StreamingSession.query.filter_by(session_token=session_token).first()
            if session and session.is_active and not session.is_expired():
                return session.last_position
            return 0.0
            
        except Exception as e:
            logger.error(f"Error getting streaming position: {e}")
            return 0.0
    
    def revoke_streaming_session(self, session_token):
        """Revoke a streaming session"""
        try:
            session = StreamingSession.query.filter_by(session_token=session_token).first()
            if session:
                session.is_active = False
                db.session.commit()
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error revoking streaming session: {e}")
            db.session.rollback()
            return False
    
    def cleanup_expired_sessions(self):
        """Clean up expired streaming sessions"""
        try:
            expired_sessions = StreamingSession.query.filter(
                StreamingSession.expires_at < datetime.utcnow(),
                StreamingSession.is_active == True
            ).all()
            
            for session in expired_sessions:
                session.is_active = False
            
            db.session.commit()
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            db.session.rollback()
    
    def get_user_active_sessions(self, user_id):
        """Get all active streaming sessions for a user"""
        try:
            sessions = StreamingSession.query.filter_by(
                user_id=user_id,
                is_active=True
            ).filter(
                StreamingSession.expires_at > datetime.utcnow()
            ).all()
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return []
    
    def generate_password_protected_link(self, file_id, user_id, password, link_type='stream'):
        """Generate password-protected link"""
        try:
            expires_at = datetime.utcnow() + (self.stream_expires if link_type == 'stream' else self.download_expires)
            
            # Hash password for storage
            import hashlib
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            payload = {
                'file_id': file_id,
                'user_id': user_id,
                'type': link_type,
                'password_protected': True,
                'password_hash': password_hash,
                'exp': expires_at,
                'iat': datetime.utcnow()
            }
            
            token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
            
            base_url = "http://localhost:5000"
            endpoint = 'stream' if link_type == 'stream' else 'download'
            
            return f"{base_url}/{endpoint}/{token}"
            
        except Exception as e:
            logger.error(f"Error generating password-protected link: {e}")
            return None
    
    def verify_password_protected_token(self, token, password):
        """Verify password-protected token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            
            if not payload.get('password_protected'):
                return None, "Token is not password protected"
            
            # Verify password
            import hashlib
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            if password_hash != payload.get('password_hash'):
                return None, "Invalid password"
            
            # Return file info if password is correct
            file_id = payload.get('file_id')
            user_id = payload.get('user_id')
            
            file = File.query.get(file_id)
            if not file:
                return None, "File not found"
            
            return {
                'file': file,
                'user_id': user_id,
                'type': payload.get('type')
            }, None
            
        except jwt.ExpiredSignatureError:
            return None, "Token expired"
        except jwt.InvalidTokenError:
            return None, "Invalid token"
        except Exception as e:
            logger.error(f"Error verifying password-protected token: {e}")
            return None, "Token verification failed"
    
    def get_access_logs(self, file_id=None, user_id=None, limit=100):
        """Get access logs with optional filters"""
        try:
            query = AccessLog.query
            
            if file_id:
                query = query.filter_by(file_id=file_id)
            
            if user_id:
                query = query.filter_by(user_id=user_id)
            
            logs = query.order_by(AccessLog.accessed_at.desc()).limit(limit).all()
            return logs
            
        except Exception as e:
            logger.error(f"Error getting access logs: {e}")
            return []
    
    def generate_admin_token(self, admin_user_id):
        """Generate admin token for management operations"""
        try:
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            payload = {
                'user_id': admin_user_id,
                'type': 'admin',
                'exp': expires_at,
                'iat': datetime.utcnow()
            }
            
            token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
            return token
            
        except Exception as e:
            logger.error(f"Error generating admin token: {e}")
            return None
    
    def verify_admin_token(self, token):
        """Verify admin token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            
            if payload.get('type') != 'admin':
                return None, "Invalid token type"
            
            user_id = payload.get('user_id')
            
            # Verify user is admin
            from src.models.user import User
            user = User.query.get(user_id)
            if not user or not user.is_admin():
                return None, "User is not admin"
            
            return {'user_id': user_id}, None
            
        except jwt.ExpiredSignatureError:
            return None, "Token expired"
        except jwt.InvalidTokenError:
            return None, "Invalid token"
        except Exception as e:
            logger.error(f"Error verifying admin token: {e}")
            return None, "Token verification failed"

