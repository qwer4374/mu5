#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
User Management Handler
======================

Handles user profile, settings, and management functionality.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import os
from src.utils.localization_core import get_text


class UserHandler:
    """Handles user management functionality."""

    def __init__(self, bot_manager, config, db_manager):
        self.bot_manager = bot_manager
        self.config = config
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)

    async def handle_command(self, update, context):
        """Handle user management commands."""
        command = update.message.text.lower()
        user_id = update.effective_user.id
        db_user = await self.bot_manager.db.get_user(user_id)
        lang = getattr(db_user, 'language_code', None) or getattr(update.effective_user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'

        if command == "/profile":
            await self._show_user_profile(update, context, lang=lang)
        elif command == "/settings":
            await self._show_user_settings(update, context, lang=lang)
        elif command == "/stats":
            await self._show_user_stats(update, context, lang=lang)
        elif command == "/help":
            await self._show_user_help(update, context, lang=lang)
        else:
            await update.message.reply_text(get_text('msg_unknown_command', lang))

    def get_settings_keyboard(self, lang='ar'):
        """Get settings keyboard with proper localization."""
        return [
            [
                InlineKeyboardButton(get_text('button_language_ar', lang), callback_data="user_set_language:ar"),
                InlineKeyboardButton(get_text('button_language_en', lang), callback_data="user_set_language:en")
            ],
            [InlineKeyboardButton(get_text('button_timezone', lang), callback_data="user_timezone_settings")],
            [InlineKeyboardButton(get_text('button_notifications', lang), callback_data="user_notification_settings"), InlineKeyboardButton(get_text('button_privacy_settings', lang), callback_data="user_privacy_settings")],
            [InlineKeyboardButton(get_text('button_user_analytics', lang), callback_data="user_analytics"), InlineKeyboardButton(get_text('button_user_downloads', lang), callback_data="user_downloads")],
            [InlineKeyboardButton(get_text('button_back', lang), callback_data="user_profile")]
        ]

    def get_profile_keyboard(self):
        """Get profile keyboard."""
        return [
            [
                InlineKeyboardButton("📊 تقرير مفصل", callback_data="user_detailed_report"),
                InlineKeyboardButton("🏆 الإنجازات", callback_data="user_achievements")
            ],
            [
                InlineKeyboardButton("⚙️ الإعدادات", callback_data="user_edit_settings"),
                InlineKeyboardButton("📈 الإحصائيات", callback_data="user_analytics")
            ],
            [
                InlineKeyboardButton("📥 تصدير البيانات", callback_data="user_export_data"),
                InlineKeyboardButton("🗑️ حذف الحساب", callback_data="user_delete_account")
            ]
        ]

    async def _show_user_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show user profile."""
        user_id = update.effective_user.id
        user = await self.bot_manager.db.get_user(user_id)
        if lang is None:
            lang = getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'

        if not user:
            await update.message.reply_text(get_text('msg_user_not_found', lang))
            return

        # Get user statistics
        stats = await self._get_user_statistics(user_id)
        level_info = self._calculate_user_level(stats['download_stats']['total_downloads'])
        badges = self._get_user_badges(stats)

        # Format registration date
        reg_date = user.registration_date.strftime("%Y-%m-%d") if user.registration_date else get_text('msg_not_specified', lang)
        last_activity = user.last_activity.strftime("%Y-%m-%d %H:%M") if user.last_activity else get_text('msg_not_specified', lang)

        text = get_text('msg_profile', lang) + "\n\n" + get_text('msg_user_info', lang) + "\n" + get_text('msg_name', lang) + f": {user.first_name or get_text('msg_not_specified', lang)}\n" + get_text('msg_username', lang) + f": @{user.username or get_text('msg_not_specified', lang)}\n" + get_text('msg_user_id', lang) + f": {user.id}\n" + get_text('msg_registration_date', lang) + f": {reg_date}\n" + get_text('msg_last_activity', lang) + f": {last_activity}\n" + get_text('msg_language', lang) + f": {user.language_code or 'ar'}\n"

        text += get_text('msg_achievements', lang) + "\n" + get_text('msg_level', lang) + f": {level_info['level']} {level_info['title']}\n" + get_text('msg_points', lang) + f": {level_info['points']:,} {get_text('msg_progress', lang)}: {level_info['progress']:.1f}%\n\n"

        text += get_text('msg_quick_stats', lang) + "\n" + get_text('msg_total_downloads', lang) + f": {stats['download_stats']['total_downloads']}\n" + get_text('msg_success_rate', lang) + f": {stats['download_stats']['success_rate']:.1f}%\n" + get_text('msg_total_size', lang) + f": {stats['download_stats']['total_size_mb']:.1f} {get_text('msg_mb', lang)}\n" + get_text('msg_total_activities', lang) + f": {stats['activity_stats']['total_actions']}\n\n"

        text += get_text('msg_badges', lang) + "\n" + self._format_badges(badges)

        keyboard = self.get_profile_keyboard()

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

    async def _show_user_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        # دعم كل من Update و CallbackQuery
        if hasattr(update, 'effective_user') and update.effective_user:
            user_id = update.effective_user.id
        elif hasattr(update, 'from_user') and update.from_user:
            user_id = update.from_user.id
        elif hasattr(message_object, 'chat') and hasattr(message_object.chat, 'id'):
            user_id = message_object.chat.id
        else:
            user_id = None
        user = await self.bot_manager.db.get_user(user_id)
        if lang is None:
            lang = getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        settings = user.settings or {}
        text = get_text('msg_settings', lang) + "\n\n" + get_text('msg_language', lang) + f": {user.language_code or 'ar'}\n" + get_text('msg_timezone', lang) + f": {user.timezone or 'Asia/Baghdad'}"
        keyboard = self.get_settings_keyboard(lang)
        if message_object:
            try:
                await message_object.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            except Exception as e:
                if "Message is not modified" in str(e):
                    pass
                else:
                    raise e
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def _change_language(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Change user language."""
        if lang is None:
            user_id = update.effective_user.id
            db_user = await self.bot_manager.db.get_user(user_id)
            lang = getattr(db_user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = get_text('msg_change_language', lang) + "\n\n" + get_text('msg_choose_language', lang)
        keyboard = [
            [InlineKeyboardButton(get_text('button_language_ar', lang), callback_data="user_set_language:ar"), InlineKeyboardButton(get_text('button_language_en', lang), callback_data="user_set_language:en")],
            [InlineKeyboardButton(get_text('button_back_to_settings', lang), callback_data="user_settings")]
        ]
        if message_object:
            try:
                await message_object.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            except Exception as e:
                if "Message is not modified" in str(e):
                    pass
                else:
                    raise e
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def _change_timezone(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Change user timezone."""
        if lang is None:
            user_id = update.effective_user.id
            db_user = await self.bot_manager.db.get_user(user_id)
            lang = getattr(db_user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = get_text('msg_change_timezone', lang) + "\n\n" + get_text('msg_choose_timezone', lang)
        keyboard = [
            [InlineKeyboardButton(get_text('button_timezone_baghdad', lang), callback_data="user_set_timezone:Asia/Baghdad")],
            [InlineKeyboardButton(get_text('button_timezone_new_york', lang), callback_data="user_set_timezone:America/New_York")],
            [InlineKeyboardButton(get_text('button_timezone_moscow', lang), callback_data="user_set_timezone:Europe/Moscow")],
            [InlineKeyboardButton(get_text('button_timezone_beijing', lang), callback_data="user_set_timezone:Asia/Shanghai")],
            [InlineKeyboardButton(get_text('button_back_to_settings', lang), callback_data="user_settings")]
        ]
        if message_object:
            try:
                await message_object.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            except Exception as e:
                if "Message is not modified" in str(e):
                    pass
                else:
                    raise e
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def _manage_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Manage user notifications."""
        user_id = update.effective_user.id
        user = await self.bot_manager.db.get_user(user_id)
        if lang is None:
            lang = getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        settings = user.settings or {}

        text = get_text('msg_manage_notifications', lang) + "\n\n" + get_text('msg_current_settings', lang) + "\n\n"

        text += get_text('msg_download_notifications', lang) + "\n" + get_text('msg_download_start', lang) + f": {'🟢' if settings.get('notify_download_start', True) else '🔴'}\n" + get_text('msg_download_complete', lang) + f": {'🟢' if settings.get('notify_download_complete', True) else '🔴'}\n" + get_text('msg_download_failed', lang) + f": {'🟢' if settings.get('notify_download_failed', True) else '🔴'}\n\n"

        text += get_text('msg_system_notifications', lang) + "\n" + get_text('msg_bot_updates', lang) + f": {'🟢' if settings.get('notify_bot_updates', True) else '🔴'}\n" + get_text('msg_admin_messages', lang) + f": {'🟢' if settings.get('notify_admin_messages', True) else '🔴'}\n" + get_text('msg_security_alerts', lang) + f": {'🟢' if settings.get('notify_security_alerts', True) else '🔴'}\n\n"

        text += get_text('msg_notification_timing', lang) + "\n" + get_text('msg_night_notifications', lang) + f": {'🟢 مفعلة' if settings.get('night_notifications', False) else '🔴 معطلة'}\n" + get_text('msg_quiet_hours', lang) + f": {settings.get('quiet_hours', '22:00-08:00')}\n\n"

        text += get_text('msg_notification_type', lang) + "\n" + get_text('msg_sound_notifications', lang) + f": {'🟢' if settings.get('sound_notifications', False) else '🔴'}\n" + get_text('msg_vibration_notifications', lang) + f": {'🟢' if settings.get('vibration_notifications', True) else '🔴'}\n"

        keyboard = [
            [
                InlineKeyboardButton(get_text('button_download_notifications', lang), callback_data="user_download_notifications"),
                InlineKeyboardButton(get_text('button_system_notifications', lang), callback_data="user_system_notifications")
            ],
            [
                InlineKeyboardButton(get_text('button_notification_timing', lang), callback_data="user_notification_timing"),
                InlineKeyboardButton(get_text('button_notification_type', lang), callback_data="user_notification_type")
            ],
            [
                InlineKeyboardButton(get_text('button_disable_all_notifications', lang), callback_data="user_disable_all_notifications"),
                InlineKeyboardButton(get_text('button_enable_all_notifications', lang), callback_data="user_enable_all_notifications")
            ],
            [InlineKeyboardButton(get_text('button_back_to_settings', lang), callback_data="user_settings")]
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

    # Notification management functions
    async def _toggle_download_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Toggle download notifications."""
        user_id = update.effective_user.id
        user = await self.bot_manager.db.get_user(user_id)
        if lang is None:
            lang = getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        settings = user.settings or {}

        # Toggle download notifications
        current_setting = settings.get('notify_download_start', True)
        settings['notify_download_start'] = not current_setting
        settings['notify_download_complete'] = not current_setting
        settings['notify_download_failed'] = not current_setting

        # Update user settings
        await self.bot_manager.db.update_user(user_id, {'settings': settings})

        # Show updated notifications page
        await self._manage_notifications(update, context, message_object, lang=lang)

    async def _toggle_system_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Toggle system notifications."""
        user_id = update.effective_user.id
        user = await self.bot_manager.db.get_user(user_id)
        if lang is None:
            lang = getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        settings = user.settings or {}

        # Toggle system notifications
        current_setting = settings.get('notify_bot_updates', True)
        settings['notify_bot_updates'] = not current_setting
        settings['notify_admin_messages'] = not current_setting
        settings['notify_security_alerts'] = not current_setting

        # Update user settings
        await self.bot_manager.db.update_user(user_id, {'settings': settings})

        # Show updated notifications page
        await self._manage_notifications(update, context, message_object, lang=lang)

    async def _toggle_notification_timing(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Toggle notification timing."""
        user_id = update.effective_user.id
        user = await self.bot_manager.db.get_user(user_id)
        if lang is None:
            lang = getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        settings = user.settings or {}

        # Toggle night notifications
        current_setting = settings.get('night_notifications', False)
        settings['night_notifications'] = not current_setting

        # Update user settings
        await self.bot_manager.db.update_user(user_id, {'settings': settings})

        # Show updated notifications page
        await self._manage_notifications(update, context, message_object, lang=lang)

    async def _toggle_notification_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Toggle notification type."""
        user_id = update.effective_user.id
        user = await self.bot_manager.db.get_user(user_id)
        if lang is None:
            lang = getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        settings = user.settings or {}

        # Toggle sound notifications
        current_setting = settings.get('sound_notifications', False)
        settings['sound_notifications'] = not current_setting

        # Update user settings
        await self.bot_manager.db.update_user(user_id, {'settings': settings})

        # Show updated notifications page
        await self._manage_notifications(update, context, message_object, lang=lang)

    async def _disable_all_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Disable all notifications."""
        user_id = update.effective_user.id
        user = await self.bot_manager.db.get_user(user_id)
        if lang is None:
            lang = getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        settings = user.settings or {}

        # Disable all notifications
        settings['notify_download_start'] = False
        settings['notify_download_complete'] = False
        settings['notify_download_failed'] = False
        settings['notify_bot_updates'] = False
        settings['notify_admin_messages'] = False
        settings['notify_security_alerts'] = False
        settings['night_notifications'] = False
        settings['sound_notifications'] = False
        settings['vibration_notifications'] = False

        # Update user settings
        await self.bot_manager.db.update_user(user_id, {'settings': settings})

        # Show updated notifications page
        await self._manage_notifications(update, context, message_object, lang=lang)

    async def _enable_all_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Enable all notifications."""
        user_id = update.effective_user.id
        user = await self.bot_manager.db.get_user(user_id)
        if lang is None:
            lang = getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        settings = user.settings or {}

        # Enable all notifications
        settings['notify_download_start'] = True
        settings['notify_download_complete'] = True
        settings['notify_download_failed'] = True
        settings['notify_bot_updates'] = True
        settings['notify_admin_messages'] = True
        settings['notify_security_alerts'] = True
        settings['night_notifications'] = True
        settings['sound_notifications'] = True
        settings['vibration_notifications'] = True

        # Update user settings
        await self.bot_manager.db.update_user(user_id, {'settings': settings})

        # Show updated notifications page
        await self._manage_notifications(update, context, message_object, lang=lang)

    async def handle_callback(self, update, context):
        """Handle callback queries."""
        query = update.callback_query
        data = query.data if query else None

        if not query:
            return

        # Route to appropriate handler
        if data == "user_profile":
            await self._show_user_profile(update, context, message_object=query.message)
        elif data == "user_edit_settings":
            await self._show_user_settings(update, context, message_object=query.message)
        elif data == "user_detailed_report":
            await self._show_detailed_report(update, context, message_object=query.message)
        elif data == "user_achievements":
            await self._show_user_achievements(update, context, message_object=query.message)
        elif data == "user_analytics":
            await self._show_user_analytics(update, context, message_object=query.message)
        elif data == "user_export_data":
            await self._export_user_data(update, context, message_object=query.message)
        elif data == "user_privacy_settings":
            await self._privacy_settings(update, context, message_object=query.message)
        elif data == "user_confirm_delete":
            await self._confirm_delete_callback(query, context)
        elif data == "user_cancel_delete":
            await self._show_user_profile(update, context, message_object=query.message)
        elif data == "user_language_settings":
            await self._change_language(update, context, message_object=query.message)
        elif data == "user_timezone_settings":
            await self._change_timezone(update, context, message_object=query.message)
        elif data == "user_notification_settings":
            await self._manage_notifications(update, context, message_object=query.message)
        elif data == "user_downloads":
            await self._show_user_downloads(update, context, message_object=query.message)
        elif data == "user_settings":
            await self._show_user_settings(update, context, message_object=query.message)
        elif data == "user_download_notifications":
            await self._toggle_download_notifications(update, context, message_object=query.message)
        elif data == "user_system_notifications":
            await self._toggle_system_notifications(update, context, message_object=query.message)
        elif data == "user_notification_timing":
            await self._toggle_notification_timing(update, context, message_object=query.message)
        elif data == "user_notification_type":
            await self._toggle_notification_type(update, context, message_object=query.message)
        elif data == "user_disable_all_notifications":
            await self._disable_all_notifications(update, context, message_object=query.message)
        elif data == "user_enable_all_notifications":
            await self._enable_all_notifications(update, context, message_object=query.message)
        elif data == "user_cleanup_storage":
            await self._cleanup_storage(update, context, message_object=query.message)
        elif data == "user_storage_analysis":
            await self._storage_analysis(update, context, message_object=query.message)
        elif data == "user_clear_all_files":
            await self._clear_all_files(update, context, message_object=query.message)
        elif data.startswith("user_set_language:"):
            await self._set_language_callback(query, context)
        elif data.startswith("user_set_timezone:"):
            await self._set_timezone_callback(query, context)
        # أزرار العودة الموحدة لأي قيمة تحتوي على back أو عودة أو user_profile أو main_menu
        elif data and ("back" in data or "عودة" in data or data == "user_profile" or data == "main_menu"):
            await self._show_user_profile(update, context, message_object=query.message)
        elif data and data.startswith("toggle_show_stats:"):
            new_value = bool(int(data.split(":")[1]))
            user_id = query.from_user.id
            user = await self.bot_manager.db.get_user(user_id)
            settings = user.settings or {}
            settings['show_stats'] = new_value
            await self.bot_manager.db.update_user(user_id, {'settings': settings})
            await self._privacy_settings(update, context, message_object=query.message)
        elif data and data.startswith("toggle_save_activity_log:"):
            new_value = bool(int(data.split(":")[1]))
            user_id = query.from_user.id
            user = await self.bot_manager.db.get_user(user_id)
            settings = user.settings or {}
            settings['save_activity_log'] = new_value
            await self.bot_manager.db.update_user(user_id, {'settings': settings})
            await self._privacy_settings(update, context, message_object=query.message)
        else:
            await query.answer(get_text('msg_unknown_button', self.config.LANGUAGE_DEFAULT or 'ar'), show_alert=True)

    async def _set_language_callback(self, query, context):
        """Set user language from callback."""
        await query.answer()
        language = query.data.split(":")[1]
        user_id = query.from_user.id
        # Update user language in DB
        await self.bot_manager.db.update_user(user_id, {'language_code': language})
        # أعد تحميل بيانات المستخدم بعد التحديث
        db_user = await self.bot_manager.db.get_user(user_id)
        lang = db_user.language_code or self.config.LANGUAGE_DEFAULT or 'ar'
        language_names = {
            'ar': 'العربية',
            'en': 'English',
            'fr': 'Français',
            'es': 'Español',
            'de': 'Deutsch',
            'ru': 'Русский'
        }
        await query.edit_message_text(
            get_text('msg_language_changed_success', lang) + f" ({language_names.get(lang, lang)})"
        )
        # أعد عرض الإعدادات أو القائمة الرئيسية باللغة الجديدة
        await self._show_user_settings(query, context, message_object=query.message, lang=lang)

    async def _set_timezone_callback(self, query, context):
        """Set user timezone from callback."""
        await query.answer()

        timezone = query.data.split(":")[1]
        user_id = query.from_user.id

        # Update user timezone
        success = await self.bot_manager.db.update_user(
            user_id,
            {'timezone': timezone}
        )

        if success:
            await query.edit_message_text(
                get_text('msg_timezone_changed_success', self.config.LANGUAGE_DEFAULT or 'ar')
            )
        else:
            await query.edit_message_text(get_text('msg_timezone_change_failed', self.config.LANGUAGE_DEFAULT or 'ar'))

    # Helper methods
    async def _get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user statistics."""
        # Get downloads
        downloads = await self.bot_manager.db.get_user_downloads(user_id, limit=1000)

        # Calculate download stats
        total_downloads = len(downloads)
        successful_downloads = len([d for d in downloads if d.download_status == 'completed'])
        failed_downloads = len([d for d in downloads if d.download_status == 'failed'])
        success_rate = (successful_downloads / total_downloads * 100) if total_downloads > 0 else 0

        total_size_mb = sum(d.file_size or 0 for d in downloads) / (1024 * 1024)

        # Get activity stats
        analytics = await self.bot_manager.db.get_user_analytics(user_id, days=30)
        total_actions = len(analytics)

        # Calculate action breakdown
        action_breakdown = {}
        for analytic in analytics:
            action_type = analytic.action_type
            action_breakdown[action_type] = action_breakdown.get(action_type, 0) + 1

        return {
            'download_stats': {
                'total_downloads': total_downloads,
                'successful_downloads': successful_downloads,
                'failed_downloads': failed_downloads,
                'success_rate': success_rate,
                'total_size_mb': total_size_mb
            },
            'activity_stats': {
                'total_actions': total_actions,
                'action_breakdown': action_breakdown
            }
        }

    def _calculate_user_level(self, total_downloads: int) -> Dict[str, Any]:
        """Calculate user level based on downloads."""
        levels = [
            (0, "مبتدئ", "🥉"),
            (10, "متوسط", "🥈"),
            (50, "متقدم", "🥇"),
            (100, "خبير", "💎"),
            (500, "محترف", "👑"),
            (1000, "أسطورة", "🏆")
        ]

        current_level = levels[0]
        next_level = None

        for i, (threshold, title, icon) in enumerate(levels):
            if total_downloads >= threshold:
                current_level = (threshold, title, icon)
                if i + 1 < len(levels):
                    next_level = levels[i + 1]

        points = total_downloads * 10
        progress = 0

        if next_level:
            progress = ((total_downloads - current_level[0]) /
                       (next_level[0] - current_level[0])) * 100

        return {
            'level': current_level[2],
            'title': current_level[1],
            'points': points,
            'progress': progress
        }

    def _get_user_badges(self, stats: Dict[str, Any]) -> List[str]:
        """Get user badges based on achievements."""
        badges = []
        download_stats = stats['download_stats']

        if download_stats['total_downloads'] >= 10:
            badges.append(get_text('msg_active_downloader_badge', self.config.LANGUAGE_DEFAULT or 'ar'))

        if download_stats['success_rate'] >= 95:
            badges.append(get_text('msg_pro_downloader_badge', self.config.LANGUAGE_DEFAULT or 'ar'))

        if download_stats['total_size_mb'] >= 1000:
            badges.append(get_text('msg_data_collector_badge', self.config.LANGUAGE_DEFAULT or 'ar'))

        if stats['activity_stats']['total_actions'] >= 100:
            badges.append(get_text('msg_active_user_badge', self.config.LANGUAGE_DEFAULT or 'ar'))

        return badges

    def _format_badges(self, badges: List[str]) -> str:
        """Format badges for display."""
        if not badges:
            return get_text('msg_no_badges', self.config.LANGUAGE_DEFAULT or 'ar')

        return "\n".join([f"• {badge}" for badge in badges])

    # Placeholder methods for future implementation
    async def _show_user_achievements(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show user achievements."""
        if lang is None:
            lang = update.effective_user.language_code or self.config.LANGUAGE_DEFAULT or 'ar'
        if message_object:
            await message_object.edit_text(get_text('msg_achievements_page_under_development', lang))
        elif update.message:
            await update.message.reply_text(get_text('msg_achievements_page_under_development', lang))
        else:
            # Fallback for callback queries
            await context.bot.send_message(update.effective_chat.id, get_text('msg_achievements_page_under_development', lang))

    async def _show_user_analytics(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show user analytics (إحصائيات المستخدم)."""
        user_id = update.effective_user.id
        user = await self.bot_manager.db.get_user(user_id)
        if lang is None:
            lang = getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        stats = await self.bot_manager.db.get_user_stats(user_id)
        if not stats:
            text = get_text('msg_no_stats', lang) + "\n\n" + get_text('msg_analytics_page_under_development', lang)
        else:
            download_stats = stats.get('download_stats', {})
            activity_stats = stats.get('activity_stats', {})
            text = get_text('msg_analytics_page_title', lang) + "\n\n"
            text += f"• {get_text('msg_total_downloads', lang)}: {download_stats.get('total_downloads', 0)}\n"
            text += f"• {get_text('msg_success_rate', lang)}: {download_stats.get('success_rate', 0):.1f}%\n"
            text += f"• {get_text('msg_total_size', lang)}: {download_stats.get('total_size_mb', 0):.1f} {get_text('msg_mb', lang)}\n"
            text += f"• {get_text('msg_total_activities', lang)}: {activity_stats.get('total_actions', 0)}\n"
            text += f"• {get_text('msg_avg_daily_actions', lang)}: {activity_stats.get('avg_daily_actions', 0):.2f}\n"
        keyboard = [
            [InlineKeyboardButton(get_text('button_back', lang), callback_data="user_profile")]
        ]
        if message_object:
            await message_object.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_user_downloads(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show user downloads (قائمة التحميلات)."""
        user_id = update.effective_user.id
        user = await self.bot_manager.db.get_user(user_id)
        if lang is None:
            lang = getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        downloads = await self.bot_manager.db.get_user_downloads(user_id, limit=5)
        if not downloads:
            text = get_text('msg_no_stats', lang) + "\n\n" + get_text('msg_downloads_page_under_development', lang)
        else:
            text = get_text('msg_downloads_page_title', lang) + "\n\n"
            for i, d in enumerate(downloads, 1):
                status_emoji = "✅" if getattr(d, 'download_status', '') == "completed" else "❌"
                text += f"{i}. {status_emoji} {getattr(d, 'filename', 'ملف غير معروف')}\n"
                text += f"   📅 {d.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                if getattr(d, 'file_size', None):
                    text += f"   📊 {d.file_size / (1024*1024):.1f} MB\n"
                text += "\n"
        keyboard = [
            [InlineKeyboardButton(get_text('button_download_new', lang), callback_data="download_menu")],
            [InlineKeyboardButton(get_text('button_back', lang), callback_data="user_profile")]
        ]
        if message_object:
            await message_object.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_user_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE, lang=None):
        """Show user help."""
        if lang is None:
            lang = update.effective_user.language_code or self.config.LANGUAGE_DEFAULT or 'ar'
        if update.message:
            await update.message.reply_text(get_text('msg_help_page_under_development', lang))
        else:
            # Fallback for callback queries
            await context.bot.send_message(update.effective_chat.id, get_text('msg_help_page_under_development', lang))

    async def _show_user_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE, lang=None):
        """Show user stats."""
        if lang is None:
            lang = update.effective_user.language_code or self.config.LANGUAGE_DEFAULT or 'ar'
        if update.message:
            await update.message.reply_text(get_text('msg_stats_page_under_development', lang))
        else:
            # Fallback for callback queries
            await context.bot.send_message(update.effective_chat.id, get_text('msg_stats_page_under_development', lang))

    async def _privacy_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show privacy settings (إعدادات الخصوصية)."""
        user_id = update.effective_user.id
        user = await self.bot_manager.db.get_user(user_id)
        if lang is None:
            lang = getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        settings = user.settings or {}
        show_stats = settings.get('show_stats', True)
        save_activity_log = settings.get('save_activity_log', True)
        text = get_text('msg_privacy_settings', lang) + "\n\n"
        text += f"• {get_text('msg_show_stats', lang)}: {'🟢 مفعل' if show_stats else '🔴 معطل'}\n"
        text += f"• {get_text('msg_save_activity_log', lang)}: {'🟢 مفعل' if save_activity_log else '🔴 معطل'}\n"
        keyboard = [
            [InlineKeyboardButton(('🔒 ' if show_stats else '🔓 ') + get_text('msg_show_stats', lang), callback_data=f"toggle_show_stats:{int(not show_stats)}")],
            [InlineKeyboardButton(('💾 ' if save_activity_log else '🗑️ ') + get_text('msg_save_activity_log', lang), callback_data=f"toggle_save_activity_log:{int(not save_activity_log)}")],
            [InlineKeyboardButton(get_text('button_back', lang), callback_data="user_settings")]
        ]
        if message_object:
            await message_object.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def _export_user_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Export user data."""
        if lang is None:
            lang = update.effective_user.language_code or self.config.LANGUAGE_DEFAULT or 'ar'
        if message_object:
            await message_object.edit_text(get_text('msg_export_data_under_development', lang))
        elif update.message:
            await update.message.reply_text(get_text('msg_export_data_under_development', lang))
        else:
            # Fallback for callback queries
            await context.bot.send_message(update.effective_chat.id, get_text('msg_export_data_under_development', lang))

    async def _confirm_delete_callback(self, query, context):
        """Confirm account deletion."""
        await query.edit_message_text("❗️ تم تأكيد حذف الحساب (تحت التطوير)")

    async def _show_detailed_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show detailed user report."""
        user_id = update.effective_user.id
        stats = await self._get_user_statistics(user_id)
        if lang is None:
            lang = update.effective_user.language_code or self.config.LANGUAGE_DEFAULT or 'ar'

        if not stats:
            text = get_text('msg_no_stats_available_for_detailed_report', lang)
        else:
            download_stats = stats['download_stats']
            activity_stats = stats['activity_stats']
            user_level = self._calculate_user_level(download_stats['total_downloads'])

            text = get_text('msg_detailed_report', lang) + "\n\n" + get_text('msg_user_info', lang) + "\n" + get_text('msg_user_id', lang) + f": {user_id}\n" + get_text('msg_level', lang) + f": {user_level['level']} {user_level['title']}\n" + get_text('msg_points', lang) + f": {user_level['points']}\n" + get_text('msg_progress', lang) + f": {user_level['progress']:.1f}%\n\n"

            text += get_text('msg_download_stats_detail', lang) + "\n" + get_text('msg_total_downloads', lang) + f": {download_stats['total_downloads']}\n" + get_text('msg_successful_downloads', lang) + f": {download_stats['successful_downloads']}\n" + get_text('msg_failed_downloads', lang) + f": {download_stats['failed_downloads']}\n" + get_text('msg_success_rate', lang) + f": {download_stats['success_rate']:.1f}%\n" + get_text('msg_total_size', lang) + f": {download_stats['total_size_mb']:.2f} {get_text('msg_mb', lang)}\n" + get_text('msg_avg_file_size', lang) + f": {download_stats.get('avg_file_size_mb', 0):.2f} {get_text('msg_mb', lang)}\n\n"

            text += get_text('msg_activity_stats', lang) + "\n" + get_text('msg_total_actions', lang) + f": {activity_stats['total_actions']}\n" + get_text('msg_most_used_action', lang) + f": {activity_stats.get('most_used_action', get_text('msg_not_specified', lang))}\n\n"

            text += get_text('msg_achievements', lang) + "\n" + get_text('msg_achievements_count', lang) + f": {activity_stats.get('achievements_count', 0)}\n" + get_text('msg_badges', lang) + "\n" + self._format_badges(self._get_user_badges(stats))

        keyboard = [
            [InlineKeyboardButton(get_text('button_export_report', lang), callback_data="user_export_data")],
            [InlineKeyboardButton(get_text('button_back_to_profile', lang), callback_data="user_profile")]
        ]

        if message_object:
            try:
                await message_object.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                if "Message is not modified" in str(e):
                    pass
                else:
                    raise e
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def _cleanup_storage(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Clean up old files from storage."""
        user_id = update.effective_user.id
        if lang is None:
            lang = getattr(update.effective_user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'

        # Get old downloads (older than 30 days)
        old_downloads = await self.bot_manager.db.get_user_downloads(user_id, limit=1000)
        old_downloads = [d for d in old_downloads if (datetime.now() - d.created_at).days > 30]

        if not old_downloads:
            text = get_text('msg_cleanup_storage', lang) + "\n\n" + get_text('msg_no_old_files_to_delete', lang)
        else:
            # Delete old files
            deleted_count = 0
            for download in old_downloads:
                try:
                    # Delete file from storage
                    file_path = f"downloads/{download.filename}"
                    if os.path.exists(file_path):
                        os.remove(file_path)

                    # Mark as deleted in database
                    await self.bot_manager.db.update_download(download.id, {'download_status': 'deleted'})
                    deleted_count += 1
                except Exception as e:
                    self.logger.error(f"Error deleting file {download.filename}: {e}")

            text = get_text('msg_cleanup_storage', lang) + "\n\n" + get_text('msg_files_deleted', lang) + f": {deleted_count}"

        keyboard = [
            [InlineKeyboardButton(get_text('button_storage_analysis', lang), callback_data="user_storage_analysis")],
            [InlineKeyboardButton(get_text('button_back_to_storage_settings', lang), callback_data="storage_settings")]
        ]

        if message_object:
            try:
                await message_object.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                if "Message is not modified" in str(e):
                    pass
                else:
                    raise e
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def _storage_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show storage analysis."""
        user_id = update.effective_user.id
        downloads = await self.bot_manager.db.get_user_downloads(user_id, limit=1000)
        if lang is None:
            lang = update.effective_user.language_code or self.config.LANGUAGE_DEFAULT or 'ar'

        if not downloads:
            text = get_text('msg_storage_analysis', lang) + "\n\n" + get_text('msg_no_files_saved', lang)
        else:
            # Analyze storage usage
            total_size = sum(d.file_size or 0 for d in downloads)
            total_size_mb = total_size / (1024 * 1024)

            # Group by file type
            file_types = {}
            for download in downloads:
                if download.filename:
                    ext = download.filename.split('.')[-1].lower() if '.' in download.filename else 'unknown'
                    file_types[ext] = file_types.get(ext, 0) + 1

            # Get largest files
            largest_files = sorted(downloads, key=lambda x: x.file_size or 0, reverse=True)[:5]

            text = get_text('msg_storage_analysis', lang) + "\n\n" + get_text('msg_general_stats', lang) + "\n" + get_text('msg_total_files', lang) + f": {len(downloads)}\n" + get_text('msg_total_size', lang) + f": {total_size_mb:.2f} {get_text('msg_mb', lang)}\n" + get_text('msg_avg_file_size', lang) + f": {total_size_mb / len(downloads):.2f} {get_text('msg_mb', lang)}\n\n"

            text += get_text('msg_file_types', lang) + "\n"
            for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:5]:
                text += f"\n• {ext.upper()}: {count} {get_text('msg_files', lang)}"

            text += "\n\n" + get_text('msg_largest_files', lang) + "\n"
            for i, download in enumerate(largest_files, 1):
                size_mb = (download.file_size or 0) / (1024 * 1024)
                text += f"\n{i}. {download.filename}: {size_mb:.1f} {get_text('msg_mb', lang)}"

        keyboard = [
            [InlineKeyboardButton(get_text('button_cleanup_storage', lang), callback_data="user_cleanup_storage")],
            [InlineKeyboardButton(get_text('button_back_to_storage_settings', lang), callback_data="storage_settings")]
        ]

        if message_object:
            try:
                await message_object.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                if "Message is not modified" in str(e):
                    pass
                else:
                    raise e
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def _clear_all_files(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Clear all user files."""
        user_id = update.effective_user.id
        downloads = await self.bot_manager.db.get_user_downloads(user_id, limit=1000)
        if lang is None:
            lang = update.effective_user.language_code or self.config.LANGUAGE_DEFAULT or 'ar'

        if not downloads:
            text = get_text('msg_clear_all_files', lang) + "\n\n" + get_text('msg_no_files_to_delete', lang)
        else:
            # Delete all files
            deleted_count = 0
            for download in downloads:
                try:
                    # Delete file from storage
                    file_path = f"downloads/{download.filename}"
                    if os.path.exists(file_path):
                        os.remove(file_path)

                    # Mark as deleted in database
                    await self.bot_manager.db.update_download(download.id, {'download_status': 'deleted'})
                    deleted_count += 1
                except Exception as e:
                    self.logger.error(f"Error deleting file {download.filename}: {e}")

            text = get_text('msg_clear_all_files', lang) + "\n\n" + get_text('msg_files_deleted', lang) + f": {deleted_count}"

        keyboard = [
            [InlineKeyboardButton(get_text('button_storage_analysis', lang), callback_data="user_storage_analysis")],
            [InlineKeyboardButton(get_text('button_back_to_storage_settings', lang), callback_data="storage_settings")]
        ]

        if message_object:
            try:
                await message_object.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                if "Message is not modified" in str(e):
                    pass
                else:
                    raise e
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )


def _is_message_modified(message, new_text, new_reply_markup):
    current_text = getattr(message, 'text', None)
    current_markup = getattr(message, 'reply_markup', None)
    if current_text != new_text:
        return True
    if current_markup is None and new_reply_markup is None:
        return False
    if current_markup is None or new_reply_markup is None:
        return True
    if hasattr(current_markup, 'to_dict') and hasattr(new_reply_markup, 'to_dict'):
        return current_markup.to_dict() != new_reply_markup.to_dict()
    return current_markup != new_reply_markup
