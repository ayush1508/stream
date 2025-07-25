#!/bin/bash

# StreamFlix Bot Setup Script

echo "🎬 StreamFlix Bot Setup"
echo "======================"

# Check if Python 3.11+ is available
if ! command -v python3.11 &> /dev/null; then
    echo "❌ Python 3.11+ is required but not found."
    echo "Please install Python 3.11 or higher."
    exit 1
fi

# Check if ffmpeg is available
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg not found. Installing..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y ffmpeg
    elif command -v yum &> /dev/null; then
        sudo yum install -y ffmpeg
    elif command -v brew &> /dev/null; then
        brew install ffmpeg
    else
        echo "❌ Could not install FFmpeg automatically."
        echo "Please install FFmpeg manually for video processing features."
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3.11 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p uploads thumbnails logs

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating environment configuration..."
    cp .env.example .env
    echo "📝 Please edit .env file with your configuration:"
    echo "   - Set TELEGRAM_BOT_TOKEN"
    echo "   - Set ADMIN_TELEGRAM_IDS"
    echo "   - Update other settings as needed"
fi

# Set permissions
echo "🔐 Setting permissions..."
chmod +x run_bot.py
chmod +x setup.sh

echo ""
echo "✅ Setup completed!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Get your Telegram bot token from @BotFather"
echo "3. Add your Telegram ID to ADMIN_TELEGRAM_IDS"
echo "4. Run the bot: python run_bot.py"
echo ""
echo "For more information, see README.md"

