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

        if command == "/profile":
            await self._show_user_profile(update, context)
        elif command == "/settings":
            await self._show_user_settings(update, context)
        elif command == "/stats":
            await self._show_user_stats(update, context)
        elif command == "/help":
            await self._show_user_help(update, context)
        else:
            await update.message.reply_text("❌ أمر غير معروف. استخدم /help للحصول على المساعدة.")

    def get_settings_keyboard(self):
        """Get settings keyboard."""
        return [
            [
                InlineKeyboardButton("🌐 اللغة", callback_data="user_language_settings"),
                InlineKeyboardButton("⏰ المنطقة الزمنية", callback_data="user_timezone_settings")
            ],
            [
                InlineKeyboardButton("🔔 الإشعارات", callback_data="user_notification_settings"),
                InlineKeyboardButton("🔒 الخصوصية", callback_data="user_privacy_settings")
            ],
            [
                InlineKeyboardButton("📊 الإحصائيات", callback_data="user_analytics"),
                InlineKeyboardButton("📥 التحميلات", callback_data="user_downloads")
            ],
            [InlineKeyboardButton("🔙 العودة للملف الشخصي", callback_data="user_profile")]
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

    async def _show_user_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        """Show user profile."""
        user_id = update.effective_user.id
        user = await self.bot_manager.db.get_user(user_id)

        if not user:
            await update.message.reply_text("❌ لم يتم العثور على بيانات المستخدم.")
            return

        # Get user statistics
        stats = await self._get_user_statistics(user_id)
        level_info = self._calculate_user_level(stats['download_stats']['total_downloads'])
        badges = self._get_user_badges(stats)

        # Format registration date
        reg_date = user.registration_date.strftime("%Y-%m-%d") if user.registration_date else "غير محدد"
        last_activity = user.last_activity.strftime("%Y-%m-%d %H:%M") if user.last_activity else "غير محدد"

        text = f"""👤 الملف الشخصي

📋 معلومات المستخدم:
• الاسم: {user.first_name or 'غير محدد'}
• اسم المستخدم: @{user.username or 'غير محدد'}
• معرف المستخدم: {user.id}
• تاريخ التسجيل: {reg_date}
• آخر نشاط: {last_activity}
• اللغة: {user.language_code or 'ar'}

🏆 المستوى والإنجازات:
• المستوى: {level_info['level']} {level_info['title']}
• النقاط: {level_info['points']:,}
• التقدم: {level_info['progress']:.1f}%

📊 الإحصائيات السريعة:
• إجمالي التحميلات: {stats['download_stats']['total_downloads']}
• معدل النجاح: {stats['download_stats']['success_rate']:.1f}%
• الحجم الإجمالي: {stats['download_stats']['total_size_mb']:.1f} MB
• إجمالي الأنشطة: {stats['activity_stats']['total_actions']}

🏅 الشارات:
{self._format_badges(badges)}"""

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

    async def _show_user_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        """Show user settings."""
        user_id = update.effective_user.id
        user = await self.bot_manager.db.get_user(user_id)
        settings = user.settings or {}

        text = f"""⚙️ إعدادات المستخدم

🌐 اللغة والمنطقة الزمنية:
• اللغة الحالية: {user.language_code or 'العربية'}
• المنطقة الزمنية: {user.timezone or 'Asia/Baghdad'}

🔔 الإشعارات:
• إشعارات التحميل: {'🟢 مفعلة' if settings.get('notify_download_start', True) else '🔴 معطلة'}
• إشعارات النظام: {'🟢 مفعلة' if settings.get('notify_bot_updates', True) else '🔴 معطلة'}

🔒 الخصوصية:
• إظهار الإحصائيات: {'🟢 مفعل' if settings.get('show_stats', True) else '🔴 معطل'}
• حفظ سجل النشاط: {'🟢 مفعل' if settings.get('save_activity_log', True) else '🔴 معطل'}

💾 التخزين:
• المساحة المستخدمة: {settings.get('storage_used_mb', 0):.1f} MB
• حد التخزين: {settings.get('storage_limit_mb', 1000):.1f} MB"""

        keyboard = self.get_settings_keyboard()

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

    async def _change_language(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        """Change user language."""
        text = """🌐 اختيار اللغة

اختر اللغة المفضلة لك:"""

        keyboard = [
            [
                InlineKeyboardButton("العربية", callback_data="user_set_language:ar"),
                InlineKeyboardButton("English", callback_data="user_set_language:en")
            ],
            [
                InlineKeyboardButton("Français", callback_data="user_set_language:fr"),
                InlineKeyboardButton("Español", callback_data="user_set_language:es")
            ],
            [
                InlineKeyboardButton("Deutsch", callback_data="user_set_language:de"),
                InlineKeyboardButton("Русский", callback_data="user_set_language:ru")
            ],
            [InlineKeyboardButton("🔙 العودة للإعدادات", callback_data="user_settings")]
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

    async def _change_timezone(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        """Change user timezone."""
        text = """⏰ اختيار المنطقة الزمنية

اختر منطقتك الزمنية:"""

        keyboard = [
            [
                InlineKeyboardButton("بغداد (UTC+3)", callback_data="user_set_timezone:Asia/Baghdad"),
                InlineKeyboardButton("القاهرة (UTC+2)", callback_data="user_set_timezone:Africa/Cairo")
            ],
            [
                InlineKeyboardButton("الرياض (UTC+3)", callback_data="user_set_timezone:Asia/Riyadh"),
                InlineKeyboardButton("دبي (UTC+4)", callback_data="user_set_timezone:Asia/Dubai")
            ],
            [
                InlineKeyboardButton("لندن (UTC+0)", callback_data="user_set_timezone:Europe/London"),
                InlineKeyboardButton("نيويورك (UTC-5)", callback_data="user_set_timezone:America/New_York")
            ],
            [InlineKeyboardButton("🔙 العودة للإعدادات", callback_data="user_settings")]
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

    async def _manage_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        """Manage user notifications."""
        user_id = update.effective_user.id
        user = await self.bot_manager.db.get_user(user_id)
        settings = user.settings or {}

        text = f"""🔔 إدارة الإشعارات

الإعدادات الحالية:

📥 إشعارات التحميل:
• بدء التحميل: {'🟢' if settings.get('notify_download_start', True) else '🔴'}
• انتهاء التحميل: {'🟢' if settings.get('notify_download_complete', True) else '🔴'}
• فشل التحميل: {'🟢' if settings.get('notify_download_failed', True) else '🔴'}

🔔 إشعارات النظام:
• تحديثات البوت: {'🟢' if settings.get('notify_bot_updates', True) else '🔴'}
• رسائل الإدارة: {'🟢' if settings.get('notify_admin_messages', True) else '🔴'}
• تنبيهات الأمان: {'🟢' if settings.get('notify_security_alerts', True) else '🔴'}

⏰ توقيت الإشعارات:
• الإشعارات الليلية: {'🟢 مفعلة' if settings.get('night_notifications', False) else '🔴 معطلة'}
• الساعات الهادئة: {settings.get('quiet_hours', '22:00-08:00')}

🔊 نوع الإشعار:
• إشعارات صوتية: {'🟢' if settings.get('sound_notifications', False) else '🔴'}
• اهتزاز: {'🟢' if settings.get('vibration_notifications', True) else '🔴'}"""

        keyboard = [
            [
                InlineKeyboardButton("📥 إشعارات التحميل", callback_data="user_download_notifications"),
                InlineKeyboardButton("🔔 إشعارات النظام", callback_data="user_system_notifications")
            ],
            [
                InlineKeyboardButton("⏰ توقيت الإشعارات", callback_data="user_notification_timing"),
                InlineKeyboardButton("🔊 نوع الإشعار", callback_data="user_notification_type")
            ],
            [
                InlineKeyboardButton("🔕 إيقاف جميع الإشعارات", callback_data="user_disable_all_notifications"),
                InlineKeyboardButton("🔔 تفعيل جميع الإشعارات", callback_data="user_enable_all_notifications")
            ],
            [InlineKeyboardButton("🔙 العودة للإعدادات", callback_data="user_settings")]
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
    async def _toggle_download_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        """Toggle download notifications."""
        user_id = update.effective_user.id
        user = await self.bot_manager.db.get_user(user_id)
        settings = user.settings or {}

        # Toggle download notifications
        current_setting = settings.get('notify_download_start', True)
        settings['notify_download_start'] = not current_setting
        settings['notify_download_complete'] = not current_setting
        settings['notify_download_failed'] = not current_setting

        # Update user settings
        await self.bot_manager.db.update_user(user_id, {'settings': settings})

        # Show updated notifications page
        await self._manage_notifications(update, context, message_object)

    async def _toggle_system_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        """Toggle system notifications."""
        user_id = update.effective_user.id
        user = await self.bot_manager.db.get_user(user_id)
        settings = user.settings or {}

        # Toggle system notifications
        current_setting = settings.get('notify_bot_updates', True)
        settings['notify_bot_updates'] = not current_setting
        settings['notify_admin_messages'] = not current_setting
        settings['notify_security_alerts'] = not current_setting

        # Update user settings
        await self.bot_manager.db.update_user(user_id, {'settings': settings})

        # Show updated notifications page
        await self._manage_notifications(update, context, message_object)

    async def _toggle_notification_timing(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        """Toggle notification timing."""
        user_id = update.effective_user.id
        user = await self.bot_manager.db.get_user(user_id)
        settings = user.settings or {}

        # Toggle night notifications
        current_setting = settings.get('night_notifications', False)
        settings['night_notifications'] = not current_setting

        # Update user settings
        await self.bot_manager.db.update_user(user_id, {'settings': settings})

        # Show updated notifications page
        await self._manage_notifications(update, context, message_object)

    async def _toggle_notification_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        """Toggle notification type."""
        user_id = update.effective_user.id
        user = await self.bot_manager.db.get_user(user_id)
        settings = user.settings or {}

        # Toggle sound notifications
        current_setting = settings.get('sound_notifications', False)
        settings['sound_notifications'] = not current_setting

        # Update user settings
        await self.bot_manager.db.update_user(user_id, {'settings': settings})

        # Show updated notifications page
        await self._manage_notifications(update, context, message_object)

    async def _disable_all_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        """Disable all notifications."""
        user_id = update.effective_user.id
        user = await self.bot_manager.db.get_user(user_id)
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
        await self._manage_notifications(update, context, message_object)

    async def _enable_all_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        """Enable all notifications."""
        user_id = update.effective_user.id
        user = await self.bot_manager.db.get_user(user_id)
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
        await self._manage_notifications(update, context, message_object)

    async def handle_callback(self, update, context):
        query = update.callback_query
        data = query.data if query else None
        user_id = query.from_user.id if query else None
        if not query:
            return

        # Route callback to appropriate handler
        if data == "user_profile":
            await self._show_user_profile(update, context, message_object=query.message)
        elif data == "user_edit_settings":
            await self._show_user_settings(update, context, message_object=query.message)
        elif data == "user_detailed_report":
            await self._show_user_profile(update, context, message_object=query.message)
        elif data == "user_achievements":
            await self._show_user_achievements(update, context, message_object=query.message)
        elif data == "user_analytics":
            await self._show_user_analytics(update, context, message_object=query.message)
        elif data == "user_export_data":
            await self._export_user_data(update, context)
        elif data == "user_privacy_settings":
            await self._privacy_settings(update, context, message_object=query.message)
        elif data == "user_confirm_delete":
            await self._confirm_delete_callback(query, context)
        elif data == "user_cancel_delete":
            await query.edit_message_text("✅ تم إلغاء حذف الحساب.")
        elif data == "user_language_settings":
            await self._change_language(update, context, message_object=query.message)
        elif data == "user_notification_settings":
            await self._manage_notifications(update, context, message_object=query.message)
        elif data == "user_downloads":
            await self._show_user_downloads(update, context, message_object=query.message)
        elif data == "main_menu":
            if query and query.message:
                await self._show_user_profile(update, context, message_object=query.message)
            else:
                await self._show_user_profile(update, context)
        elif data == "user_settings":
            if query and query.message:
                await self._show_user_settings(update, context, message_object=query.message)
            else:
                await self._show_user_settings(update, context)
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
        elif data and data.startswith("user_set_language:"):
            await self._set_language_callback(query, context)

    async def _set_language_callback(self, query, context):
        """Set user language from callback."""
        await query.answer()

        language = query.data.split(":")[1]
        user_id = query.from_user.id

        # Update user language
        success = await self.bot_manager.db.update_user(
            user_id,
            {'language_code': language}
        )

        if success:
            language_names = {
                'ar': 'العربية',
                'en': 'English',
                'fr': 'Français',
                'es': 'Español',
                'de': 'Deutsch',
                'ru': 'Русский'
            }

            await query.edit_message_text(
                f"✅ تم تغيير اللغة إلى {language_names.get(language, language)} بنجاح!"
            )
        else:
            await query.edit_message_text("❌ فشل في تغيير اللغة.")

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
            badges.append("🎯 محمل نشط")

        if download_stats['success_rate'] >= 95:
            badges.append("⭐ محمل محترف")

        if download_stats['total_size_mb'] >= 1000:
            badges.append("💾 جامع البيانات")

        if stats['activity_stats']['total_actions'] >= 100:
            badges.append("🔥 مستخدم نشط")

        return badges

    def _format_badges(self, badges: List[str]) -> str:
        """Format badges for display."""
        if not badges:
            return "لا توجد شارات بعد"

        return "\n".join([f"• {badge}" for badge in badges])

    # Placeholder methods for future implementation
    async def _show_user_achievements(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        """Show user achievements."""
        await update.message.reply_text("🏆 صفحة الإنجازات - قيد التطوير")

    async def _show_user_analytics(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        """Show user analytics."""
        await update.message.reply_text("📈 صفحة الإحصائيات - قيد التطوير")

    async def _show_user_downloads(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        """Show user downloads."""
        await update.message.reply_text("📥 صفحة التحميلات - قيد التطوير")

    async def _show_user_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user help."""
        await update.message.reply_text("❓ صفحة المساعدة - قيد التطوير")

    async def _show_user_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user stats."""
        await update.message.reply_text("📊 صفحة الإحصائيات - قيد التطوير")

    async def _privacy_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        """Show privacy settings."""
        await update.message.reply_text("🔒 صفحة الخصوصية - قيد التطوير")

    async def _export_user_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Export user data."""
        await update.message.reply_text("📥 تصدير البيانات - قيد التطوير")

    async def _confirm_delete_callback(self, query, context):
        """Confirm account deletion."""
        await query.edit_message_text("🗑️ حذف الحساب - قيد التطوير")
