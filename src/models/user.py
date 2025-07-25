from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from enum import Enum

db = SQLAlchemy() # Assuming db is initialized here or imported from a central place

class UserRole(Enum):
    USER = "user"
    ADMIN = "admin"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=False)
    username = db.Column(db.String(80), nullable=True)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    role = db.Column(db.Enum(UserRole), default=UserRole.USER, nullable=False)
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    uploaded_files = db.relationship(
        'File', backref='uploader', lazy=True
    )

    # Relationship for requests made by this user
    requested_accesses = db.relationship(
        'AccessRequest', 
        backref='requester', # This backref will be on AccessRequest model
        lazy=True, 
        foreign_keys='AccessRequest.user_id' # Link to AccessRequest.user_id
    )

    # Relationship for requests processed by this user (if they are an admin)
    processed_accesses = db.relationship(
        'AccessRequest', 
        backref='processor', # This backref will be on AccessRequest model
        lazy=True, 
        foreign_keys='AccessRequest.processed_by' # Link to AccessRequest.processed_by
    )

    access_logs = db.relationship(
        'AccessLog', backref='user', lazy=True
    )

    def __repr__(self):
        return f'<User {self.username or self.telegram_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'telegram_id': self.telegram_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role.value,
            'is_approved': self.is_approved,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_active': self.last_active.isoformat() if self.last_active else None
        }

    def is_admin(self):
        return self.role == UserRole.ADMIN

    def can_access_files(self):
        return self.is_admin() or self.is_approved

