import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
from src.models.user import db, User, UserRole
from src.models.file import File, FileType
from src.models.access import AccessRequest, RequestStatus
from src.services.file_service import FileService
from src.services.auth_service import AuthService
from datetime import datetime
from types import SimpleNamespace

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class StreamFlixBot:
    def __init__(self, token, flask_app):
        self.token = token
        self.flask_app = flask_app
        self.application = Application.builder().token(token).build()
        self.file_service = FileService()
        self.auth_service = AuthService()
        self.setup_handlers()

    def setup_handlers(self):
        """Setup all command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("request_access", self.request_access_command))
        self.application.add_handler(CommandHandler("search", self.search_command))
        
        # Admin commands
        self.application.add_handler(CommandHandler("view_users", self.view_users_command))
        self.application.add_handler(CommandHandler("approve_requests", self.approve_requests_command))
        self.application.add_handler(CommandHandler("revoke_access", self.revoke_access_command))
        self.application.add_handler(CommandHandler("make_admin", self.make_admin_command))
        self.application.add_handler(CommandHandler("remove_admin", self.remove_admin_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        
        # File upload handler
        self.application.add_handler(MessageHandler(filters.Document.ALL, self.handle_file_upload))
        self.application.add_handler(MessageHandler(filters.AUDIO, self.handle_file_upload))
        self.application.add_handler(MessageHandler(filters.VIDEO, self.handle_file_upload))
        
        # Callback query handler for inline buttons
        self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = await self.get_or_create_user(update.effective_user)
        
        welcome_text = f"""
🎬 **Welcome to StreamFlix Bot!**

Hello {user.first_name or user.username or 'User'}!

**What is StreamFlix Bot?**
StreamFlix Bot is your personal media streaming and file management solution. Upload videos, audio, documents, and more, then stream or download them with secure, Netflix-like controls.

**Your Status:** {'✅ Admin' if user.is_admin() else '✅ Approved User' if user.is_approved else '⏳ Pending Approval'}

**Available Commands:**
• `/help` - Show detailed help
• `/search <filename>` - Search for files
• `/request_access` - Request access (if not approved)

**For Admins:**
• `/view_users` - List all users
• `/approve_requests` - View pending requests
• `/stats` - View usage statistics

**How to use:**
1. Send any file to upload it
2. Get secure streaming and download links
3. Enjoy Netflix-like streaming experience!

Ready to get started? Send me a file! 📁
        """
        
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🎬 **StreamFlix Bot - Complete Guide**

**📁 Supported File Types:**
• 🎥 Videos: .mp4, .mkv, .webm, .avi, .mov
• 🎵 Audio: .mp3, .aac, .wav, .flac, .ogg
• 📜 Subtitles: .srt, .vtt, .ass
• 📄 Documents: .pdf, .doc, .txt, .epub
• 🖼️ Images: .jpg, .png, .gif, .webp
• 📦 Archives: .zip, .rar, .7z, .tar
• 📱 APKs: .apk files

**🎮 User Commands:**
• `/start` - Welcome message and status
• `/help` - This help message
• `/search <query>` - Search files by name
• `/request_access` - Request bot access

**👑 Admin Commands:**
• `/view_users` - List all users
• `/approve_requests` - View pending access requests
• `/revoke_access @username` - Remove user access
• `/make_admin @username` - Promote to admin
• `/remove_admin @username` - Demote admin
• `/stats` - View usage statistics

**📤 How to Upload:**
1. Simply send any file to the bot
2. Files are automatically organized by:
   - Your username
   - File type
   - Upload date

**🔗 Generated Links:**
Each file gets two secure links:
• **▶️ Streaming Link** - Netflix-like player with:
  - Adaptive bitrate streaming
  - Subtitle support
  - Audio track switching
  - Resume watching
• **⬇️ Download Link** - Direct download (with expiry)

**🔍 Search Features:**
• Search by filename
• Filter by file type
• Filter by uploader
• Filter by date range

**🛡️ Security Features:**
• Encrypted streaming URLs
• Anti-leeching protection
• Session management
• Access logging
• Auto-expiry options

Need help? Contact an admin! 👨‍💼
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

    async def request_access_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /request_access command"""
        user = await self.get_or_create_user(update.effective_user)
        
        if user.is_approved:
            await update.message.reply_text("✅ You already have access to the bot!")
            return
        
        # Check if user already has a pending request
        with self.flask_app.app_context():
            existing_request = AccessRequest.query.filter_by(
                user_id=user.id, 
                status=RequestStatus.PENDING
            ).first()
            
            if existing_request:
                await update.message.reply_text(
                    "⏳ You already have a pending access request. Please wait for admin approval."
                )
                return
        
        # Ask for name and purpose
        await update.message.reply_text(
            "📝 **Access Request Form**\n\n"
            "Please provide the following information:\n"
            "Format: `/request_access Your Name | Purpose/Reason`\n\n"
            "Example: `/request_access John Doe | Need access for educational content sharing`",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Parse the request if arguments provided
        if context.args:
            request_text = " ".join(context.args)
            if "|" in request_text:
                name, purpose = request_text.split("|", 1)
                name = name.strip()
                purpose = purpose.strip()
                
                if name and purpose:
                    await self.create_access_request(user, name, purpose, update)
                else:
                    await update.message.reply_text("❌ Please provide both name and purpose!")
            else:
                await update.message.reply_text("❌ Please use the correct format with | separator!")

    async def create_access_request(self, user, name, purpose, update):
        """Create a new access request"""
        with self.flask_app.app_context():
            access_request = AccessRequest(
                user_id=user.id,
                name=name,
                purpose=purpose
            )
            db.session.add(access_request)
            db.session.commit()
            
            # Notify admins
            await self.notify_admins_new_request(access_request, update)
            
            await update.message.reply_text(
                "✅ **Access request submitted!**\n\n"
                f"**Name:** {name}\n"
                f"**Purpose:** {purpose}\n\n"
                "Admins have been notified. You'll receive a response soon! ⏳"
            )

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command"""
        user = await self.get_or_create_user(update.effective_user)
        
        if not user.can_access_files():
            await update.message.reply_text("❌ You don't have access to search files. Use /request_access first.")
            return
        
        if not context.args:
            await update.message.reply_text(
                "🔍 **Search Files**\n\n"
                "Usage: `/search <filename>`\n"
                "Example: `/search movie.mp4`\n\n"
                "You can search by:\n"
                "• Filename\n"
                "• File type\n"
                "• Uploader name"
            )
            return
        
        query = " ".join(context.args)
        await self.perform_search(user, query, update)

    async def perform_search(self, user, query, update):
        """Perform file search"""
        with self.flask_app.app_context():
            files = File.query.filter(
                File.original_filename.contains(query)
            ).limit(10).all()
            
            if not files:
                await update.message.reply_text(f"🔍 No files found matching '{query}'")
                return
            
            response = f"🔍 **Search Results for '{query}'**\n\n"
            
            for file in files:
                uploader = User.query.get(file.uploader_id)
                file_size = self.format_file_size(file.file_size)
                
                response += f"📁 **{file.original_filename}**\n"
                response += f"📊 Size: {file_size} | Type: {file.file_type.value}\n"
                response += f"👤 Uploader: {uploader.username or uploader.first_name}\n"
                response += f"📅 Uploaded: {file.uploaded_at.strftime('%Y-%m-%d')}\n"
                
                # Create inline buttons for each file
                keyboard = [
                    [
                        InlineKeyboardButton("▶️ Stream", callback_data=f"stream_{file.id}"),
                        InlineKeyboardButton("⬇️ Download", callback_data=f"download_{file.id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(response, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
                response = ""  # Reset for next file

    async def handle_file_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle file uploads"""
        user = await self.get_or_create_user(update.effective_user)
        
        if not user.is_admin():
            await update.message.reply_text("❌ Only admins can upload files.")
            return
        
        # Get file info
        file_obj = None
        if update.message.document:
            file_obj = update.message.document
        elif update.message.audio:
            file_obj = update.message.audio
        elif update.message.video:
            file_obj = update.message.video
        
        if not file_obj:
            return
        
        # Send processing message
        processing_msg = await update.message.reply_text("📤 Processing your file... Please wait.")
        
        try:
            # Download and process file
            file_record = await self.file_service.process_upload(file_obj, user, update, context)
            
            if file_record:
                # Generate secure links
                stream_link = self.auth_service.generate_stream_link(file_record.id, user.id)
                download_link = self.auth_service.generate_download_link(file_record.id, user.id)
                
                # Create response with inline buttons
                keyboard = [
                    [
                        InlineKeyboardButton("▶️ Stream Now", url=stream_link),
                        InlineKeyboardButton("⬇️ Download", url=download_link)
                    ],
                    [
                        InlineKeyboardButton("🔁 Reshare", callback_data=f"reshare_{file_record.id}"),
                        InlineKeyboardButton("📊 Stats", callback_data=f"stats_{file_record.id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                file_size = self.format_file_size(file_record.file_size)
                
                success_text = f"""
✅ **File uploaded successfully!**

📁 **{file_record.original_filename}**
📊 Size: {file_size}
🎬 Type: {file_record.file_type.value}
📅 Uploaded: {file_record.uploaded_at.strftime('%Y-%m-%d %H:%M')}

🔗 **Your secure links are ready!**
                """
                
                await processing_msg.edit_text(success_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            else:
                await processing_msg.edit_text("❌ Failed to process file. Please try again.")
                
        except Exception as e:
            logger.error(f"File upload error: {e}")
            await processing_msg.edit_text("❌ An error occurred while processing your file.")

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks"""
        query = update.callback_query
        await query.answer()
        
        user = await self.get_or_create_user(update.effective_user)
        data = query.data
        
        if data.startswith("stream_"):
            file_id = int(data.split("_")[1])
            stream_link = self.auth_service.generate_stream_link(file_id, user.id)
            await query.edit_message_text(f"▶️ Stream link generated: {stream_link}")
            
        elif data.startswith("download_"):
            file_id = int(data.split("_")[1])
            download_link = self.auth_service.generate_download_link(file_id, user.id)
            await query.edit_message_text(f"⬇️ Download link generated: {download_link}")
            
        elif data.startswith("approve_"):
            request_id = int(data.split("_")[1])
            await self.approve_access_request(request_id, user, query)
            
        elif data.startswith("reject_"):
            request_id = int(data.split("_")[1])
            await self.reject_access_request(request_id, user, query)
   
    async def get_or_create_user(self, telegram_user):
        """Get or create user from Telegram user object"""
        with self.flask_app.app_context():
            user = User.query.filter_by(telegram_id=telegram_user.id).first()

            if not user:
                user = User(
                    telegram_id=telegram_user.id,
                    username=telegram_user.username,
                    first_name=telegram_user.first_name,
                    last_name=telegram_user.last_name
                )
                db.session.add(user)
                db.session.commit()
            else:
                # Update user info
                user.username = telegram_user.username
                user.first_name = telegram_user.first_name
                user.last_name = telegram_user.last_name
                user.last_active = datetime.utcnow()
                db.session.commit()

            # Return a simple copy (not tied to SQLAlchemy session)
            return SimpleNamespace(
                id=user.id,
                telegram_id=user.telegram_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                is_admin=user.is_admin,
                is_approved=user.is_approved,
                can_access_files=user.can_access_files
            )

    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"

    async def notify_admins_new_request(self, access_request, update):
        """Notify all admins about new access request"""
        with self.flask_app.app_context():
            admins = User.query.filter_by(role=UserRole.ADMIN).all()
            
            for admin in admins:
                try:
                    keyboard = [
                        [
                            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{access_request.id}"),
                            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{access_request.id}")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    notification_text = f"""
🔔 **New Access Request**

👤 **Name:** {access_request.name}
🆔 **Username:** @{access_request.user.username or 'N/A'}
📝 **Purpose:** {access_request.purpose}
📅 **Requested:** {access_request.requested_at.strftime('%Y-%m-%d %H:%M')}
                    """
                    
                    await context.bot.send_message(
                        chat_id=admin.telegram_id,
                        text=notification_text,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin.telegram_id}: {e}")

    # Admin command implementations
    async def view_users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /view_users command (admin only)"""
        user = await self.get_or_create_user(update.effective_user)
        
        if not user.is_admin():
            await update.message.reply_text("❌ This command is only available to admins.")
            return
        
        with self.flask_app.app_context():
            users = User.query.all()
            
            response = "👥 **All Users**\n\n"
            
            for u in users:
                status = "👑 Admin" if u.is_admin() else "✅ Approved" if u.is_approved else "⏳ Pending"
                response += f"• {u.first_name or u.username or 'Unknown'} (@{u.username or 'N/A'}) - {status}\n"
            
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

    async def approve_requests_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /approve_requests command (admin only)"""
        user = await self.get_or_create_user(update.effective_user)
        
        if not user.is_admin():
            await update.message.reply_text("❌ This command is only available to admins.")
            return
        
        with self.flask_app.app_context():
            pending_requests = AccessRequest.query.filter_by(status=RequestStatus.PENDING).all()
            
            if not pending_requests:
                await update.message.reply_text("✅ No pending access requests.")
                return
            
            for request in pending_requests:
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Approve", callback_data=f"approve_{request.id}"),
                        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{request.id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                request_text = f"""
📋 **Access Request #{request.id}**

👤 **Name:** {request.name}
🆔 **Username:** @{request.user.username or 'N/A'}
📝 **Purpose:** {request.purpose}
📅 **Requested:** {request.requested_at.strftime('%Y-%m-%d %H:%M')}
                """
                
                await update.message.reply_text(request_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command (admin only)"""
        user = await self.get_or_create_user(update.effective_user)
        
        if not user.is_admin():
            await update.message.reply_text("❌ This command is only available to admins.")
            return
        
        with self.flask_app.app_context():
            total_users = User.query.count()
            approved_users = User.query.filter_by(is_approved=True).count()
            total_files = File.query.count()
            total_downloads = db.session.query(db.func.sum(File.download_count)).scalar() or 0
            total_streams = db.session.query(db.func.sum(File.stream_count)).scalar() or 0
            
            stats_text = f"""
📊 **StreamFlix Bot Statistics**

👥 **Users:**
• Total: {total_users}
• Approved: {approved_users}
• Pending: {total_users - approved_users}

📁 **Files:**
• Total uploaded: {total_files}
• Total downloads: {total_downloads}
• Total streams: {total_streams}

📈 **Activity:**
• Most active today
• Recent uploads
• Popular files
            """
            
            await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)

    async def approve_access_request(self, request_id, admin_user, query):
        """Approve an access request"""
        if not admin_user.is_admin():
            await query.edit_message_text("❌ You don't have permission to approve requests.")
            return
        
        with self.flask_app.app_context():
            request = AccessRequest.query.get(request_id)
            if not request:
                await query.edit_message_text("❌ Request not found.")
                return
            
            # Approve the user
            user = User.query.get(request.user_id)
            user.is_approved = True
            
            # Update request status
            request.status = RequestStatus.APPROVED
            request.processed_at = datetime.utcnow()
            request.processed_by = admin_user.id
            
            db.session.commit()
            
            # Notify the user
            try:
                await query.bot.send_message(
                    chat_id=user.telegram_id,
                    text="🎉 **Access Approved!**\n\nYour access request has been approved! You can now upload and access files. Welcome to StreamFlix Bot! 🎬",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Failed to notify user {user.telegram_id}: {e}")
            
            await query.edit_message_text(f"✅ Access request approved for {request.name}")

    async def reject_access_request(self, request_id, admin_user, query):
        """Reject an access request"""
        if not admin_user.is_admin():
            await query.edit_message_text("❌ You don't have permission to reject requests.")
            return
        
        with self.flask_app.app_context():
            request = AccessRequest.query.get(request_id)
            if not request:
                await query.edit_message_text("❌ Request not found.")
                return
            
            # Update request status
            request.status = RequestStatus.REJECTED
            request.processed_at = datetime.utcnow()
            request.processed_by = admin_user.id
            
            db.session.commit()
            
            # Notify the user
            user = User.query.get(request.user_id)
            try:
                await query.bot.send_message(
                    chat_id=user.telegram_id,
                    text="❌ **Access Request Rejected**\n\nYour access request has been rejected. You can submit a new request with more details if needed.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Failed to notify user {user.telegram_id}: {e}")
            
            await query.edit_message_text(f"❌ Access request rejected for {request.name}")

    async def revoke_access_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Dummy handler for /revoke_access"""
        await update.message.reply_text("Your access has been revoked (this is a placeholder).")

    async def make_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("👑 Make admin feature coming soon.")

    async def remove_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("❌ Remove admin feature coming soon.")


    def run_polling(self):
        """Run the bot in polling mode"""
        logger.info("Starting StreamFlix Bot...")
        self.application.run_polling()

    def run_webhook(self, webhook_url, port=8443):
        """Run the bot in webhook mode"""
        logger.info(f"Starting StreamFlix Bot with webhook: {webhook_url}")
        self.application.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=webhook_url
        )

