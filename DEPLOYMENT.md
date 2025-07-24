# 🚀 StreamFlix Bot Deployment Guide

This guide covers various deployment options for StreamFlix Bot, from development to production environments.

## 📋 Prerequisites

### System Requirements
- **Operating System**: Linux (Ubuntu 20.04+ recommended), macOS, or Windows
- **Python**: Version 3.11 or higher
- **Memory**: Minimum 512MB RAM (2GB+ recommended for production)
- **Storage**: 10GB+ available space (depends on file storage needs)
- **Network**: Stable internet connection for Telegram API

### Required Software
- **FFmpeg**: For video/audio processing
- **Git**: For version control
- **Nginx**: For production reverse proxy (optional)
- **Docker**: For containerized deployment (optional)

## 🛠️ Development Deployment

### Local Development Setup

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd streamflix-bot
   ```

2. **Run Setup Script**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your settings
   ```

4. **Start Development Server**
   ```bash
   source venv/bin/activate
   python run_bot.py
   ```

### Development Configuration
```bash
# .env for development
FLASK_ENV=development
FLASK_DEBUG=True
TELEGRAM_BOT_TOKEN=your_development_bot_token
ADMIN_TELEGRAM_IDS=your_telegram_id
DATABASE_URL=sqlite:///dev_streamflix.db
```

## 🏭 Production Deployment

### Option 1: Direct Server Deployment

#### 1. Server Preparation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip ffmpeg nginx

# Create user
sudo useradd -m -s /bin/bash streamflix
sudo usermod -aG sudo streamflix
```

#### 2. Application Setup
```bash
# Switch to streamflix user
sudo su - streamflix

# Clone repository
git clone <repository-url> /opt/streamflix-bot
cd /opt/streamflix-bot

# Run setup
./setup.sh

# Configure production environment
cp .env.example .env
nano .env  # Set production values
```

#### 3. Production Environment Configuration
```bash
# .env for production
FLASK_ENV=production
FLASK_DEBUG=False
TELEGRAM_BOT_TOKEN=your_production_bot_token
ADMIN_TELEGRAM_IDS=comma_separated_admin_ids
DATABASE_URL=postgresql://user:pass@localhost/streamflix
SECRET_KEY=your_very_secure_secret_key
JWT_SECRET_KEY=your_jwt_secret_key
UPLOAD_FOLDER=/opt/streamflix-bot/uploads
```

#### 4. Database Setup (PostgreSQL)
```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Create database
sudo -u postgres createuser streamflix
sudo -u postgres createdb streamflix -O streamflix
sudo -u postgres psql -c "ALTER USER streamflix PASSWORD 'secure_password';"

# Update connection string
DATABASE_URL=postgresql://streamflix:secure_password@localhost/streamflix
```

#### 5. Systemd Service
```bash
# Create service file
sudo nano /etc/systemd/system/streamflix-bot.service
```

```ini
[Unit]
Description=StreamFlix Bot
After=network.target postgresql.service

[Service]
Type=simple
User=streamflix
Group=streamflix
WorkingDirectory=/opt/streamflix-bot
Environment=PATH=/opt/streamflix-bot/venv/bin
Environment=FLASK_ENV=production
EnvironmentFile=/opt/streamflix-bot/.env
ExecStart=/opt/streamflix-bot/venv/bin/python /opt/streamflix-bot/run_bot.py
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/streamflix-bot/uploads /opt/streamflix-bot/thumbnails

[Install]
WantedBy=multi-user.target
```

#### 6. Start Service
```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable streamflix-bot
sudo systemctl start streamflix-bot

# Check status
sudo systemctl status streamflix-bot
```

#### 7. Nginx Configuration
```bash
# Create Nginx config
sudo nano /etc/nginx/sites-available/streamflix-bot
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # File upload size
    client_max_body_size 2G;

    # Main application
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Streaming endpoints with special handling
    location /stream/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_buffering off;
        proxy_set_header Range $http_range;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # API endpoints
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Static files (if any)
    location /static/ {
        alias /opt/streamflix-bot/src/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

#### 8. Enable Nginx Site
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/streamflix-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 9. SSL with Let's Encrypt
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Option 2: Docker Deployment

#### 1. Create Dockerfile
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 streamflix

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads thumbnails logs

# Set ownership
RUN chown -R streamflix:streamflix /app

# Switch to app user
USER streamflix

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Start application
CMD ["python", "run_bot.py"]
```

#### 2. Create Docker Compose
```yaml
version: '3.8'

services:
  streamflix-bot:
    build: .
    container_name: streamflix-bot
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - ADMIN_TELEGRAM_IDS=${ADMIN_TELEGRAM_IDS}
      - DATABASE_URL=postgresql://streamflix:${DB_PASSWORD}@db:5432/streamflix
      - SECRET_KEY=${SECRET_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    volumes:
      - ./uploads:/app/uploads
      - ./thumbnails:/app/thumbnails
      - ./logs:/app/logs
    depends_on:
      - db
    networks:
      - streamflix-network

  db:
    image: postgres:15
    container_name: streamflix-db
    restart: unless-stopped
    environment:
      - POSTGRES_DB=streamflix
      - POSTGRES_USER=streamflix
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - streamflix-network

  nginx:
    image: nginx:alpine
    container_name: streamflix-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - streamflix-bot
    networks:
      - streamflix-network

volumes:
  postgres_data:

networks:
  streamflix-network:
    driver: bridge
```

#### 3. Environment File for Docker
```bash
# .env for Docker
TELEGRAM_BOT_TOKEN=your_bot_token
ADMIN_TELEGRAM_IDS=your_admin_ids
DB_PASSWORD=secure_database_password
SECRET_KEY=your_secret_key
JWT_SECRET_KEY=your_jwt_secret_key
```

#### 4. Deploy with Docker
```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f streamflix-bot

# Update application
docker-compose pull
docker-compose up -d --build
```

### Option 3: Cloud Deployment

#### Heroku Deployment

1. **Prepare for Heroku**
```bash
# Create Procfile
echo "web: python run_bot.py" > Procfile

# Create runtime.txt
echo "python-3.11.0" > runtime.txt
```

2. **Deploy to Heroku**
```bash
# Install Heroku CLI and login
heroku login

# Create app
heroku create your-streamflix-bot

# Add buildpacks
heroku buildpacks:add --index 1 heroku/python
heroku buildpacks:add --index 2 https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git

# Set environment variables
heroku config:set TELEGRAM_BOT_TOKEN=your_token
heroku config:set ADMIN_TELEGRAM_IDS=your_ids
heroku config:set FLASK_ENV=production

# Deploy
git push heroku main
```

#### AWS EC2 Deployment

1. **Launch EC2 Instance**
   - Choose Ubuntu 20.04 LTS
   - Select appropriate instance type (t3.medium recommended)
   - Configure security groups (ports 22, 80, 443)

2. **Setup Application**
```bash
# Connect to instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Follow production deployment steps above
```

3. **Configure Load Balancer** (for high availability)
   - Create Application Load Balancer
   - Configure target groups
   - Set up health checks

## 🔧 Configuration Management

### Environment Variables Reference

| Variable | Development | Production | Description |
|----------|-------------|------------|-------------|
| `FLASK_ENV` | development | production | Flask environment |
| `FLASK_DEBUG` | True | False | Debug mode |
| `TELEGRAM_BOT_TOKEN` | dev_token | prod_token | Bot authentication |
| `DATABASE_URL` | sqlite:/// | postgresql:// | Database connection |
| `SECRET_KEY` | simple | complex | Flask secret key |
| `UPLOAD_FOLDER` | uploads | /var/uploads | File storage path |

### Security Configuration

#### Production Security Checklist
- [ ] Use strong, unique secret keys
- [ ] Enable HTTPS with valid SSL certificates
- [ ] Configure firewall rules
- [ ] Set up regular backups
- [ ] Enable access logging
- [ ] Implement rate limiting
- [ ] Use secure database passwords
- [ ] Regular security updates

#### File Storage Security
```bash
# Set proper permissions
chmod 755 /opt/streamflix-bot/uploads
chmod 644 /opt/streamflix-bot/uploads/*

# Create separate partition for uploads (recommended)
sudo mkdir /var/streamflix-uploads
sudo mount /dev/sdb1 /var/streamflix-uploads
```

## 📊 Monitoring and Maintenance

### Log Management
```bash
# Application logs
tail -f /opt/streamflix-bot/logs/streamflix.log

# System service logs
journalctl -u streamflix-bot -f

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Performance Monitoring
```bash
# System resources
htop
df -h
free -h

# Application metrics
curl http://localhost:5000/admin/stats
```

### Backup Strategy
```bash
# Database backup
pg_dump streamflix > backup_$(date +%Y%m%d).sql

# File backup
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz uploads/

# Automated backup script
#!/bin/bash
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
pg_dump streamflix > "$BACKUP_DIR/db_$DATE.sql"

# Files backup
tar -czf "$BACKUP_DIR/files_$DATE.tar.gz" uploads/ thumbnails/

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

### Update Procedure
```bash
# 1. Backup current version
sudo systemctl stop streamflix-bot
cp -r /opt/streamflix-bot /opt/streamflix-bot.backup

# 2. Update code
cd /opt/streamflix-bot
git pull origin main

# 3. Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# 4. Run migrations (if any)
python -c "from src.main import create_app; app = create_app(); app.app_context().push(); from src.models.user import db; db.create_all()"

# 5. Restart service
sudo systemctl start streamflix-bot
sudo systemctl status streamflix-bot
```

## 🚨 Troubleshooting

### Common Deployment Issues

#### Service Won't Start
```bash
# Check service status
sudo systemctl status streamflix-bot

# Check logs
journalctl -u streamflix-bot --no-pager

# Common fixes
sudo systemctl daemon-reload
sudo systemctl restart streamflix-bot
```

#### Database Connection Issues
```bash
# Test database connection
python -c "
from src.main import create_app
app = create_app()
with app.app_context():
    from src.models.user import db
    db.create_all()
    print('Database OK')
"
```

#### File Permission Issues
```bash
# Fix ownership
sudo chown -R streamflix:streamflix /opt/streamflix-bot

# Fix permissions
sudo chmod -R 755 /opt/streamflix-bot
sudo chmod -R 777 /opt/streamflix-bot/uploads
```

#### Nginx Issues
```bash
# Test configuration
sudo nginx -t

# Check logs
sudo tail -f /var/log/nginx/error.log

# Restart nginx
sudo systemctl restart nginx
```

### Performance Optimization

#### Database Optimization
```sql
-- Create indexes for better performance
CREATE INDEX idx_files_uploader ON files(uploader_id);
CREATE INDEX idx_files_type ON files(file_type);
CREATE INDEX idx_access_logs_file ON access_logs(file_id);
CREATE INDEX idx_access_logs_user ON access_logs(user_id);
```

#### File Storage Optimization
```bash
# Use SSD for database
# Use HDD for file storage
# Implement file compression
# Set up CDN for static files
```

## 📈 Scaling Considerations

### Horizontal Scaling
- Use load balancer (Nginx, HAProxy)
- Separate database server
- Shared file storage (NFS, S3)
- Redis for session management

### Vertical Scaling
- Increase server resources
- Optimize database queries
- Implement caching
- Use async processing

---

This deployment guide covers all major deployment scenarios. Choose the option that best fits your infrastructure and requirements. For additional support, refer to the main README.md or create an issue on GitHub.

