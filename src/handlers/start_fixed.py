#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Start Handler
============

Handles the /start command and main menu functionality.
"""

import logging
from datetime import datetime
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.utils.localization_core import get_text


class StartHandler:
    """Handles start command and main menu."""

    def __init__(self, bot_manager, config, db_manager):
        self.bot_manager = bot_manager
        self.config = config
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user = update.effective_user
        user_id = user.id

        # Check if user exists in database
        db_user = await self.bot_manager.db.get_user(user_id)

        if not db_user:
            # Create new user
            await self.bot_manager.db.create_user(
                user_id=user_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code
            )
            self.logger.info(f"New user registered: {user_id}")

        # Check subscription requirements
        if self.config.REQUIRED_CHANNELS:
            unsubscribed_channels = await self.bot_manager.check_user_subscription(user_id)
            if unsubscribed_channels:
                lang = getattr(db_user, 'language_code', None) or getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
                await self._send_subscription_required_message(update, unsubscribed_channels, lang=lang)
                return

        # Send welcome message
        lang = getattr(db_user, 'language_code', None) or getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        await self._send_welcome_message(update, user, lang=lang)

    async def _send_subscription_required_message(self, update: Update, unsubscribed_channels: list, lang=None):
        """Send subscription required message."""
        if lang is None:
            user = update.effective_user
            db_user = await self.bot_manager.db.get_user(user.id)
            lang = getattr(db_user, 'language_code', None) or getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = get_text('msg_subscription_required', lang, channels='\n'.join([f"@{c['name']}" for c in unsubscribed_channels]))

        keyboard = []
        for channel in unsubscribed_channels:
            keyboard.append([
                InlineKeyboardButton(f"\U0001F4E2 {channel['name']}", url=channel['url'])
            ])

        keyboard.append([InlineKeyboardButton(get_text('button_check_subscription', lang), callback_data="check_subscription")])
        keyboard.append([InlineKeyboardButton(get_text('button_back', lang), callback_data="main_menu")])

        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _send_welcome_message(self, update: Update, user, message_object=None, lang=None):
        """Send welcome message with main menu."""
        if lang is None:
            db_user = await self.bot_manager.db.get_user(user.id)
            lang = getattr(db_user, 'language_code', None) or getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = get_text('msg_welcome', lang)

        keyboard = [
            [
                InlineKeyboardButton(get_text('button_download_menu', lang), callback_data="download_menu"),
                InlineKeyboardButton(get_text('button_user_stats', lang), callback_data="user_stats")
            ],
            [
                InlineKeyboardButton(get_text('button_settings', lang), callback_data="settings_menu"),
                InlineKeyboardButton(get_text('button_help', lang), callback_data="help_menu")
            ],
            [
                InlineKeyboardButton(get_text('button_admin_panel', lang), callback_data="admin_menu"),
                InlineKeyboardButton(get_text('button_check_subscription', lang), callback_data="check_subscription")
            ]
        ]

        if message_object:
            try:
                await message_object.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                if "Message is not modified" in str(e):
                    # Ignore this error as it means the message is already up to date
                    pass
                else:
                    raise e
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries."""
        query = update.callback_query
        data = query.data if query else None

        if not query:
            return

        # Route to appropriate handler
        if data == "main_menu":
            await self._send_welcome_message(update, query.from_user, message_object=query.message)
        elif data == "download_menu":
            await self._show_download_menu(update, context, message_object=query.message)
        elif data == "user_stats":
            await self._show_user_stats(update, context, message_object=query.message)
        elif data == "settings_menu":
            await self._show_settings_menu(update, context, message_object=query.message)
        elif data == "help_menu":
            await self._show_help_menu(update, context, message_object=query.message)
        elif data == "admin_menu":
            await self._show_admin_menu(update, context, message_object=query.message)
        elif data == "check_subscription":
            await self._check_subscription_callback(update, context)
        elif data == "detailed_report":
            await self._show_user_stats(update, context, message_object=query.message)
        elif data == "download_history":
            await self._show_download_menu(update, context, message_object=query.message)
        elif data == "change_language":
            await self._show_settings_menu(update, context, message_object=query.message)
        elif data == "change_timezone":
            await self._show_settings_menu(update, context, message_object=query.message)
        elif data == "notification_settings":
            await self._show_settings_menu(update, context, message_object=query.message)
        elif data == "storage_settings":
            await self._show_settings_menu(update, context, message_object=query.message)
        elif data == "full_commands":
            await self._show_help_menu(update, context, message_object=query.message)
        elif data == "faq":
            await self._show_help_menu(update, context, message_object=query.message)
        elif data == "support":
            await self._show_help_menu(update, context, message_object=query.message)
        elif data == "terms":
            await self._show_help_menu(update, context, message_object=query.message)
        elif data == "admin_stats":
            await self._show_admin_menu(update, context, message_object=query.message)
        elif data == "admin_users":
            await self._show_admin_menu(update, context, message_object=query.message)
        elif data == "admin_broadcast":
            await self._show_admin_menu(update, context, message_object=query.message)
        elif data == "admin_settings":
            await self._show_admin_menu(update, context, message_object=query.message)
        elif data == "admin_logs":
            await self._show_admin_menu(update, context, message_object=query.message)
        elif data == "admin_backup":
            await self._show_admin_menu(update, context, message_object=query.message)

    async def _check_subscription_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle subscription check callback."""
        query = update.callback_query
        user_id = query.from_user.id

        if self.config.REQUIRED_CHANNELS:
            unsubscribed_channels = await self.bot_manager.check_user_subscription(user_id)
            if unsubscribed_channels:
                await query.answer("❌ يجب الاشتراك في جميع القنوات المطلوبة", show_alert=True)
                return

        await query.answer("✅ تم التحقق من الاشتراك بنجاح!", show_alert=True)
        await self._send_welcome_message(update, query.from_user, message_object=query.message)

    async def _show_download_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        """Show download menu."""
        text = """📥 تحميل الملفات

🔗 أرسل رابط الملف الذي تريد تحميله
📎 أو أرسل ملف لرفعه وإدارته

📋 الصيغ المدعومة:
• فيديو: MP4, AVI, MKV
• صوت: MP3, WAV, FLAC
• صور: JPG, PNG, GIF
• مستندات: PDF, DOC, ZIP

⚡ الحد الأقصى للحجم: 50 MB"""

        keyboard = [
            [InlineKeyboardButton("📋 سجل التحميلات", callback_data="download_history")],
            [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]
        ]

        if message_object:
            try:
                await message_object.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                if "Message is not modified" in str(e):
                    # Ignore this error as it means the message is already up to date
                    pass
                else:
                    raise e
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def _show_user_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        """Show user statistics."""
        user_id = update.effective_user.id
        stats = await self.bot_manager.get_user_stats(user_id)

        if not stats:
            if message_object:
                await message_object.answer("❌ لا توجد إحصائيات متاحة")
            else:
                await update.message.reply_text("❌ لا توجد إحصائيات متاحة")
            return

        user_info = stats['user_info']
        download_stats = stats['download_stats']
        activity_stats = stats['activity_stats']

        text = f"""📊 إحصائياتك الشخصية

👤 معلومات المستخدم:
• الاسم: {user_info['first_name']}
• تاريخ التسجيل: {user_info['registration_date'].strftime('%Y-%m-%d')}
• آخر نشاط: {user_info['last_activity'].strftime('%Y-%m-%d %H:%M')}
• اللغة: {user_info['language']}

📥 إحصائيات التحميل:
• إجمالي التحميلات: {download_stats['total_downloads']}
• التحميلات الناجحة: {download_stats['successful_downloads']}
• التحميلات الفاشلة: {download_stats['failed_downloads']}
• معدل النجاح: {download_stats['success_rate']:.1f}%
• الحجم الإجمالي: {download_stats['total_size_mb']} MB
• المساحة المستخدمة: {download_stats['storage_used_mb']} MB

📈 إحصائيات النشاط:
• إجمالي الأنشطة: {activity_stats['total_actions']}
• متوسط الأنشطة اليومية: {activity_stats['avg_daily_actions']}"""

        keyboard = [
            [InlineKeyboardButton("📊 تقرير مفصل", callback_data="detailed_report")],
            [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]
        ]

        if message_object:
            try:
                await message_object.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                if "Message is not modified" in str(e):
                    # Ignore this error as it means the message is already up to date
                    pass
                else:
                    raise e
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def _show_settings_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show settings menu."""
        if lang is None:
            user_id = update.effective_user.id
            db_user = await self.bot_manager.db.get_user(user_id)
            lang = getattr(db_user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = get_text('msg_settings', lang)
        keyboard = [
            [
                InlineKeyboardButton(get_text('button_language_ar', lang), callback_data="change_language"),
                InlineKeyboardButton(get_text('button_timezone', lang), callback_data="change_timezone")
            ],
            [
                InlineKeyboardButton(get_text('button_notifications', lang), callback_data="notification_settings"),
                InlineKeyboardButton(get_text('button_storage', lang), callback_data="storage_settings")
            ],
            [InlineKeyboardButton(get_text('button_back', lang), callback_data="main_menu")]
        ]
        if message_object:
            try:
                await message_object.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                if "Message is not modified" in str(e):
                    # Ignore this error as it means the message is already up to date
                    pass
                else:
                    raise e
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def _show_help_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show help menu."""
        if lang is None:
            db_user = await self.bot_manager.db.get_user(update.effective_user.id)
            lang = getattr(db_user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = get_text('msg_help', lang)
        keyboard = [
            [
                InlineKeyboardButton(get_text('button_full_commands', lang), callback_data="full_commands"),
                InlineKeyboardButton(get_text('button_faq', lang), callback_data="faq")
            ],
            [
                InlineKeyboardButton(get_text('button_support', lang), callback_data="support"),
                InlineKeyboardButton(get_text('button_terms', lang), callback_data="terms")
            ],
            [InlineKeyboardButton(get_text('button_back', lang), callback_data="main_menu")]
        ]
        if message_object:
            try:
                await message_object.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                if "Message is not modified" in str(e):
                    # Ignore this error as it means the message is already up to date
                    pass
                else:
                    raise e
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def _show_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show admin menu."""
        user_id = update.effective_user.id

        if not await self.bot_manager.is_user_admin(user_id):
            if message_object:
                await message_object.answer("❌ غير مصرح لك بالوصول لهذه القائمة", show_alert=True)
            else:
                await update.message.reply_text("❌ غير مصرح لك بالوصول لهذه القائمة")
            return

        if lang is None:
            db_user = await self.bot_manager.db.get_user(user_id)
            lang = getattr(db_user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = get_text('msg_admin_panel', lang)
        keyboard = [
            [
                InlineKeyboardButton(get_text('button_admin_stats', lang), callback_data="admin_stats"),
                InlineKeyboardButton(get_text('button_admin_users', lang), callback_data="admin_users")
            ],
            [
                InlineKeyboardButton(get_text('button_admin_broadcast', lang), callback_data="admin_broadcast"),
                InlineKeyboardButton(get_text('button_admin_settings', lang), callback_data="admin_settings")
            ],
            [
                InlineKeyboardButton(get_text('button_admin_logs', lang), callback_data="admin_logs"),
                InlineKeyboardButton(get_text('button_admin_backup', lang), callback_data="admin_backup")
            ],
            [InlineKeyboardButton(get_text('button_back', lang), callback_data="main_menu")]
        ]
        if message_object:
            try:
                await message_object.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                if "Message is not modified" in str(e):
                    # Ignore this error as it means the message is already up to date
                    pass
                else:
                    raise e
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
