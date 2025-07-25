from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from enum import Enum
from src.main import db

# IMPORTANT: You need to import the `db` object from where it's initialized.
# For example, if db is initialized in src/main.py, you might use:
# from src.main import db
# If db is initialized in user.py, you might use:
# from .user import db
# For this example, I'm assuming db is available globally or imported correctly.
# If you get a NameError for 'db', adjust this import line.

# Placeholder for db if not imported. In a real app, you'd import it.
# db = SQLAlchemy() 

class RequestStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

# Add this class to your src/models/access.py file

class StreamingSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    file_id = db.Column(db.Integer, db.ForeignKey("file.id"), nullable=False)
    session_token = db.Column(db.String(255), unique=True, nullable=False) # JWT or unique token
    expires_at = db.Column(db.DateTime, nullable=False)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    play_position = db.Column(db.Integer, default=0) # In seconds

    def __repr__(self):
        return f"<StreamingSession {self.session_token} for user {self.user_id} on file {self.file_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "file_id": self.file_id,
            "session_token": self.session_token,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "play_position": self.play_position,
        }



class AccessRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    purpose = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    processed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<AccessRequest {self.name} - {self.status.value}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'purpose': self.purpose,
            'status': self.status.value,
            'requested_at': self.requested_at.isoformat() if self.requested_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'processed_by': self.processed_by,
            'admin_notes': self.admin_notes
        }

class AccessLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=True)
    action = db.Column(db.String(50), nullable=False)  # 'download', 'stream', 'view'
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AccessLog {self.action} by user {self.user_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'file_id': self.file_id,
            'action': self.action,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
