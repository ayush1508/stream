# 🎬 StreamFlix Bot

A comprehensive Telegram bot for file management, streaming, and downloads with Netflix-like features.

## ✨ Features

### 📁 File Management
- **Universal File Support**: Upload any file type including videos, audio, documents, images, archives, and APKs
- **Smart Organization**: Automatic file organization by uploader, type, and date
- **Thumbnail Generation**: Automatic thumbnail creation for videos and images
- **File Compression**: Intelligent compression for large files to optimize streaming

### 🎮 Streaming & Downloads
- **Netflix-like Player**: HTML5 video player with adaptive bitrate streaming
- **Resume Watching**: Automatic position saving and resume functionality
- **Subtitle Support**: Built-in subtitle overlay and multiple audio track switching
- **Secure Links**: JWT-based secure streaming and download links with expiry
- **Mobile Responsive**: Optimized for both desktop and mobile devices

### 🛡️ Security & Access Control
- **Admin System**: Multi-level user roles (Admin/User)
- **Access Requests**: User approval workflow with admin notifications
- **Anti-leeching**: Session-based protection against unauthorized access
- **Access Logging**: Comprehensive logging of all file access attempts
- **Password Protection**: Optional password-protected links

### 🔍 Advanced Search
- **Smart Search**: Search files by name, type, uploader, and date
- **Filtering**: Advanced filtering options for efficient file discovery
- **Inline Results**: Interactive search results with instant streaming/download buttons

### 👑 Admin Dashboard
- **Web Interface**: Beautiful web-based admin panel
- **User Management**: Approve/reject users, manage roles and permissions
- **Statistics**: Comprehensive usage analytics and file statistics
- **Access Logs**: Monitor all file access and user activity
- **File Management**: Delete files, view upload statistics

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- FFmpeg (for video processing)
- Telegram Bot Token (from @BotFather)

### Installation

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd streamflix-bot
   chmod +x setup.sh
   ./setup.sh
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Set Required Variables**
   ```bash
   export TELEGRAM_BOT_TOKEN="your_bot_token_here"
   export ADMIN_TELEGRAM_IDS="your_telegram_id"
   ```

4. **Run the Bot**
   ```bash
   python run_bot.py
   ```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | ✅ | - |
| `ADMIN_TELEGRAM_IDS` | Comma-separated admin IDs | ✅ | - |
| `SECRET_KEY` | Flask secret key | ❌ | Auto-generated |
| `JWT_SECRET_KEY` | JWT signing key | ❌ | Auto-generated |
| `DATABASE_URL` | Database connection string | ❌ | SQLite |
| `UPLOAD_FOLDER` | File upload directory | ❌ | `uploads` |
| `TELEGRAM_WEBHOOK_URL` | Webhook URL for production | ❌ | - |

### Getting Your Bot Token

1. Message @BotFather on Telegram
2. Send `/newbot` and follow instructions
3. Copy the token to your `.env` file
4. Send `/setcommands` to set bot commands:
   ```
   start - Welcome message and status
   help - Show detailed help
   search - Search for files
   request_access - Request bot access
   ```

### Finding Your Telegram ID

1. Message @userinfobot on Telegram
2. Copy your numeric ID to `ADMIN_TELEGRAM_IDS`

## 📖 User Guide

### For Regular Users

#### Getting Access
1. Start the bot with `/start`
2. If not approved, use `/request_access Your Name | Purpose`
3. Wait for admin approval

#### Uploading Files
- Simply send any file to the bot
- Get secure streaming and download links
- Files are automatically organized

#### Searching Files
- Use `/search filename` to find files
- Click inline buttons to stream or download
- Filter by type, uploader, or date

#### Streaming Experience
- Click stream links for Netflix-like player
- Use keyboard shortcuts:
  - `Space`: Play/Pause
  - `←/→`: Skip 10 seconds
  - `F`: Fullscreen
- Position automatically saved

### For Admins

#### Bot Commands
- `/view_users` - List all users
- `/approve_requests` - View pending requests
- `/revoke_access @username` - Remove access
- `/make_admin @username` - Promote to admin
- `/remove_admin @username` - Demote admin
- `/stats` - View usage statistics

#### Web Dashboard
1. Visit `http://your-server:5000`
2. Login with your Telegram ID
3. Manage users, files, and view analytics

## 🏗️ Architecture

### Core Components

#### Backend (Flask)
- **Main App**: Flask application with CORS support
- **Database**: SQLAlchemy with SQLite/PostgreSQL
- **Authentication**: JWT-based secure token system
- **File Processing**: FFmpeg integration for media processing

#### Telegram Bot
- **python-telegram-bot**: Modern async Telegram bot framework
- **Command Handlers**: Comprehensive command processing
- **File Handlers**: Multi-format file upload processing
- **Inline Keyboards**: Interactive button interfaces

#### Security Layer
- **JWT Tokens**: Secure link generation with expiry
- **Session Management**: Anti-leeching protection
- **Access Control**: Role-based permissions
- **Audit Logging**: Comprehensive access tracking

### Database Schema

#### Users Table
- `telegram_id`: Unique Telegram user ID
- `username`, `first_name`, `last_name`: User information
- `role`: Admin or User role
- `is_approved`: Access approval status
- `created_at`, `last_active`: Timestamps

#### Files Table
- `filename`, `original_filename`: File identifiers
- `file_path`, `file_size`: Storage information
- `file_type`, `mime_type`: Type classification
- `duration`, `width`, `height`: Media metadata
- `thumbnail_path`: Generated thumbnail location
- `download_count`, `stream_count`: Usage statistics

#### Access Management
- **AccessRequest**: User access requests
- **AccessLog**: File access audit trail
- **StreamingSession**: Active streaming sessions

## 🔧 API Documentation

### Authentication
All admin API endpoints require Bearer token authentication:
```
Authorization: Bearer <jwt_token>
```

### Admin Endpoints

#### Login
```http
POST /admin/login
Content-Type: application/json

{
  "telegram_id": 123456789
}
```

#### Get Users
```http
GET /admin/users?page=1&per_page=20&search=username
Authorization: Bearer <token>
```

#### Update User
```http
PUT /admin/users/{user_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "is_approved": true,
  "role": "admin"
}
```

#### Get Files
```http
GET /admin/files?page=1&type=video&uploader_id=123
Authorization: Bearer <token>
```

#### Get Statistics
```http
GET /admin/stats
Authorization: Bearer <token>
```

### Streaming Endpoints

#### Stream File
```http
GET /stream/{jwt_token}
```

#### Download File
```http
GET /download/{jwt_token}
```

#### Stream Data (for player)
```http
GET /api/stream/{jwt_token}/data
Range: bytes=0-1023
```

#### Update Position
```http
POST /api/stream/{jwt_token}/position
Content-Type: application/json

{
  "position": 120.5
}
```

## 🚀 Deployment

### Development
```bash
python run_bot.py
```

### Production with Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "run_bot.py"]
```

### Production with systemd
```ini
[Unit]
Description=StreamFlix Bot
After=network.target

[Service]
Type=simple
User=streamflix
WorkingDirectory=/opt/streamflix-bot
Environment=FLASK_ENV=production
ExecStart=/opt/streamflix-bot/venv/bin/python run_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /stream/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_buffering off;
        proxy_set_header Range $http_range;
    }
}
```

## 🔒 Security Considerations

### Best Practices
- Use strong JWT secret keys
- Enable HTTPS in production
- Regularly rotate tokens
- Monitor access logs
- Implement rate limiting
- Use secure file storage

### File Security
- Validate file types and sizes
- Scan uploads for malware
- Implement virus scanning
- Use secure file paths
- Regular cleanup of expired files

## 🐛 Troubleshooting

### Common Issues

#### Bot Not Responding
- Check `TELEGRAM_BOT_TOKEN` is correct
- Verify bot is not already running
- Check network connectivity
- Review logs for errors

#### File Upload Fails
- Check disk space
- Verify upload directory permissions
- Ensure FFmpeg is installed
- Check file size limits

#### Streaming Issues
- Verify JWT token validity
- Check file exists on disk
- Ensure proper MIME types
- Test with different browsers

#### Database Errors
- Check database permissions
- Verify SQLite file location
- Run database migrations
- Check disk space

### Logs and Debugging
```bash
# Enable debug logging
export FLASK_DEBUG=True

# View logs
tail -f logs/streamflix.log

# Test database connection
python -c "from src.main import create_app; app = create_app(); print('DB OK')"
```

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create feature branch
3. Install development dependencies
4. Run tests
5. Submit pull request

### Code Style
- Follow PEP 8 for Python
- Use type hints
- Add docstrings
- Write tests for new features

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- python-telegram-bot for excellent Telegram integration
- Flask for the robust web framework
- FFmpeg for media processing capabilities
- SQLAlchemy for database management

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the API documentation
- Join our community discussions

---

**StreamFlix Bot** - Making file sharing and streaming simple and secure! 🎬✨

