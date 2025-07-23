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
        user_id = user.id if user else None

        # Check if user exists in database
        db_user = await self.bot_manager.db.get_user(user_id) if user_id else None

        if not db_user and user_id:
            # Create new user
            await self.bot_manager.db.create_user({
                "id": user_id,
                "username": getattr(user, 'username', None),
                "first_name": getattr(user, 'first_name', None),
                "last_name": getattr(user, 'last_name', None),
                "language_code": getattr(user, 'language_code', None)
            })
            self.logger.info(f"New user registered: {user_id}")

        # تحقق من الاشتراك الإجباري دائماً من قاعدة البيانات
        forced_channels = await self.bot_manager.db.get_forced_subscription_channels()
        if forced_channels and user_id:
            unsubscribed_channels = await self.bot_manager.check_user_subscription(user_id)
            if unsubscribed_channels:
                await self._send_subscription_required_message(update, unsubscribed_channels)
                return

        # Send welcome message
        lang = (getattr(db_user, 'language_code', None) if db_user else None) or (getattr(user, 'language_code', None) if user else None) or self.config.LANGUAGE_DEFAULT or 'ar'
        await self._send_welcome_message(update, user, context=context, lang=lang)

    async def _send_subscription_required_message(self, update: Update, unsubscribed_channels: list, lang=None):
        """Send subscription required message."""
        user = update.effective_user
        user_id = user.id if user else None
        if lang is None:
            db_user = await self.bot_manager.db.get_user(user_id) if user_id else None
            lang = (getattr(db_user, 'language_code', None) if db_user else None) or (getattr(user, 'language_code', None) if user else None) or self.config.LANGUAGE_DEFAULT or 'ar'
        # تحقق من حالة كل قناة (✅/❌)
        all_channels = await self.bot_manager.db.get_forced_subscription_channels()
        status_map = {}
        for channel in all_channels:
            channel_id = channel.get('id', channel.get('username', ''))
            status = not any(c['id'] == channel_id for c in unsubscribed_channels)
            status_map[channel_id] = status
        # نص احترافي متعدد اللغات
        text = get_text('msg_subscription_required', lang) + "\n\n"
        for channel in all_channels:
            channel_id = channel.get('id', channel.get('username', ''))
            name = channel.get('name', channel_id)
            status_emoji = '✅' if status_map[channel_id] else '❌'
            text += f"{status_emoji} <b>{name}</b>\n"
        text += "\n" + get_text('msg_subscription_instructions', lang)
        keyboard = []
        for channel in all_channels:
            channel_id = channel.get('id', channel.get('username', ''))
            name = channel.get('name', channel_id)
            url = channel.get('url', f"https://t.me/{channel_id}")
            keyboard.append([
                InlineKeyboardButton(f"{get_text('button_subscribe', lang)} {name}", url=url)
            ])
        keyboard.append([InlineKeyboardButton(get_text('button_check_subscription', lang), callback_data="check_subscription")])
        keyboard.append([InlineKeyboardButton(get_text('button_support', lang), callback_data="support")])
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        elif hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )

    async def _send_welcome_message(self, update, user, message_object=None, lang=None, context=None):
        if lang is None:
            db_user = await self.bot_manager.db.get_user(user.id)
            lang = getattr(db_user, 'language_code', None) or getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        # رسالة ترحيب احترافية مع الأزرار
        welcome_intro = (
            """
🎉 مرحبًا بك في مركز التحميل الذكي!
حلّك الشامل لتحميل الفيديوهات والمقاطع الصوتية من أشهر المنصات – بسهولة وسرعة.

🔹 المنصات المدعومة:
ـ انستغرام | فيسبوك | تيك توك | بنترست  | سناب شات
✔️ تحميل مباشر للفيديو أو الصوت من أي رابط

🔹 يوتيوب – بمستوى متقدم:
✔️ تحميل فيديو أو صوت
✔️ دعم كامل لقوائم التشغيل وميزة البحث
✔️ تصفح القائمة، اختيار ملفات معينة أو تحميل الكل
✔️ تحديد الصيغة: فيديو أو صوت حسب رغبتك

💡 كل ما عليك: أرسل الرابط فقط
وأنا أتكفّل بالباقي — بدقة وسرعة.

🚀 جاهز؟ ابدأ بإرسال أول رابط الآن.
"""
        )
        # رسالة ترحيب احترافية مع الأزرار
        keyboard = [
            [
                InlineKeyboardButton(get_text('button_download_menu', lang), callback_data="download_menu"),
                InlineKeyboardButton(get_text('button_user_stats', lang), callback_data="user_stats")
            ],
            [
                InlineKeyboardButton(get_text('button_settings', lang), callback_data="settings_menu"),
                InlineKeyboardButton(get_text('button_help', lang), callback_data="help_menu")
            ]
        ]
        if await self.bot_manager.is_user_admin(user.id):
            keyboard.append([
                InlineKeyboardButton(get_text('button_admin_panel', lang), callback_data="admin_menu")
            ])
        from config import Config
        if user.id != Config.OWNER_ID:
            keyboard.append([
                InlineKeyboardButton(get_text('button_check_subscription', lang), callback_data="check_subscription")
            ])
        if message_object:
            try:
                await message_object.edit_text(welcome_intro, reply_markup=InlineKeyboardMarkup(keyboard))
            except Exception:
                pass
        elif hasattr(update, 'message') and update.message:
            await update.message.reply_text(welcome_intro, reply_markup=InlineKeyboardMarkup(keyboard))
        elif user is not None and context is not None and hasattr(user, 'id'):
            await context.bot.send_message(chat_id=user.id, text=welcome_intro, reply_markup=InlineKeyboardMarkup(keyboard))
        # لا ترسل أي رسالة ترحيب أخرى هنا
        return

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries."""
        query = update.callback_query
        data = query.data if query else None

        if not query or not hasattr(query, 'data'):
            return

        # طبقة تحقق إضافية: منع غير الأدمن من الوصول للوحة الإدارة
        if data == "admin_menu" and not await self.bot_manager.is_user_admin(query.from_user.id):
            await query.answer("❌ غير مصرح لك بالوصول لهذه القائمة", show_alert=True)
            return

        # Route to appropriate handler
        if data == "main_menu":
            await self._send_welcome_message(update, query.from_user, message_object=query.message, context=context)
        elif data == "help_menu":
            await self._show_help_menu(update, context, message_object=query.message)
        elif data == "settings_menu":
            await self._show_settings_menu(update, context, message_object=query.message)
        elif data == "download_menu":
            await self._show_download_menu(update, context, message_object=query.message)
        elif data == "user_stats":
            await self._show_user_stats(update, context, message_object=query.message)
        elif data == "download_history":
            await self._show_download_history(update, context, message_object=query.message)
        elif data == "change_language":
            await self._show_language_settings(update, context, message_object=query.message)
        elif data == "change_timezone":
            await self._show_timezone_settings(update, context, message_object=query.message)
        elif data == "notification_settings":
            await self._show_notification_settings(update, context, message_object=query.message)
        elif data == "storage_settings":
            await self._show_storage_settings(update, context, message_object=query.message)
        elif data == "full_commands":
            await self._show_full_commands(update, context, message_object=query.message)
        elif data == "faq":
            await self._show_faq(update, context, message_object=query.message)
        elif data == "support":
            await self._show_support(update, context, message_object=query.message)
        elif data == "terms":
            await self._show_terms(update, context, message_object=query.message)
        elif data == "admin_menu":
            await self._show_admin_menu(update, context, message_object=query.message)
        elif data == "admin_stats":
            await self._show_admin_stats(update, context, message_object=query.message)
        elif data == "admin_users":
            await self._show_admin_users(update, context, message_object=query.message)
        elif data == "admin_broadcast":
            await self._show_admin_broadcast(update, context, message_object=query.message)
        elif data == "admin_settings":
            await self._show_admin_settings(update, context, message_object=query.message)
        elif data == "admin_logs":
            await self._show_admin_logs(update, context, message_object=query.message)
        elif data == "admin_backup":
            await self._show_admin_backup(update, context, message_object=query.message)
        elif data == "privacy_settings":
            await self._show_privacy_settings(update, context, message_object=query.message)
        # أزرار العودة الموحدة لأي قيمة تحتوي على back أو عودة أو main_menu
        elif data and ("back" in data or "عودة" in data or data == "main_menu"):
            await self._send_welcome_message(update, query.from_user, message_object=query.message, context=context)
        elif data == "detailed_report":
            await self._show_detailed_report(update, context, message_object=query.message)
        elif data == "check_subscription":
            await self._check_subscription_callback(update, context)
        else:
            if query and hasattr(query, 'answer'):
                await query.answer("❌ هذا الزر غير معروف أو لم يتم ربطه بعد.", show_alert=True)

    async def _check_subscription_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle subscription check callback."""
        query = update.callback_query
        user_id = query.from_user.id

        # تحقق من الاشتراك الإجباري دائماً من قاعدة البيانات
        forced_channels = await self.bot_manager.db.get_forced_subscription_channels()
        if forced_channels:
            unsubscribed_channels = await self.bot_manager.check_user_subscription(user_id)
            if unsubscribed_channels:
                await query.answer("❌ يجب الاشتراك في جميع القنوات المطلوبة", show_alert=True)
                return

        await query.answer("✅ تم التحقق من الاشتراك بنجاح!", show_alert=True)
        await self._send_welcome_message(update, query.from_user, message_object=query.message, context=context)

    async def _show_download_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show download menu."""
        if lang is None:
            user_id = update.effective_user.id
            db_user = await self.bot_manager.db.get_user(user_id)
            lang = getattr(db_user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = get_text('msg_download_menu', lang)

        keyboard = [
            [InlineKeyboardButton(get_text('button_download_history', lang), callback_data="download_history")],
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

    async def _show_user_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
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

        if lang is None:
            user_id = update.effective_user.id
            db_user = await self.bot_manager.db.get_user(user_id)
            lang = getattr(db_user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = get_text('msg_user_stats', lang)
        text += f"""

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
            [InlineKeyboardButton(get_text('button_detailed_report', lang), callback_data="detailed_report")],
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
                InlineKeyboardButton(get_text('button_notifications', lang), callback_data="notification_settings")
            ],
            [InlineKeyboardButton(get_text('button_back', lang), callback_data="main_menu")]
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

    async def _show_help_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show help menu."""
        user = update.effective_user
        from config import Config
        is_owner = user and user.id == Config.OWNER_ID
        if lang is None:
            user_id = user.id if user else None
            db_user = await self.bot_manager.db.get_user(user_id) if user_id else None
            lang = (getattr(db_user, 'language_code', None) if db_user else None) or (getattr(user, 'language_code', None) if user else None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = get_text('msg_help_menu', lang)
        text += """

📖 كيفية استخدام البوت:
1. أرسل رابط الملف للتحميل
2. أو أرسل ملف مباشرة للرفع
3. استخدم الأوامر للوصول للميزات

🔧 الأوامر المتاحة:
/start - بدء البوت
/help - عرض المساعدة
/stats - عرض الإحصائيات
/settings - الإعدادات
/profile - الملف الشخصي

💬 للدعم الفني:
تواصل مع المطور أو استخدم قسم الأسئلة الشائعة"""

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
        if is_owner:
            text += "\n\n👑 أوامر الإدارة (للمالك فقط):\n"
            text += "/admin - لوحة الإدارة\n"
            text += "/broadcast - رسالة جماعية\n"
            text += "/ban - حظر مستخدم\n"
            text += "/unban - إلغاء حظر\n"
            text += "/logs - السجلات\n"
            text += "/maintenance - وضع الصيانة\n"
            text += "/backup - نسخة احتياطية\n"
            text += "/restart - إعادة تشغيل\n"
            text += "/users - إدارة المستخدمين\n"
            keyboard = [
                [InlineKeyboardButton(get_text('button_faq', lang), callback_data="faq")],
                [InlineKeyboardButton(get_text('button_back', lang), callback_data="help_menu")]
            ]
            await message_object.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

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
            user_id = update.effective_user.id
            db_user = await self.bot_manager.db.get_user(user_id)
            lang = getattr(db_user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = get_text('msg_admin_menu', lang)
        text += """

👑 لوحة الإدارة

🎛️ إدارة البوت والمستخدمين
📊 عرض الإحصائيات التفصيلية
📢 إرسال رسائل جماعية
🔧 إعدادات النظام"""

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

    async def _show_detailed_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show detailed user report."""
        user_id = update.effective_user.id
        stats = await self.bot_manager.get_user_stats(user_id)

        if not stats:
            text = "❌ لا توجد إحصائيات متاحة لعرض التقرير المفصل"
        else:
            user_info = stats['user_info']
            download_stats = stats['download_stats']
            activity_stats = stats['activity_stats']

            if lang is None:
                user_id = update.effective_user.id
                db_user = await self.bot_manager.db.get_user(user_id)
                lang = getattr(db_user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
            text = get_text('msg_detailed_report', lang)
            text += f"""

👤 معلومات المستخدم:
• الاسم: {user_info['first_name']}
• المعرف: {user_id}
• تاريخ التسجيل: {user_info['registration_date'].strftime('%Y-%m-%d %H:%M')}
• آخر نشاط: {user_info['last_activity'].strftime('%Y-%m-%d %H:%M')}
• اللغة: {user_info['language']}
• المنطقة الزمنية: {user_info.get('timezone', 'غير محدد')}

📥 إحصائيات التحميل التفصيلية:
• إجمالي التحميلات: {download_stats['total_downloads']}
• التحميلات الناجحة: {download_stats['successful_downloads']}
• التحميلات الفاشلة: {download_stats['failed_downloads']}
• معدل النجاح: {download_stats['success_rate']:.1f}%
• الحجم الإجمالي: {download_stats['total_size_mb']:.2f} MB
• المساحة المستخدمة: {download_stats['storage_used_mb']:.2f} MB
• متوسط حجم الملف: {download_stats.get('avg_file_size_mb', 0):.2f} MB

📈 إحصائيات النشاط:
• إجمالي الأنشطة: {activity_stats['total_actions']}
• متوسط الأنشطة اليومية: {activity_stats.get('avg_daily_actions', 0):.1f}
• أكثر الأنشطة استخداماً: {activity_stats.get('most_used_action', 'غير محدد')}

🏆 الإنجازات:
• المستوى الحالي: {activity_stats.get('user_level', 'مبتدئ')}
• النقاط المكتسبة: {activity_stats.get('points_earned', 0)}
• الإنجازات المحققة: {activity_stats.get('achievements_count', 0)}"""

        keyboard = [
            [InlineKeyboardButton(get_text('button_user_export_data', lang), callback_data="user_export_data")],
            [InlineKeyboardButton(get_text('button_back', lang), callback_data="user_stats")]
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

    async def _show_download_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show download history."""
        user_id = update.effective_user.id
        downloads = await self.bot_manager.db.get_user_downloads(user_id, limit=10)

        if not downloads:
            text = "📋 سجل التحميلات\n\n❌ لا توجد تحميلات سابقة"
        else:
            text = "📋 سجل التحميلات الأخيرة\n\n"
            for i, download in enumerate(downloads[:5], 1):
                status_emoji = "✅" if download.download_status == "completed" else "❌"
                text += f"{i}. {status_emoji} {download.filename or 'ملف غير معروف'}\n"
                text += f"   📅 {download.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                if download.file_size:
                    text += f"   📊 {download.file_size / (1024*1024):.1f} MB\n"
                text += "\n"

        keyboard = [
            [InlineKeyboardButton(get_text('button_download_new', lang), callback_data="download_menu")],
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
                    pass
                else:
                    raise e
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def _show_language_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show language settings."""
        if lang is None:
            user_id = update.effective_user.id
            db_user = await self.bot_manager.db.get_user(user_id)
            lang = getattr(db_user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = get_text('msg_language_settings', lang)
        text += """

اختر اللغة المفضلة لك:"""

        keyboard = [
            [
                InlineKeyboardButton(get_text('button_language_ar', lang), callback_data="user_set_language:ar"),
                InlineKeyboardButton(get_text('button_language_en', lang), callback_data="user_set_language:en")
            ],
            [
                InlineKeyboardButton(get_text('button_language_fr', lang), callback_data="user_set_language:fr"),
                InlineKeyboardButton(get_text('button_language_es', lang), callback_data="user_set_language:es")
            ],
            [
                InlineKeyboardButton(get_text('button_language_de', lang), callback_data="user_set_language:de"),
                InlineKeyboardButton(get_text('button_language_ru', lang), callback_data="user_set_language:ru")
            ],
            [InlineKeyboardButton(get_text('button_back', lang), callback_data="settings_menu")]
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

    async def _show_timezone_settings(self, update, context, message_object=None, lang=None):
        if lang is None:
            db_user = await self.bot_manager.db.get_user(update.effective_user.id)
            lang = getattr(db_user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = get_text('msg_timezone_settings', lang) + "\nاختر المنطقة الزمنية المناسبة لك:"
        # أزرار المناطق الزمنية المطلوبة فقط
        timezones = [
            ("Asia/Baghdad", get_text('button_timezone_baghdad', lang)),
            ("America/New_York", get_text('button_timezone_newyork', lang)),
            ("Europe/Moscow", get_text('button_timezone_moscow', lang)),
            ("Asia/Shanghai", get_text('button_timezone_beijing', lang)),
        ]
        keyboard = []
        for i in range(0, len(timezones), 2):
            row = []
            for tz, label in timezones[i:i+2]:
                row.append(InlineKeyboardButton(label, callback_data=f"user_set_timezone:{tz}"))
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton(get_text('button_back', lang), callback_data="user_settings")])
        if message_object:
            await message_object.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_notification_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show notification settings."""
        if lang is None:
            user_id = update.effective_user.id
            db_user = await self.bot_manager.db.get_user(user_id)
            lang = getattr(db_user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = get_text('msg_notification_settings', lang)
        text += """

اختر الإشعارات التي تريد استقبالها:"""

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
            [InlineKeyboardButton(get_text('button_back', lang), callback_data="settings_menu")]
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

    async def _show_storage_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show storage settings."""
        user_id = update.effective_user.id
        user = await self.bot_manager.db.get_user(user_id)
        settings = user.settings or {}

        storage_used = settings.get('storage_used_mb', 0)
        storage_limit = settings.get('storage_limit_mb', 1000)
        storage_percentage = (storage_used / storage_limit) * 100 if storage_limit > 0 else 0

        if lang is None:
            user_id = update.effective_user.id
            db_user = await self.bot_manager.db.get_user(user_id)
            lang = getattr(db_user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = get_text('msg_storage_settings', lang)
        text += f"""

📊 استخدام التخزين:
• المساحة المستخدمة: {storage_used:.1f} MB
• الحد الأقصى: {storage_limit:.1f} MB
• النسبة المئوية: {storage_percentage:.1f}%

⚙️ الخيارات المتاحة:"""

        keyboard = [
            [
                InlineKeyboardButton(get_text('button_cleanup_storage', lang), callback_data="user_cleanup_storage"),
                InlineKeyboardButton(get_text('button_storage_analysis', lang), callback_data="user_storage_analysis")
            ],
            [
                InlineKeyboardButton(get_text('button_clear_all_files', lang), callback_data="user_clear_all_files"),
                InlineKeyboardButton(get_text('button_export_data', lang), callback_data="user_export_data")
            ],
            [InlineKeyboardButton(get_text('button_back', lang), callback_data="settings_menu")]
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

    async def _show_full_commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show full commands list."""
        if lang is None:
            user_id = update.effective_user.id
            db_user = await self.bot_manager.db.get_user(user_id)
            lang = getattr(db_user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        from config import Config
        is_owner = update.effective_user and update.effective_user.id == Config.OWNER_ID
        text = get_text('msg_full_commands', lang)
        text += """

📋 جميع الأوامر المتاحة

🎯 الأوامر الأساسية:
/start - بدء البوت
/help - المساعدة
/profile - الملف الشخصي
/settings - الإعدادات

📥 أوامر التحميل:
• أرسل أي رابط للتحميل
• أرسل ملف لرفعه

📊 أوامر الإحصائيات:
/stats - إحصائيات البوت
/user_stats - إحصائياتك الشخصية

⚙️ أوامر الإعدادات:
/language - تغيير اللغة
/timezone - المنطقة الزمنية
/notifications - الإشعارات
/privacy - الخصوصية
/export - تصدير البيانات
/delete - حذف الحساب
"""
        if is_owner:
            text += """
👑 أوامر الإدارة (للمشرفين):
/admin - لوحة الإدارة
/broadcast - رسالة جماعية
/ban - حظر مستخدم
/unban - إلغاء حظر
/logs - السجلات
/maintenance - وضع الصيانة
/backup - نسخة احتياطية
/restart - إعادة تشغيل
/users - إدارة المستخدمين"""
        keyboard = [
            [InlineKeyboardButton(get_text('button_faq', lang), callback_data="faq")],
            [InlineKeyboardButton(get_text('button_back', lang), callback_data="help_menu")]
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

    async def _show_faq(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show FAQ."""
        if lang is None:
            user_id = update.effective_user.id
            db_user = await self.bot_manager.db.get_user(user_id)
            lang = getattr(db_user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = get_text('msg_faq', lang)
        text += """

❓ الأسئلة الشائعة

🤔 كيف أحمّل ملف؟
• أرسل رابط الملف مباشرة للبوت
• البوت سيعرض خيارات التحميل المتاحة

🤔 ما هي الصيغ المدعومة؟
• فيديو: MP4, AVI, MKV
• صوت: MP3, WAV, FLAC
• صور: JPG, PNG, GIF
• مستندات: PDF, DOC, ZIP

🤔 ما هو الحد الأقصى للحجم؟
• الحد الأقصى: 50 MB لكل ملف

🤔 كيف أغير اللغة؟
• اذهب للإعدادات → تغيير اللغة
• اختر اللغة المفضلة

🤔 كيف أتصدير بياناتي؟
• اذهب للملف الشخصي → تصدير البيانات
• سيتم إرسال ملف JSON بجميع بياناتك

🤔 كيف أحذف حسابي؟
• اذهب للإعدادات → حذف الحساب
• تأكد من الحذف مرتين

🤔 كيف أتواصل مع الدعم؟
• استخدم زر "الدعم" في قائمة المساعدة
• أو أرسل رسالة مباشرة للمشرف"""

        keyboard = [
            [InlineKeyboardButton(get_text('button_support', lang), callback_data="support")],
            [InlineKeyboardButton(get_text('button_back', lang), callback_data="help_menu")]
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

    async def _show_support(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show support information."""
        if lang is None:
            user_id = update.effective_user.id
            db_user = await self.bot_manager.db.get_user(user_id)
            lang = getattr(db_user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = get_text('msg_support', lang)
        text += """

�� الدعم الفني

🆘 إذا واجهت أي مشكلة:

👨‍💻 المطور:
@GF1FF

⚠️ قبل التواصل:
• تأكد من تحديث البوت
• افحص اتصال الإنترنت
• جرب إعادة تشغيل البوت

🔧 المشاكل الشائعة:
• البوت لا يستجيب: أعد تشغيله
• التحميل بطيء: تحقق من سرعة الإنترنت
• خطأ في التحميل: جرب رابط آخر"""

        keyboard = [
            [InlineKeyboardButton(get_text('button_faq', lang), callback_data="faq")],
            [InlineKeyboardButton(get_text('button_full_commands', lang), callback_data="full_commands")],
            [InlineKeyboardButton(get_text('button_back', lang), callback_data="help_menu")]
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

    async def _show_terms(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show terms of service."""
        if lang is None:
            user_id = update.effective_user.id
            db_user = await self.bot_manager.db.get_user(user_id)
            lang = getattr(db_user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = get_text('msg_terms', lang)
        text += """

📜 شروط الخدمة

📋 شروط استخدام Advanced Telegram Bot:

1️⃣ الاستخدام المقبول:
• تحميل الملفات للاستخدام الشخصي فقط
• احترام حقوق الملكية الفكرية
• عدم إساءة استخدام البوت

2️⃣ القيود:
• لا تستخدم البوت لأغراض تجارية
• لا تحمّل محتوى غير قانوني
• لا تشارك محتوى محمي بحقوق النشر

3️⃣ الخصوصية:
• نحن نحترم خصوصيتك
• لا نشارك بياناتك مع أطراف ثالثة
• يمكنك حذف بياناتك في أي وقت

4️⃣ المسؤولية:
• المستخدم مسؤول عن المحتوى المحمّل
• البوت غير مسؤول عن أي انتهاك لحقوق النشر
• استخدام البوت على مسؤولية المستخدم

5️⃣ التحديثات:
• قد تتغير الشروط من وقت لآخر
• سيتم إعلامك بأي تغييرات مهمة

6️⃣ الإيقاف:
• يحق لنا إيقاف الحساب لانتهاك الشروط
• يمكنك حذف حسابك في أي وقت

✅ باستخدام البوت، أنت توافق على هذه الشروط."""

        keyboard = [
            [InlineKeyboardButton(get_text('button_privacy_settings', lang), callback_data="privacy_settings")],
            [InlineKeyboardButton(get_text('button_back', lang), callback_data="help_menu")]
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

    # Admin functions
    async def _show_admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show admin statistics."""
        if not await self.bot_manager.is_user_admin(update.effective_user.id):
            await update.callback_query.answer("❌ غير مصرح لك بالوصول لهذه الميزة", show_alert=True)
            return

        # Redirect to admin handler
        await self.bot_manager.admin_handler._show_bot_statistics(update, context, message_object=message_object)

    async def _show_admin_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show admin users management."""
        if not await self.bot_manager.is_user_admin(update.effective_user.id):
            await update.callback_query.answer("❌ غير مصرح لك بالوصول لهذه الميزة", show_alert=True)
            return

        # Redirect to admin handler
        await self.bot_manager.admin_handler._show_users_management_callback(update, context)

    async def _show_admin_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show admin broadcast menu."""
        if not await self.bot_manager.is_user_admin(update.effective_user.id):
            await update.callback_query.answer("❌ غير مصرح لك بالوصول لهذه الميزة", show_alert=True)
            return

        # Redirect to admin handler
        await self.bot_manager.admin_handler._show_broadcast_menu(update, context, message_object=message_object)

    async def _show_admin_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show admin system settings."""
        if not await self.bot_manager.is_user_admin(update.effective_user.id):
            await update.callback_query.answer("❌ غير مصرح لك بالوصول لهذه الميزة", show_alert=True)
            return

        # Redirect to admin handler
        await self.bot_manager.admin_handler._show_system_settings(update, context, message_object=message_object)

    async def _show_admin_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show admin system logs."""
        if not await self.bot_manager.is_user_admin(update.effective_user.id):
            await update.callback_query.answer("❌ غير مصرح لك بالوصول لهذه الميزة", show_alert=True)
            return

        # Redirect to admin handler
        await self.bot_manager.admin_handler._show_system_logs(update, context, message_object=message_object)

    async def _show_admin_backup(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show admin backup options."""
        if not await self.bot_manager.is_user_admin(update.effective_user.id):
            await update.callback_query.answer("❌ غير مصرح لك بالوصول لهذه الميزة", show_alert=True)
            return

        # Redirect to admin handler
        await self.bot_manager.admin_handler._create_backup(update, context, message_object=message_object)

    async def _show_privacy_settings(self, update, context, message_object=None, lang=None):
        if lang is None:
            user_id = update.effective_user.id
            db_user = await self.bot_manager.db.get_user(user_id)
            lang = getattr(db_user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = get_text('msg_privacy_settings', lang) + "\n\n" + get_text('msg_privacy_details', lang)
        keyboard = [[InlineKeyboardButton(get_text('button_back', lang), callback_data="terms")]]
        if message_object:
            await message_object.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
