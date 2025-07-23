
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Advanced Telegram Bot
===================

A feature-rich Telegram bot with advanced capabilities including:
- File downloading and management
- User analytics and statistics
- Scheduled tasks and automation
- Admin panel and user management
- Backup and security features
- Multi-language support
- AI-powered responses (optional)

Author: Advanced Bot Developer
Version: 2.0.0
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
import subprocess

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ChatMemberHandler
)
# Import configuration
from config import Config

# Import core modules
from src.core.database import DatabaseManager
from src.core.bot_manager import BotManager
from src.utils.logger import setup_logging
from src.utils.error_handler import error_handler
from src.middleware.rate_limiter import RateLimiter
from src.middleware.auth import AuthMiddleware

# Import handlers
from src.handlers.start import StartHandler
from src.handlers.admin import AdminHandler
from src.handlers.download import DownloadHandler
from src.handlers.user_management import UserHandler
from src.handlers.analytics import AnalyticsHandler

# Import services
from src.services.notification_service import AdvancedNotificationService
from src.services.analytics_service import AdvancedAnalyticsService

# فلتر مخصص: يعالج فقط إذا كان هناك انتظار إداري
from telegram.ext import filters

def admin_waiting_filter(update):
    context = update.application.context if hasattr(update, 'application') and hasattr(update.application, 'context') else None
    if not context or not hasattr(context, 'user_data'):
        return False
    user_data = context.user_data
    return (
        user_data.get('awaiting_broadcast_message') or
        user_data.get('awaiting_forced_channel') or
        user_data.get('awaiting_section_message') or
        user_data.get('awaiting_section_max')
    )

class AdvancedTelegramBot:
    """Main bot class that orchestrates all components."""

    def __init__(self):
        """Initialize the bot with all components."""
        self.logger = setup_logging()
        self.config = Config()
        self._auto_update_dependencies()
        self.application = (
            Application.builder()
            .token(self.config.TELEGRAM_BOT_TOKEN)
            .build()
        )
        self.logger.info(f"Application initialized: {self.application}")
        self.db_manager = DatabaseManager(self.config.DATABASE_URL)
        self.services = {}
        self.handlers = {}
        self.bot_manager = BotManager(self.application, self.config, self.db_manager)
        self.running = True

    def _auto_update_dependencies(self):
        """Automatically update yt-dlp and ffmpeg on startup."""
        import platform
        import zipfile
        import shutil
        import urllib.request
        import tempfile
        import os
        try:
            self.logger.info("Updating yt-dlp via pip...")
            subprocess.run(["pip", "install", "-U", "yt-dlp"], check=True)
            self.logger.info("Updating yt-dlp binary (if installed)...")
            subprocess.run(["yt-dlp", "-U"], check=False)
        except Exception as e:
            self.logger.warning(f"[AUTO-UPDATE] Failed to update yt-dlp: {e}")
        # تحديث ffmpeg تلقائياً على ويندوز
        try:
            ffmpeg_dir = os.path.join("data", "ffmpeg")
            ffmpeg_exe = os.path.join(ffmpeg_dir, "ffmpeg.exe")
            need_update = False
            if platform.system() == "Windows":
                # تحقق من وجود ffmpeg
                if not os.path.exists(ffmpeg_exe):
                    need_update = True
                else:
                    # تحقق من الإصدار الحالي
                    result = subprocess.run([ffmpeg_exe, "-version"], capture_output=True, text=True)
                    if result.returncode != 0 or "ffmpeg version" not in result.stdout:
                        need_update = True
                if need_update:
                    self.logger.info("Downloading latest ffmpeg for Windows...")
                    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
                        urllib.request.urlretrieve(url, tmp_zip.name)
                        with zipfile.ZipFile(tmp_zip.name, 'r') as zip_ref:
                            # ابحث عن ffmpeg.exe في الأرشيف
                            for member in zip_ref.namelist():
                                if member.endswith("/ffmpeg.exe"):
                                    zip_ref.extract(member, ffmpeg_dir)
                                    # انسخ ffmpeg.exe إلى الجذر
                                    src = os.path.join(ffmpeg_dir, member)
                                    shutil.copy2(src, ffmpeg_exe)
                                    break
                    self.logger.info(f"ffmpeg updated and extracted to {ffmpeg_exe}")
                # أضف ffmpeg_dir إلى PATH مؤقتاً
                os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
            else:
                # على أنظمة أخرى فقط تحقق من وجود ffmpeg
                subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            self.logger.warning(f"[AUTO-UPDATE] Could not check/update ffmpeg: {e}")

    def register_handlers(self):
        """Register all command and callback handlers."""
        # إنشاء الهاندلرز
        start_handler = StartHandler(self.bot_manager, self.config, self.db_manager)
        admin_handler = AdminHandler(self.bot_manager, self.config, self.db_manager)
        download_handler = DownloadHandler(self.bot_manager, self.config, self.db_manager)
        user_handler = UserHandler(self.bot_manager, self.config, self.db_manager)
        analytics_handler = AnalyticsHandler(self.bot_manager, self.config, self.db_manager)

        # ربط الهاندلرز مع bot_manager (للوصول المتبادل)
        self.bot_manager.set_admin_handler(admin_handler)
        self.bot_manager.set_user_handler(user_handler)

        # ربط الأوامر الأساسية
        self.application.add_handler(CommandHandler("start", start_handler.handle))
        self.application.add_handler(CommandHandler("help", start_handler._show_help_menu))
        self.application.add_handler(CommandHandler("admin", admin_handler.handle_command))
        self.application.add_handler(CommandHandler("stats", analytics_handler.handle_command))
        self.application.add_handler(CommandHandler("user_stats", analytics_handler.handle_command))
        self.application.add_handler(CommandHandler("profile", user_handler.handle_command))
        self.application.add_handler(CommandHandler("settings", user_handler.handle_command))
        self.application.add_handler(CommandHandler("language", user_handler.handle_command))
        self.application.add_handler(CommandHandler("timezone", user_handler.handle_command))
        self.application.add_handler(CommandHandler("notifications", user_handler.handle_command))
        self.application.add_handler(CommandHandler("privacy", user_handler.handle_command))
        self.application.add_handler(CommandHandler("export", user_handler.handle_command))
        self.application.add_handler(CommandHandler("delete", user_handler.handle_command))
        self.application.add_handler(CommandHandler("broadcast", admin_handler.handle_command))
        self.application.add_handler(CommandHandler("ban", admin_handler.handle_command))
        self.application.add_handler(CommandHandler("unban", admin_handler.handle_command))
        self.application.add_handler(CommandHandler("logs", admin_handler.handle_command))
        self.application.add_handler(CommandHandler("maintenance", admin_handler.handle_command))
        self.application.add_handler(CommandHandler("backup", admin_handler.handle_command))
        self.application.add_handler(CommandHandler("restart", admin_handler.handle_command))
        self.application.add_handler(CommandHandler("users", admin_handler.handle_command))

        # أولوية: هاندلر الإدارة أولاً لأي رسالة نصية
        self.application.add_handler(MessageHandler(filters.TEXT, admin_handler.handle_message), group=0)
        # ثم هاندلر التحميل للروابط فقط
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"https?://"), download_handler.handle_url), group=1)
        # ثم هاندلر البحث التلقائي لأي نص عادي (ليس رابط)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.Regex(r"https?://"), download_handler.handle_message), group=2)
        # ربط استقبال الملفات
        self.application.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO, download_handler.handle_file))

        # ربط جميع الكول باك (الأزرار) - يجب أن يكون أول واحد وبدون pattern مؤقتًا
        self.application.add_handler(CallbackQueryHandler(download_handler.handle_callback))
        self.application.add_handler(CallbackQueryHandler(start_handler.handle_callback, pattern=r"^(download_menu|user_stats|settings_menu|help_menu|admin_menu|check_subscription|main_menu|detailed_report|change_language|change_timezone|notification_settings|storage_settings|full_commands|faq|support|terms|admin_stats|admin_users|admin_broadcast|admin_settings|admin_logs)$"))
        self.application.add_handler(CallbackQueryHandler(user_handler.handle_callback, pattern=r"^(user_.*|profile_.*)$"))
        self.application.add_handler(CallbackQueryHandler(admin_handler.handle_callback, pattern=r"^admin_.*|admin_detailed_stats$"))
        self.application.add_handler(CallbackQueryHandler(analytics_handler.handle_callback, pattern=r"^analytics_.*|stats_.*"))
        self.application.add_handler(CallbackQueryHandler(
            download_handler.handle_callback,
            pattern=r"^(ytpl_dl\||cancel_playlist|cancel_download_|cancel_playlist|download_details_|share_file_|delete_download_|file_details_|delete_file_|dlv\||dla\||dlva\||dpi\||dpa\||dpaa\||dpop\||dpopv\||dpopa\||ppg\||ytsearch_.*)$"
        ))
        user_management_pattern = r"^(admin_users_management|admin_list_users(_page)?(:\d+)?|admin_search_user|admin_banned_users(_page)?(:\d+)?|admin_premium_users(_page)?(:\d+)?|admin_user_analytics|admin_activity_report|admin_user_settings|admin_mass_notifications|admin_user_details(:\d+:\d+)?|admin_ban_user(:\d+:\d+)?|admin_unban_user(:\d+:\d+)?|admin_premium(:\d+:\d+)?|admin_unpremium(:\d+:\d+)?|back_to_users_management)$"
        self.application.add_handler(CallbackQueryHandler(admin_handler.handle_callback, pattern=user_management_pattern))
        stats_pattern = r"^(admin_export_stats|admin_refresh_stats|admin_charts|admin_detailed_report)$"
        self.application.add_handler(CallbackQueryHandler(admin_handler.handle_callback, pattern=stats_pattern))

        # إضافة هاندلر الأخطاء
        self.application.add_error_handler(error_handler)
        self.application.add_handler(ChatMemberHandler(self.bot_manager.handle_my_chat_member, chat_member_types=ChatMemberHandler.MY_CHAT_MEMBER))

    def run(self):
        self.logger.info("Starting AdvancedTelegramBot...")
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.db_manager.initialize())
        # جدولة المهام الدورية بعد تهيئة كل شيء
        loop.run_until_complete(self.bot_manager.start_background_tasks())
        self.register_handlers()
        self.logger.info("Bot started. Running polling...")
        self.application.run_polling()

def main():
    bot = AdvancedTelegramBot()
    bot.run()

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")
