import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.user import db
from src.models.file import File
from src.models.access import AccessRequest, AccessLog, StreamingSession
from src.routes.user import user_bp
from src.routes.streaming import streaming_bp
from src.routes.admin import admin_bp
from config import config

def create_app(config_name='development'):
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    
    # Load configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Enable CORS
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    # Initialize database
    db.init_app(app)
    
    # Register blueprints
    app.register_blueprint(user_bp, url_prefix='/api')
    app.register_blueprint(streaming_bp, url_prefix='/')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Create default admin user if specified in config
        from src.models.user import User, UserRole
        if app.config.get('ADMIN_TELEGRAM_IDS'):
            for admin_id in app.config['ADMIN_TELEGRAM_IDS']:
                existing_admin = User.query.filter_by(telegram_id=admin_id).first()
                if not existing_admin:
                    admin_user = User(
                        telegram_id=admin_id,
                        username=f"admin_{admin_id}",
                        role=UserRole.ADMIN,
                        is_approved=True
                    )
                    db.session.add(admin_user)
            db.session.commit()

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        static_folder_path = app.static_folder
        if static_folder_path is None:
                return "Static folder not configured", 404

        if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
            return send_from_directory(static_folder_path, path)
        else:
            index_path = os.path.join(static_folder_path, 'index.html')
            if os.path.exists(index_path):
                return send_from_directory(static_folder_path, 'index.html')
            else:
                return "StreamFlix Bot Backend Running", 200

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
