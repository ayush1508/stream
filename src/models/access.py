from src.models.user import db, RequestStatus
from datetime import datetime

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
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # 'download', 'stream', 'view'
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    accessed_at = db.Column(db.DateTime, default=datetime.utcnow)
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<AccessLog {self.action} - File {self.file_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'file_id': self.file_id,
            'action': self.action,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'accessed_at': self.accessed_at.isoformat() if self.accessed_at else None,
            'success': self.success,
            'error_message': self.error_message
        }

class StreamingSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=False)
    session_token = db.Column(db.String(255), unique=True, nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_position = db.Column(db.Float, default=0.0)  # in seconds
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    ip_address = db.Column(db.String(45), nullable=True)

    def __repr__(self):
        return f'<StreamingSession {self.session_token}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'file_id': self.file_id,
            'session_token': self.session_token,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'last_position': self.last_position,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'ip_address': self.ip_address
        }

    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    def update_position(self, position):
        self.last_position = position
        db.session.commit()

