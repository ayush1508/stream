#!/usr/bin/env python3
"""
StreamFlix Bot Runner
Run the Telegram bot alongside the Flask web server
"""

import os
import sys
import threading
import logging
from src.main import create_app
from src.bot.telegram_bot import StreamFlixBot
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def run_flask_app(app):
    """Run Flask app in a separate thread"""
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

def main():
    """Main function to run both Flask and Telegram bot"""
    # Get bot token from environment
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        logger.info("Please set your bot token: export TELEGRAM_BOT_TOKEN='your_bot_token_here'")
        sys.exit(1)
    
    # Create Flask app
    app = create_app('production' if os.environ.get('FLASK_ENV') == 'production' else 'development')
    
    # Start Flask app in a separate thread
    flask_thread = threading.Thread(target=run_flask_app, args=(app,))
    flask_thread.daemon = True
    flask_thread.start()
    
    logger.info("Flask web server started on http://0.0.0.0:5000")
    
    # Create and run Telegram bot
    with app.app_context():
        bot = StreamFlixBot(bot_token, app)
        
        # Check if webhook URL is provided
        webhook_url = os.environ.get('TELEGRAM_WEBHOOK_URL')
        
        if webhook_url:
            logger.info(f"Starting bot with webhook: {webhook_url}")
            bot.run_webhook(webhook_url)
        else:
            logger.info("Starting bot in polling mode")
            bot.run_polling()

if __name__ == '__main__':
    main()

