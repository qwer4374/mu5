#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from typing import List
from pathlib import Path

class Config:
    """Configuration class for the advanced Telegram bot."""

    # Bot Configuration
    VERSION = "2.0.0"
    TELEGRAM_BOT_TOKEN = "1862186312:AAEgq9cIQDbf2MitTjDMjYKPgdD9eGCPSlI"
    OWNER_ID = 697852646
    ADMIN_USER_IDS = [697852646]  # Owner is automatically admin

    # Database Configuration
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///advanced_telegram_bot.db")

    # Logging Configuration
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FILE = "logs/bot.log"

    # Download Configuration
    DOWNLOAD_DIRECTORY = os.environ.get("DOWNLOAD_DIRECTORY", "downloads")
    MAX_DOWNLOAD_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_FORMATS = ['mp4', 'mp3', 'pdf', 'jpg', 'png', 'gif', 'zip', 'rar']

    # Subscription Configuration
    FORCED_SUBSCRIPTION_CHANNELS = []  # List of channel usernames/IDs
    REQUIRED_CHANNELS = []  # List of required channels for subscription
    SUBSCRIPTION_MESSAGE = "🔒 للاستفادة من جميع ميزات البوت، يرجى الاشتراك في القنوات التالية:\n\n{channels}\n\n✅ بعد الاشتراك، اضغط /start للمتابعة"

    # Bot Features Configuration
    WELCOME_MESSAGE = """
🤖 مرحباً بك في البوت المتطور!

🌟 الميزات المتاحة:
📥 تحميل الملفات من الروابط
📊 إحصائيات مفصلة
👥 إدارة المستخدمين
📢 إرسال رسائل جماعية
⏰ جدولة المهام
🔒 نظام الاشتراك الإجباري
💾 نسخ احتياطي للبيانات
🎨 واجهة تفاعلية متطورة

📝 استخدم /help لعرض جميع الأوامر المتاحة
    """

    # Security Configuration
    RATE_LIMIT_REQUESTS = 10  # requests per minute
    RATE_LIMIT_WINDOW = 60   # seconds

    # Backup Configuration
    BACKUP_INTERVAL = 24 * 60 * 60  # 24 hours in seconds
    BACKUP_DIRECTORY = "backups"
    AUTO_BACKUP_ENABLED = True  # تفعيل النسخ الاحتياطي التلقائي

    # Notification Configuration
    NOTIFICATION_CHANNELS = []  # Channels to send notifications
    SMART_NOTIFICATIONS_ENABLED = True  # تفعيل الإشعارات الذكية

    # Channel/Group Integration
    TARGET_CHANNELS = []  # قائمة القنوات أو المجموعات لنشر الملفات أو الإشعارات تلقائياً

    # Advanced Features
    ENABLE_AI_RESPONSES = False
    ENABLE_ANALYTICS = True
    ENABLE_WEBHOOKS = False
    WEBHOOK_URL = ""

    # File Processing
    ENABLE_FILE_PREVIEW = True
    ENABLE_FILE_COMPRESSION = True
    ENABLE_VIRUS_SCAN = False

    # User Experience
    LANGUAGE_DEFAULT = "ar"
    TIMEZONE_DEFAULT = "Asia/Riyadh"
    ENABLE_VOICE_MESSAGES = True

    @classmethod
    def validate_config(cls):
        """Validate configuration settings."""
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")

        if not cls.OWNER_ID:
            raise ValueError("OWNER_ID is required")

        # Create necessary directories
        Path(cls.DOWNLOAD_DIRECTORY).mkdir(parents=True, exist_ok=True)
        Path(cls.BACKUP_DIRECTORY).mkdir(parents=True, exist_ok=True)
        Path("logs").mkdir(parents=True, exist_ok=True)
        return True

