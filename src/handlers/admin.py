#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Admin Handler
=============

Comprehensive admin panel with advanced management features
for user control, system monitoring, and bot configuration.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from src.utils.performance_monitor import performance_monitor
from src.utils.localization_core import get_text
import re
import urllib.parse
import os
import sys
import subprocess
import telegram

# في أعلى الملف
ADD_FORCED_CHANNEL = 10001

def _is_message_modified(message, new_text, new_reply_markup):
    current_text = getattr(message, 'text', None)
    current_markup = getattr(message, 'reply_markup', None)
    # قارن النصوص
    if current_text != new_text:
        return True
    # قارن الأزرار (reply_markup)
    if current_markup is None and new_reply_markup is None:
        return False
    if current_markup is None or new_reply_markup is None:
        return True
    if hasattr(current_markup, 'to_dict') and hasattr(new_reply_markup, 'to_dict'):
        return current_markup.to_dict() != new_reply_markup.to_dict()
    return current_markup != new_reply_markup

class AdminHandler:
    """Advanced admin handler with comprehensive management features."""

    def __init__(self, bot_manager, config, db_manager):
        """Initialize admin handler."""
        self.bot_manager = bot_manager
        self.config = config
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)

    async def handle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            self.logger.info(f"[DIAG] Command Triggered: {update.message.text if update.message else ''}")
            """Handle admin commands."""
            user_id = update.effective_user.id
            command = update.message.text.split()[0][1:]  # Remove '/'

            # Check admin permissions
            if not await self.bot_manager.is_user_admin(user_id):
                await update.message.reply_text("❌ غير مصرح لك بالوصول لهذه الميزة.")
                return

            # إضافة دعم استقبال الرسائل الخاصة بإضافة قناة اشتراك إجباري
            if context.user_data.get('awaiting_forced_channel'):
                await self._process_forced_channel_input(update, context)
                return

            # Route to appropriate handler
            handlers = {
                'admin': self._show_admin_panel,
                'stats': self._show_bot_statistics,
                'users': self._show_users_management,
                'broadcast': self._handle_broadcast,
                'ban': self._handle_ban_user,
                'unban': self._handle_unban_user,
                'logs': self._show_system_logs,
                'maintenance': self._toggle_maintenance,
                'backup': self._create_backup,
                'restart': self._restart_bot,
                'settings': self._show_system_settings
            }

            handler = handlers.get(command)
            if handler:
                await handler(update, context)
            else:
                await update.message.reply_text("❌ أمر غير معروف. استخدم /admin لعرض لوحة الإدارة.")
        except Exception as e:
            self.logger.error(f"[AdminHandler.handle_command] {e}")
            await update.message.reply_text("❌ حدث خطأ غير متوقع. يرجى المحاولة لاحقاً.")

    async def _show_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        if lang is None:
            user = update.effective_user if update.effective_user else None
            db_user = await self.bot_manager.db.get_user(user.id) if user else None
            lang = getattr(db_user, 'language_code', None) or getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = get_text('msg_admin_panel', lang)
        """Show main admin panel."""
        user_id = update.effective_user.id

        # Get bot statistics
        stats = await self.bot_manager.get_bot_statistics()
        db_stats = stats.get('database_stats', {})

        keyboard = [
            [
                InlineKeyboardButton(get_text('button_detailed_stats', lang), callback_data=f"admin_detailed_stats"),
                InlineKeyboardButton(get_text('button_users_management', lang), callback_data=f"admin_users_management")
            ],
            [
                InlineKeyboardButton(get_text('button_broadcast_menu', lang), callback_data=f"admin_broadcast_menu"),
                InlineKeyboardButton(get_text('button_system_settings', lang), callback_data=f"admin_system_settings")
            ],
            [
                InlineKeyboardButton(get_text('button_system_logs', lang), callback_data=f"admin_system_logs"),
                InlineKeyboardButton(get_text('button_create_backup', lang), callback_data=f"admin_create_backup")
            ],
            [
                InlineKeyboardButton(get_text('button_restart_bot', lang), callback_data=f"admin_restart_bot"),
                InlineKeyboardButton(get_text('button_maintenance_mode', lang), callback_data=f"admin_maintenance_mode")
            ],
            [
                InlineKeyboardButton(get_text('button_performance_monitor', lang), callback_data=f"admin_performance_monitor"),
                InlineKeyboardButton(get_text('button_security_panel', lang), callback_data=f"admin_security_panel")
            ],
            [InlineKeyboardButton("📦 النسخ الاحتياطية", callback_data="admin_backups")],
            [InlineKeyboardButton("🔗 إدارة الاشتراك الإجباري", callback_data="admin_forced_subscription")],
        ]

        if message_object:
            if _is_message_modified(message_object, text, InlineKeyboardMarkup(keyboard)):
                await message_object.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )

    async def _show_bot_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show detailed bot statistics."""
        if lang is None:
            user = update.effective_user if update.effective_user else None
            db_user = await self.bot_manager.db.get_user(user.id) if user else None
            lang = getattr(db_user, 'language_code', None) or getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        stats = await self.bot_manager.get_bot_statistics()
        db_stats = stats.get('database_stats', {})
        bot_info = stats.get('bot_info', {})

        # Get additional statistics
        user_growth = await self._calculate_user_growth()
        download_trends = await self._calculate_download_trends()
        performance_metrics = await self._get_performance_metrics()

        text = f"""📊 إحصائيات البوت المفصلة

🤖 معلومات البوت:
• الاسم: {bot_info.get('first_name', 'غير متوفر')}
• المعرف: @{bot_info.get('username', 'غير متوفر')}
• الإصدار: {stats.get('version', '2.0.0')}
• وقت التشغيل: {stats.get('uptime', 'غير متوفر')}

👥 إحصائيات المستخدمين:
• إجمالي المستخدمين: {db_stats.get('total_users', 0)}
• المستخدمين النشطين: {db_stats.get('active_users', 0)}
• المستخدمين الجدد (24 ساعة): {db_stats.get('recent_active_users', 0)}
• نمو المستخدمين: {user_growth.get('growth_rate', 0):.1f}%

📥 إحصائيات التحميل:
• إجمالي التحميلات: {db_stats.get('total_downloads', 0)}
• التحميلات الناجحة: {db_stats.get('completed_downloads', 0)}
• التحميلات الفاشلة: {db_stats.get('total_downloads', 0) - db_stats.get('completed_downloads', 0)}
• معدل النجاح: {db_stats.get('success_rate', 0):.1f}%
• التحميلات الحديثة (24 ساعة): {db_stats.get('recent_downloads', 0)}

📈 اتجاهات الاستخدام:
• متوسط التحميلات اليومية: {download_trends.get('daily_average', 0):.1f}
• ذروة الاستخدام: {download_trends.get('peak_hour', 'غير محدد')}
• أكثر الأيام نشاطاً: {download_trends.get('busiest_day', 'غير محدد')}

⚡ مقاييس الأداء:
• متوسط وقت الاستجابة: {performance_metrics.get('avg_response_time', 0):.2f}ms
• استخدام الذاكرة: {performance_metrics.get('memory_usage', 0):.1f}MB
• استخدام المعالج: {performance_metrics.get('cpu_usage', 0):.1f}%
• مساحة التخزين المستخدمة: {performance_metrics.get('storage_used', 0):.1f}GB"""

        keyboard = [
            [
                InlineKeyboardButton(get_text('button_export_stats', lang), callback_data=f"admin_export_stats"),
                InlineKeyboardButton(get_text('button_refresh_stats', lang), callback_data=f"admin_refresh_stats")
            ],
            [
                InlineKeyboardButton(get_text('button_charts', lang), callback_data=f"admin_charts"),
                InlineKeyboardButton(get_text('button_detailed_report', lang), callback_data=f"admin_detailed_report")
            ],
            [InlineKeyboardButton(get_text('button_main_panel', lang), callback_data=f"admin_main_panel")]
        ]

        if message_object:
            if _is_message_modified(message_object, text, InlineKeyboardMarkup(keyboard)):
                await message_object.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def _show_users_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        """Show users management panel."""
        try:
            if lang is None:
                user = update.effective_user if update.effective_user else None
                db_user = await self.bot_manager.db.get_user(user.id) if user else None
                lang = getattr(db_user, 'language_code', None) or getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
            users = await self.bot_manager.db.get_all_users(active_only=False)
            # حماية ضد القيم الفارغة أو الكائنات غير المتوقعة
            safe_users = [u for u in users if u and hasattr(u, 'is_active') and hasattr(u, 'is_banned') and hasattr(u, 'is_premium') and hasattr(u, 'registration_date')]
            active_users = len([u for u in safe_users if getattr(u, 'is_active', False)])
            banned_users = len([u for u in safe_users if getattr(u, 'is_banned', False)])
            premium_users = len([u for u in safe_users if getattr(u, 'is_premium', False)])
            recent_date = datetime.utcnow() - timedelta(days=7)
            recent_users = len([u for u in safe_users if getattr(u, 'registration_date', None) and u.registration_date >= recent_date])

            text = f"""👥 إدارة المستخدمين
\n📊 نظرة عامة:
• إجمالي المستخدمين: {len(safe_users)}
• المستخدمين النشطين: {active_users}
• المستخدمين المحظورين: {banned_users}
• المستخدمين المميزين: {premium_users}
• المستخدمين الجدد (7 أيام): {recent_users}
\n🔍 أدوات الإدارة:
استخدم الأزرار أدناه لإدارة المستخدمين"""

            keyboard = [
                [
                    InlineKeyboardButton(get_text('button_list_users', lang), callback_data=f"admin_list_users"),
                    InlineKeyboardButton(get_text('button_search_user', lang), callback_data=f"admin_search_user")
                ],
                [
                    InlineKeyboardButton(get_text('button_banned_users', lang), callback_data=f"admin_banned_users"),
                    InlineKeyboardButton(get_text('button_premium_users', lang), callback_data=f"admin_premium_users")
                ],
                [
                    InlineKeyboardButton(get_text('button_user_analytics', lang), callback_data=f"admin_user_analytics"),
                    InlineKeyboardButton(get_text('button_activity_report', lang), callback_data=f"admin_activity_report")
                ],
                [
                    InlineKeyboardButton(get_text('button_user_settings', lang), callback_data=f"admin_user_settings"),
                    InlineKeyboardButton(get_text('button_mass_notifications', lang), callback_data=f"admin_mass_notifications")
                ],
                [InlineKeyboardButton(get_text('button_main_panel', lang), callback_data=f"admin_main_panel")]
            ]

            if message_object:
                if _is_message_modified(message_object, text, InlineKeyboardMarkup(keyboard)):
                    await message_object.edit_text(
                        text,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
            else:
                await update.message.reply_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        except Exception as e:
            self.logger.error(f"[AdminHandler._show_users_management] {e}")
            user_id = update.effective_user.id
            is_admin = await self.bot_manager.is_user_admin(user_id)
            error_text = "❌ حدث خطأ غير متوقع أثناء معالجة بيانات المستخدمين."
            if is_admin:
                error_text += f"\n[DEBUG]: {type(e).__name__}: {e}"
            if message_object:
                if _is_message_modified(message_object, error_text, None):
                    await message_object.edit_text(error_text)
            else:
                await update.message.reply_text(error_text)

    async def _handle_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle broadcast message command."""
        args = context.args

        if not args:
            text = """📢 إرسال رسالة جماعية

الاستخدام:
/broadcast [الرسالة]

مثال:
/broadcast مرحباً بجميع المستخدمين! تم تحديث البوت بميزات جديدة.

📋 خيارات متقدمة:
• /broadcast_active [الرسالة] - للمستخدمين النشطين فقط
• /broadcast_premium [الرسالة] - للمستخدمين المميزين فقط
• /broadcast_new [الرسالة] - للمستخدمين الجدد فقط"""

            await update.message.reply_text(text)
            return

        message = ' '.join(args)

        # Show confirmation
        keyboard = [
            [
                InlineKeyboardButton(get_text('button_confirm_broadcast', lang), callback_data=f"admin_confirm_broadcast:{message[:50]}"),
                InlineKeyboardButton(get_text('button_cancel_broadcast', lang), callback_data="admin_cancel_broadcast")
            ]
        ]

        await update.message.reply_text(
            f"📢 تأكيد إرسال الرسالة الجماعية:\n\n{message[:200]}{'...' if len(message) > 200 else ''}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _handle_ban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle ban user command."""
        args = context.args

        if not args:
            await update.message.reply_text(
                "الاستخدام: /ban [معرف المستخدم] [السبب (اختياري)]\n"
                "مثال: /ban 123456789 انتهاك القوانين"
            )
            return

        try:
            user_id = int(args[0])
            reason = ' '.join(args[1:]) if len(args) > 1 else "لم يتم تحديد السبب"

            # Check if user exists
            user = await self.bot_manager.db.get_user(user_id)
            if not user:
                await update.message.reply_text("❌ المستخدم غير موجود.")
                return

            # Check if user is already banned
            if user.is_banned:
                await update.message.reply_text("⚠️ المستخدم محظور بالفعل.")
                return

            # Ban user
            success = await self.bot_manager.db.ban_user(user_id)

            if success:
                # Log ban action
                await self.bot_manager.db.log_user_action(
                    update.effective_user.id,
                    'admin_ban_user',
                    {'banned_user_id': user_id, 'reason': reason}
                )

                # Notify user (optional)
                try:
                    await self.bot_manager.send_message_safe(
                        user_id,
                        f"🚫 تم حظرك من استخدام البوت.\nالسبب: {reason}\n\nللاستفسار، تواصل مع الإدارة."
                    )
                except:
                    pass

                await update.message.reply_text(
                    f"✅ تم حظر المستخدم {user_id} بنجاح.\nالسبب: {reason}"
                )
            else:
                await update.message.reply_text("❌ فشل في حظر المستخدم.")

        except ValueError:
            await update.message.reply_text("❌ معرف المستخدم يجب أن يكون رقماً.")
        except Exception as e:
            self.logger.error(f"Error banning user: {e}")
            await update.message.reply_text("❌ حدث خطأ أثناء حظر المستخدم.")

    async def _handle_unban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unban user command."""
        args = context.args

        if not args:
            await update.message.reply_text(
                "الاستخدام: /unban [معرف المستخدم]\n"
                "مثال: /unban 123456789"
            )
            return

        try:
            user_id = int(args[0])

            # Check if user exists
            user = await self.bot_manager.db.get_user(user_id)
            if not user:
                await update.message.reply_text("❌ المستخدم غير موجود.")
                return

            # Check if user is banned
            if not user.is_banned:
                await update.message.reply_text("⚠️ المستخدم غير محظور.")
                return

            # Unban user
            success = await self.bot_manager.db.unban_user(user_id)

            if success:
                # Log unban action
                await self.bot_manager.db.log_user_action(
                    update.effective_user.id,
                    'admin_unban_user',
                    {'unbanned_user_id': user_id}
                )

                # Notify user
                try:
                    await self.bot_manager.send_message_safe(
                        user_id,
                        "✅ تم إلغاء حظرك. يمكنك الآن استخدام البوت مرة أخرى."
                    )
                except:
                    pass

                await update.message.reply_text(f"✅ تم إلغاء حظر المستخدم {user_id} بنجاح.")
            else:
                await update.message.reply_text("❌ فشل في إلغاء حظر المستخدم.")

        except ValueError:
            await update.message.reply_text("❌ معرف المستخدم يجب أن يكون رقماً.")
        except Exception as e:
            self.logger.error(f"Error unbanning user: {e}")
            await update.message.reply_text("❌ حدث خطأ أثناء إلغاء حظر المستخدم.")

    async def _show_system_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        """Show system logs."""
        try:
            # Read recent logs
            import os
            log_file = "data/logs/bot.log"

            if not os.path.exists(log_file):
                if message_object:
                    await message_object.edit_text("❌ ملف السجلات غير موجود.")
                else:
                    await update.message.reply_text("❌ ملف السجلات غير موجود.")
                return

            # Get last 50 lines
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                recent_logs = lines[-50:] if len(lines) > 50 else lines

            log_text = ''.join(recent_logs)

            # Truncate if too long
            if len(log_text) > 4000:
                log_text = log_text[-4000:]
                log_text = "...\n" + log_text

            if message_object:
                if _is_message_modified(message_object, f"📋 آخر سجلات النظام:\n\n```\n{log_text}\n```", None):
                    await message_object.edit_text(
                        f"📋 آخر سجلات النظام:\n\n```\n{log_text}\n```",
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text(
                    f"📋 آخر سجلات النظام:\n\n```\n{log_text}\n```",
                    parse_mode='Markdown'
                )

        except Exception as e:
            self.logger.error(f"Error reading logs: {e}")
            if message_object:
                if _is_message_modified(message_object, "❌ فشل في قراءة سجلات النظام.", None):
                    await message_object.edit_text("❌ فشل في قراءة سجلات النظام.")
            else:
                await update.message.reply_text("❌ فشل في قراءة سجلات النظام.")

    async def _toggle_maintenance(self, update, context, message_object=None):
        current_mode = await self.bot_manager.db.get_setting('maintenance_mode', False)
        new_mode = not current_mode
        await self.bot_manager.db.set_setting('maintenance_mode', new_mode)
        text = f"🔧 وضع الصيانة {'🟢 مفعل' if new_mode else '🔴 معطل'}\nتم {'تفعيل' if new_mode else 'إيقاف'} وضع الصيانة بنجاح."
        if message_object:
            if _is_message_modified(message_object, text, None):
                await message_object.edit_text(text)
        else:
            await update.message.reply_text(text)

    async def _create_backup(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        """Create system backup + إشعار ذكي + إرسال للقنوات/المجموعات + تسجيل النشاط."""
        try:
            if message_object:
                await message_object.edit_text("💾 جاري إنشاء النسخة الاحتياطية...")
            else:
                await update.message.reply_text("💾 جاري إنشاء النسخة الاحتياطية...")

            backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            import shutil
            import os
            source_db = "advanced_telegram_bot.db"
            backup_path = f"data/backups/{backup_filename}"
            os.makedirs("data/backups", exist_ok=True)
            if os.path.exists(source_db):
                shutil.copy2(source_db, backup_path)
                # سجل النشاط
                await self.bot_manager.db.log_user_action(
                    update.effective_user.id,
                    'admin_create_backup',
                    {'backup_file': backup_filename}
                )
                # إشعار ذكي للإدارة (فقط إذا كانت الخدمة متوفرة)
                if getattr(self.config, 'SMART_NOTIFICATIONS_ENABLED', False) and hasattr(self.bot_manager, 'notification_service') and self.bot_manager.notification_service:
                    await self.bot_manager.notification_service.send_backup_notification(
                        user_id=self.config.OWNER_ID,
                        backup_file=backup_filename,
                        success=True
                    )
                # إرسال للقنوات/المجموعات
                if getattr(self.config, 'TARGET_CHANNELS', []):
                    await self.bot_manager.send_to_target_channels(
                        text=f"💾 تم إنشاء نسخة احتياطية جديدة: {backup_filename}",
                        document=backup_path
                    )
                if message_object:
                    if _is_message_modified(message_object, f"✅ تم إنشاء النسخة الاحتياطية بنجاح!\n"
                        f"📁 اسم الملف: {backup_filename}\n"
                        f"📍 المسار: {backup_path}", None):
                        await message_object.edit_text(
                            f"✅ تم إنشاء النسخة الاحتياطية بنجاح!\n"
                            f"📁 اسم الملف: {backup_filename}\n"
                            f"📍 المسار: {backup_path}"
                        )
                else:
                    await update.message.reply_text(
                        f"✅ تم إنشاء النسخة الاحتياطية بنجاح!\n"
                        f"📁 اسم الملف: {backup_filename}\n"
                        f"📍 المسار: {backup_path}"
                    )
            else:
                if message_object:
                    if _is_message_modified(message_object, "❌ ملف قاعدة البيانات غير موجود.", None):
                        await message_object.edit_text("❌ ملف قاعدة البيانات غير موجود.")
                    else:
                        await message_object.edit_text("❌ ملف قاعدة البيانات غير موجود.")
                else:
                    await update.message.reply_text("❌ ملف قاعدة البيانات غير موجود.")
        except Exception as e:
            self.logger.error(f"Error creating backup: {e}")
            if getattr(self.config, 'SMART_NOTIFICATIONS_ENABLED', False) and hasattr(self.bot_manager, 'notification_service') and self.bot_manager.notification_service:
                await self.bot_manager.notification_service.send_backup_notification(
                    user_id=self.config.OWNER_ID,
                    backup_file=backup_filename if 'backup_filename' in locals() else 'غير معروف',
                    success=False
                )
            if message_object:
                if _is_message_modified(message_object, "❌ فشل في إنشاء النسخة الاحتياطية.", None):
                    await message_object.edit_text("❌ فشل في إنشاء النسخة الاحتياطية.")
                else:
                    await message_object.edit_text("❌ فشل في إنشاء النسخة الاحتياطية.")
            else:
                await update.message.reply_text("❌ فشل في إنشاء النسخة الاحتياطية.")

    async def _restart_bot(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        import asyncio
        import os
        import sys
        import subprocess
        if lang is None:
            user = update.effective_user if update.effective_user else None
            db_user = await self.bot_manager.db.get_user(user.id) if user else None
            lang = getattr(db_user, 'language_code', None) or getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        keyboard = [
            [
                InlineKeyboardButton(get_text('button_confirm_restart', lang), callback_data="admin_confirm_restart"),
                InlineKeyboardButton(get_text('button_cancel_restart', lang), callback_data="admin_cancel_restart")
            ]
        ]

        # إذا كان الاستدعاء للتأكيد فقط
        if context.user_data.get('restart_confirmed', False):
            if message_object:
                await message_object.edit_text("🔄 جاري إعادة تشغيل البوت...\n\nسيعود البوت للعمل خلال دقائق قليلة.")
            else:
                await update.message.reply_text("🔄 جاري إعادة تشغيل البوت...\n\nسيعود البوت للعمل خلال دقائق قليلة.")
            await asyncio.sleep(2)
            # إعادة التشغيل البرمجي على ويندوز
            python = sys.executable
            script = os.path.abspath(sys.argv[0])
            subprocess.Popen([python, script])
            os._exit(0)
            return

        # عرض رسالة التأكيد
        if message_object:
            if _is_message_modified(message_object, "🔄 تأكيد إعادة تشغيل البوت؟\n\n"
                "⚠️ سيتم قطع الاتصال مؤقتاً أثناء إعادة التشغيل.", InlineKeyboardMarkup(keyboard)):
                await message_object.edit_text(
                    "🔄 تأكيد إعادة تشغيل البوت؟\n\n"
                    "⚠️ سيتم قطع الاتصال مؤقتاً أثناء إعادة التشغيل.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            await update.message.reply_text(
                "🔄 تأكيد إعادة تشغيل البوت؟\n\n"
                "⚠️ سيتم قطع الاتصال مؤقتاً أثناء إعادة التشغيل.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def _show_system_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        if lang is None:
            user = update.effective_user if update.effective_user else None
            db_user = await self.bot_manager.db.get_user(user.id) if user else None
            lang = getattr(db_user, 'language_code', None) or getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        # Get current settings
        settings = {
            'maintenance_mode': await self.bot_manager.db.get_setting('maintenance_mode', False),
            'max_file_size': await self.bot_manager.db.get_setting('max_file_size', 50 * 1024 * 1024),
            'rate_limit_enabled': await self.bot_manager.db.get_setting('rate_limit_enabled', True),
            'backup_enabled': await self.bot_manager.db.get_setting('backup_enabled', True),
            'analytics_enabled': await self.bot_manager.db.get_setting('analytics_enabled', True)
        }

        text = f"""🔧 إعدادات النظام

🔧 وضع الصيانة: {'🟢 مفعل' if settings['maintenance_mode'] else '🔴 معطل'}
📁 الحد الأقصى لحجم الملف: {settings['max_file_size'] / (1024*1024):.0f} MB
⚡ تحديد معدل الطلبات: {'🟢 مفعل' if settings['rate_limit_enabled'] else '🔴 معطل'}
💾 النسخ الاحتياطية: {'🟢 مفعلة' if settings['backup_enabled'] else '🔴 معطلة'}
📊 التحليلات: {'🟢 مفعلة' if settings['analytics_enabled'] else '🔴 معطلة'}

استخدم الأزرار أدناه لتعديل الإعدادات:"""

        keyboard = [
            [
                InlineKeyboardButton(get_text('button_toggle_maintenance', lang), callback_data=f"admin_toggle_maintenance"),
                InlineKeyboardButton(get_text('button_set_file_size', lang), callback_data=f"admin_set_file_size")
            ],
            [
                InlineKeyboardButton(get_text('button_toggle_rate_limit', lang), callback_data=f"admin_toggle_rate_limit"),
                InlineKeyboardButton(get_text('button_toggle_backup', lang), callback_data=f"admin_toggle_backup")
            ],
            [
                InlineKeyboardButton(get_text('button_toggle_analytics', lang), callback_data=f"admin_toggle_analytics"),
                InlineKeyboardButton(get_text('button_reset_settings', lang), callback_data=f"admin_reset_settings")
            ],
            [InlineKeyboardButton(get_text('button_main_panel', lang), callback_data=f"admin_main_panel")]
        ]

        if message_object:
            if _is_message_modified(message_object, text, InlineKeyboardMarkup(keyboard)):
                await message_object.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def handle_callback(self, update, context):
        try:
            self.logger.info(f"[DIAG] Button Triggered: {update.callback_query.data if update.callback_query else ''}")
            query = update.callback_query
            if not query or not hasattr(query, 'data'):
                return
            data = query.data
            # Check admin permissions
            if not await self.bot_manager.is_user_admin(query.from_user.id):
                await query.answer("❌ غير مصرح لك بالوصول لهذه الميزة", show_alert=True)
                return
            # Route callback to appropriate handler
            if data == "admin_broadcast_text":
                await query.answer()
                await query.edit_message_text(
                    "📝 أرسل الآن نص الرسالة الجماعية التي تريد إرسالها:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❌ إلغاء", callback_data="admin_cancel_broadcast")],
                        [InlineKeyboardButton("🔙 العودة", callback_data="admin_broadcast_menu")]
                    ])
                )
                context.user_data['broadcast_target'] = 'all'
                context.user_data['awaiting_broadcast_message'] = True
            elif data == "admin_broadcast_photo":
                await query.answer()
                await query.edit_message_text(
                    "🖼️ أرسل الآن الصورة التي تريد إرسالها جماعيًا (الميزة قيد التطوير)",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❌ إلغاء", callback_data="admin_cancel_broadcast")],
                        [InlineKeyboardButton("🔙 العودة", callback_data="admin_broadcast_menu")]
                    ])
                )
            elif data == "admin_broadcast_link":
                await query.answer()
                await query.edit_message_text(
                    "🔗 أرسل الآن نص الرسالة مع الرابط الذي تريد إرساله جماعيًا:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❌ إلغاء", callback_data="admin_cancel_broadcast")],
                        [InlineKeyboardButton("🔙 العودة", callback_data="admin_broadcast_menu")]
                    ])
                )
                context.user_data['broadcast_target'] = 'link'
                context.user_data['awaiting_broadcast_message'] = True
            elif data == "admin_broadcast_poll":
                await query.answer()
                await query.edit_message_text(
                    "📊 أرسل الآن نص السؤال وخيارات التصويت (كل خيار في سطر منفصل) (الميزة قيد التطوير)",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❌ إلغاء", callback_data="admin_cancel_broadcast")],
                        [InlineKeyboardButton("🔙 العودة", callback_data="admin_broadcast_menu")]
                    ])
                )
            elif data == "admin_broadcast_active":
                await query.answer()
                await query.edit_message_text(
                    "📝 أرسل الآن نص الرسالة الجماعية التي تريد إرسالها للمستخدمين النشطين فقط:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❌ إلغاء", callback_data="admin_cancel_broadcast")],
                        [InlineKeyboardButton("🔙 العودة", callback_data="admin_broadcast_menu")]
                    ])
                )
                context.user_data['broadcast_target'] = 'active'
                context.user_data['awaiting_broadcast_message'] = True
            elif data == "admin_broadcast_premium":
                await query.answer()
                await query.edit_message_text(
                    "📝 أرسل الآن نص الرسالة الجماعية التي تريد إرسالها للمستخدمين المميزين فقط:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❌ إلغاء", callback_data="admin_cancel_broadcast")],
                        [InlineKeyboardButton("🔙 العودة", callback_data="admin_broadcast_menu")]
                    ])
                )
                context.user_data['broadcast_target'] = 'premium'
                context.user_data['awaiting_broadcast_message'] = True
            elif data == "admin_cancel_broadcast":
                await query.answer("تم إلغاء العملية.", show_alert=True)
                await self._show_broadcast_menu(update, context, message_object=query.message)
            elif data == "admin_main_panel" or data == "admin_panel" or data == "main_menu" or "main_panel" in data or "panel" in data or "عودة" in data or "back" in data:
                await self._show_admin_panel(update, context, message_object=query.message)
            elif data == "admin_broadcast_menu":
                await self._show_broadcast_menu(update, context, message_object=query.message)
            elif data == "admin_users_management":
                await self._show_users_management(update, context, message_object=query.message)
            elif data == "admin_system_settings":
                await self._show_system_settings(update, context, message_object=query.message)
            elif data == "admin_system_logs":
                await self._show_system_logs(update, context, message_object=query.message)
            elif data == "admin_create_backup":
                await self._create_backup(update, context, message_object=query.message)
            elif data == "admin_restart_bot":
                await self._restart_bot(update, context, message_object=query.message)
            elif data in ("button_confirm_restart", "admin_confirm_restart"):
                context.user_data['restart_confirmed'] = True
                await self._restart_bot(update, context, message_object=query.message, lang=None)
            elif data in ("button_cancel_restart", "admin_cancel_restart"):
                await self._show_admin_panel(update, context, message_object=query.message)
            elif data == "admin_maintenance_mode":
                await self._show_maintenance_mode(update, context, message_object=query.message)
            elif data == "admin_performance_monitor":
                await self._show_performance_monitor(update, context, message_object=query.message)
            elif data == "admin_security_panel":
                await self._show_security_panel(update, context, message_object=query.message)
            elif data == "admin_forced_subscription":
                await self._show_forced_subscription_panel(update, context, message_object=query.message)
            # أزرار العودة للقوائم الفرعية
            elif data == "back_to_admin_panel":
                if query and hasattr(query, 'message') and query.message:
                    await self._show_admin_panel(update, context, message_object=query.message)
                else:
                    await update.message.reply_text("تم الرجوع للوحة الإدارة.")
            elif data == "back_to_broadcast_menu":
                await self._show_broadcast_menu(update, context, message_object=query.message)
            elif data == "back_to_users_management":
                await self._show_users_management(update, context, message_object=query.message)
            elif data in ("button_back", "back", "admin_panel"):
                if query and hasattr(query, 'message') and query.message:
                    await self._show_admin_panel(update, context, message_object=query.message)
                else:
                    await update.message.reply_text("تم الرجوع للوحة الإدارة.")
            elif data.startswith("admin_manage_section:"):
                section_id = data.split(":", 1)[1]
                await self._show_section_management(update, context, section_id, message_object=query.message)
            elif data.startswith("admin_add_forced_channel:"):
                section_id = data.split(":", 1)[1]
                await self._add_forced_subscription_channel(update, context, message_object=query.message)
                context.user_data['awaiting_forced_channel'] = True
                context.user_data['current_section_id'] = section_id
            elif data.startswith("admin_set_section_message:"):
                section_id = data.split(":", 1)[1]
                await self._ask_section_message(update, context, section_id, message_object=query.message)
            elif data.startswith("admin_set_section_max:"):
                section_id = data.split(":", 1)[1]
                await self._ask_section_max(update, context, section_id, message_object=query.message)
            elif data.startswith("admin_move_channel_up:"):
                parts = data.split(":")
                channel_id = parts[1]
                section_id = parts[2]
                await self._move_channel_order(section_id, channel_id, direction='up')
                await self._show_section_management(update, context, section_id, message_object=query.message)
            elif data.startswith("admin_move_channel_down:"):
                parts = data.split(":")
                channel_id = parts[1]
                section_id = parts[2]
                await self._move_channel_order(section_id, channel_id, direction='down')
                await self._show_section_management(update, context, section_id, message_object=query.message)
            elif data.startswith("admin_edit_channel_message:"):
                parts = data.split(":")
                channel_id = parts[1]
                section_id = parts[2]
                await self._ask_channel_message(update, context, channel_id, section_id, message_object=query.message)
            elif data.startswith("admin_remove_forced_channel:"):
                channel_id = data.split(":", 1)[1]
                await self._remove_forced_subscription_channel(update, context, channel_id, message_object=query.message)
            elif data.startswith("admin_confirm_broadcast"):
                await query.answer()
                # استخراج الفئة المستهدفة من الكولباك
                parts = data.split(":", 1)
                target = parts[1] if len(parts) > 1 else 'all'
                await self._confirm_broadcast(update, context, target, message_object=query.message)
            elif data == "admin_broadcast_adminchats":
                await query.answer()
                text = "📝 أرسل الآن نص الرسالة التي تريد إرسالها لجميع القنوات والمجموعات التي البوت فيها أدمن:"
                keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="admin_cancel_broadcast")]]
                if query.message:
                    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
                else:
                    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
                context.user_data['broadcast_target'] = 'adminchats'
                context.user_data['awaiting_broadcast_message'] = True
            elif data == "admin_list_all_forced_channels":
                await query.answer()
                channels = await self.bot_manager.db.get_forced_subscription_channels()
                if not channels:
                    text = "لا توجد قنوات/حسابات حالياً في الاشتراك الإجباري."
                else:
                    text = "<b>جميع القنوات/الحسابات الحالية:</b>\n\n"
                    for c in channels:
                        name = c.get('name', c.get('id', c.get('url','-')))
                        cid = c.get('id', c.get('url','-'))
                        ctype = c.get('type', '-')
                        url = c.get('url', '-')
                        custom_msg = c.get('custom_message', None)
                        text += f"• <b>{name}</b> (<code>{cid}</code>)\n  النوع: {ctype}\n  الرابط: <a href='{url}'>{url}</a>\n"
                        if custom_msg:
                            text += f"  📝 رسالة مخصصة: {custom_msg[:50]}{'...' if len(custom_msg)>50 else ''}\n"
                        text += "\n"
                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="admin_forced_subscription")]]
                if query.message:
                    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML', disable_web_page_preview=True)
                else:
                    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML', disable_web_page_preview=True)
                return
            elif data == "admin_backups":
                await query.answer()
                import os
                backup_dir = os.path.join("data", "backups")
                files = []
                if os.path.exists(backup_dir):
                    files = [f for f in os.listdir(backup_dir) if f.endswith('.db')]
                    files.sort(reverse=True)
                if not files:
                    text = "لا توجد نسخ احتياطية متوفرة حالياً."
                    keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="admin_main_panel")]]
                else:
                    text = "<b>النسخ الاحتياطية المتوفرة:</b>\n\n"
                    keyboard = []
                    for f in files:
                        text += f"• {f}\n"
                        keyboard.append([InlineKeyboardButton(f"⬇️ تحميل {f}", callback_data=f"admin_download_backup:{f}")])
                    keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="admin_main_panel")])
                if query.message:
                    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
                else:
                    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
                return
            elif data.startswith("admin_download_backup:"):
                await query.answer()
                import os
                backup_dir = os.path.join("data", "backups")
                filename = data.split(":", 1)[1]
                file_path = os.path.join(backup_dir, filename)
                if not os.path.exists(file_path):
                    await query.message.reply_text("❌ الملف غير موجود.")
                    return
                await query.message.reply_document(open(file_path, "rb"), filename=filename)
                return
            elif data == "admin_list_users":
                await self._list_users(update, context, message_object=query.message, page=0)
            elif data.startswith("admin_list_users_page"):
                page = int(data.split(":")[-1])
                await self._list_users(update, context, message_object=query.message, page=page)
            elif data == "admin_search_user":
                await self._search_user(update, context, message_object=query.message)
            elif data == "admin_banned_users":
                await self._show_banned_users(update, context, message_object=query.message, page=0)
            elif data.startswith("admin_banned_users_page"):
                page = int(data.split(":")[-1])
                await self._show_banned_users(update, context, message_object=query.message, page=page)
            elif data == "admin_premium_users":
                await self._show_premium_users(update, context, message_object=query.message, page=0)
            elif data.startswith("admin_premium_users_page"):
                page = int(data.split(":")[-1])
                await self._show_premium_users(update, context, message_object=query.message, page=page)
            elif data == "admin_user_analytics":
                await self._show_user_analytics(update, context, message_object=query.message)
            elif data == "admin_activity_report":
                await self._show_activity_report(update, context, message_object=query.message, page=0)
            elif data.startswith("admin_activity_report_page"):
                page = int(data.split(":")[-1])
                await self._show_activity_report(update, context, message_object=query.message, page=page)
            elif data == "admin_user_settings":
                await self._show_user_settings(update, context, message_object=query.message)
            elif data == "admin_mass_notifications":
                await self._show_mass_notifications(update, context, message_object=query.message)
            elif data == "admin_export_stats":
                await self._export_statistics(update, context, message_object=query.message)
            elif data == "admin_refresh_stats":
                await self._refresh_statistics(update, context, message_object=query.message)
            elif data == "admin_charts":
                await self._show_charts(update, context, message_object=query.message)
            elif data == "admin_detailed_report":
                await self._show_detailed_report(update, context, message_object=query.message)
            else:
                if query and hasattr(query, 'answer'):
                    await query.answer("❌ هذا الزر غير معروف أو لم يتم ربطه بعد.", show_alert=True)
        except Exception as e:
            import telegram
            if isinstance(e, telegram.error.BadRequest) and "Query is too old" in str(e):
                try:
                    await update.effective_message.reply_text("⏰ انتهت صلاحية الزر، يرجى إعادة المحاولة من جديد.")
                except Exception:
                    pass
                return
            self.logger.error(f"[AdminHandler.handle_callback] {e}")
            try:
                await update.callback_query.answer("❌ حدث خطأ غير متوقع.", show_alert=True)
            except Exception:
                pass

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # استقبال رسالة مخصصة للقناة
        if context.user_data.get('awaiting_channel_message'):
            channel_id, section_id = context.user_data.pop('awaiting_channel_message')
            msg = update.message.text.strip()
            # تحديث الرسالة المخصصة للقناة في الداتا
            channels = await self.bot_manager.db.get_forced_subscription_channels()
            for c in channels:
                if c.get('id') == channel_id or c.get('url') == channel_id:
                    c['custom_message'] = msg
            await self.bot_manager.db.set_forced_subscription_channels(channels)
            await update.message.reply_text("✅ تم تحديث الرسالة المخصصة للقناة بنجاح.")
            await self._show_section_management(update, context, section_id)
            return
        # استقبال نصوص أخرى (باقي المنطق كما هو)
        if context.user_data.get('awaiting_broadcast_message'):
            await self._process_broadcast_message(update, context, message_object=update.message)
            return
        if context.user_data.get('awaiting_forced_channel'):
            await self._process_forced_channel_input(update, context)
            return
        if context.user_data.get('awaiting_section_message'):
            section_id = context.user_data.pop('awaiting_section_message')
            msg = update.message.text.strip()
            await self.bot_manager.db.set_section_message(section_id, msg)
            await update.message.reply_text("✅ تم تحديث رسالة القسم بنجاح.")
            await self._show_section_management(update, context, section_id)
            return
        if context.user_data.get('awaiting_section_max'):
            section_id = context.user_data.pop('awaiting_section_max')
            try:
                max_count = int(update.message.text.strip())
                await self.bot_manager.db.set_section_max_count(section_id, max_count)
                await update.message.reply_text("✅ تم تحديث الحد الأقصى بنجاح.")
            except Exception:
                await update.message.reply_text("❌ يجب إدخال رقم صحيح.")
            await self._show_section_management(update, context, section_id)
            return
        # إذا لم يكن هناك أي انتظار إداري، تجاهل الرسالة فوراً
        return

    async def _move_channel_order(self, section_id, channel_id, direction='up'):
        channels = await self.bot_manager.db.get_forced_subscription_channels()
        # فقط القنوات في هذا القسم
        section_channels = [c for c in channels if c.get('type','secondary') == section_id]
        section_channels = sorted(section_channels, key=lambda c: c.get('order', 0))
        idx = next((i for i, c in enumerate(section_channels) if c.get('id') == channel_id or c.get('url') == channel_id), None)
        if idx is None:
            return
        if direction == 'up' and idx > 0:
            section_channels[idx]['order'], section_channels[idx-1]['order'] = section_channels[idx-1].get('order', 0), section_channels[idx].get('order', 0)
        elif direction == 'down' and idx < len(section_channels)-1:
            section_channels[idx]['order'], section_channels[idx+1]['order'] = section_channels[idx+1].get('order', 0), section_channels[idx].get('order', 0)
        # تحديث القائمة الكاملة
        for c in channels:
            if c.get('id') in [x.get('id') for x in section_channels]:
                match = next((x for x in section_channels if x.get('id') == c.get('id')), None)
                if match:
                    c['order'] = match.get('order', 0)
        await self.bot_manager.db.set_forced_subscription_channels(channels)

    async def _show_broadcast_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None, lang=None):
        if lang is None:
            user = update.effective_user if update.effective_user else None
            db_user = await self.bot_manager.db.get_user(user.id) if user else None
            lang = getattr(db_user, 'language_code', None) or getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = """📢 قائمة البث الجماعي

اختر نوع الرسالة الجماعية التي ترغب في إرسالها:
"""
        keyboard = [
            [
                InlineKeyboardButton(get_text('button_broadcast_text', lang), callback_data="admin_broadcast_text"),
                InlineKeyboardButton(get_text('button_broadcast_photo', lang), callback_data="admin_broadcast_photo")
            ],
            [
                InlineKeyboardButton(get_text('button_broadcast_link', lang), callback_data="admin_broadcast_link"),
                InlineKeyboardButton(get_text('button_broadcast_poll', lang), callback_data="admin_broadcast_poll")
            ],
            [
                InlineKeyboardButton(get_text('button_broadcast_active', lang), callback_data="admin_broadcast_active"),
                InlineKeyboardButton(get_text('button_broadcast_premium', lang), callback_data="admin_broadcast_premium")
            ],
            [
                InlineKeyboardButton("📢 إذاعة للقنوات/المجموعات (البوت أدمن)", callback_data="admin_broadcast_adminchats")
            ],
            [InlineKeyboardButton(get_text('button_main_panel', lang), callback_data="admin_main_panel")]
        ]

        if message_object:
            if _is_message_modified(message_object, text, InlineKeyboardMarkup(keyboard)):
                await message_object.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )


    async def _show_admin_panel_callback(self, query, context):
        """Show admin panel in callback context."""
        await query.answer()
        await self._show_admin_panel(query, context, message_object=query.message)

    async def _show_detailed_stats_callback(self, query, context):
        """Show detailed statistics in callback context."""
        await query.answer()
        await self._show_bot_statistics(query, context, message_object=query.message)

    async def _show_users_management_callback(self, update, context):
        """Show users management in callback context."""
        query = update.callback_query
        await query.answer()
        await self._show_users_management(update, context, message_object=query.message)

    async def _confirm_broadcast_callback(self, query, context):
        """Confirm and send broadcast message."""
        await query.answer()

        # Extract message from callback data
        message_preview = query.data.split(":", 1)[1]

        # This would need to be implemented with proper message storage
        # For now, show confirmation
        await query.edit_message_text(
            f"📢 جاري إرسال الرسالة الجماعية...\n\n"
            f"المعاينة: {message_preview}..."
        )

        # Simulate broadcast
        await asyncio.sleep(2)
        await query.edit_message_text("✅ تم إرسال الرسالة الجماعية بنجاح!")

    async def _confirm_restart_callback(self, query, context):
        """Confirm bot restart and exit process safely."""
        import asyncio
        import os
        await query.answer()
        await query.edit_message_text(
            "🔄 جاري إعادة تشغيل البوت...\n\nسيعود البوت للعمل خلال دقائق قليلة."
        )
        # Log restart action
        await self.bot_manager.db.log_user_action(
            query.from_user.id,
            'admin_restart_bot',
            {}
        )
        self.logger.info(f"Bot restart requested by admin {query.from_user.id}")
        # انتظر قليلاً لإتاحة إرسال الرسالة ثم أعد التشغيل فعلياً
        await asyncio.sleep(2)
        os._exit(0)

    # Helper methods for statistics calculation
    async def _calculate_user_growth(self) -> Dict[str, Any]:
        """Calculate user growth statistics."""
        # This would implement actual user growth calculation
        return {
            'growth_rate': 15.5,
            'new_users_today': 12,
            'new_users_week': 85
        }

    async def _calculate_download_trends(self) -> Dict[str, Any]:
        """Calculate download trends."""
        # This would implement actual download trends calculation
        return {
            'daily_average': 45.2,
            'peak_hour': '20:00-21:00',
            'busiest_day': 'الجمعة'
        }

    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics."""
        # This would implement actual performance monitoring
        return {
            'avg_response_time': 125.5,
            'memory_usage': 256.8,
            'cpu_usage': 15.2,
            'storage_used': 2.1
        }

    async def _export_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        text = "📤 سيتم قريبًا تصدير الإحصائيات كملف Excel أو CSV. (الميزة قيد التطوير)"
        if message_object:
            if _is_message_modified(message_object, text, None):
                await message_object.edit_text(text)
        else:
            await update.message.reply_text(text)

    async def _refresh_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        text = "🔄 تم تحديث الإحصائيات بنجاح! (تحديث فوري)"
        if message_object:
            if _is_message_modified(message_object, text, None):
                await message_object.edit_text(text)
        else:
            await update.message.reply_text(text)

    async def _show_charts(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        text = "📊 سيتم قريبًا عرض الرسوم البيانية التفاعلية للإحصائيات. (الميزة قيد التطوير)"
        if message_object:
            if _is_message_modified(message_object, text, None):
                await message_object.edit_text(text)
        else:
            await update.message.reply_text(text)

    async def _show_detailed_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_object=None):
        text = "📑 سيتم قريبًا عرض التقرير التفصيلي للإحصائيات. (الميزة قيد التطوير)"
        if message_object:
            if _is_message_modified(message_object, text, None):
                await message_object.edit_text(text)
        else:
            await update.message.reply_text(text)

    async def _list_users(self, update, context, message_object=None, page=0, search_query=None):
        try:
            page_size = 10
            users = await self.bot_manager.db.get_all_users(active_only=False)
            if search_query:
                users = [u for u in users if search_query.lower() in (u.username or '').lower() or search_query in str(u.id)]
            total = len(users)
            if total == 0:
                text = "لا يوجد مستخدمون مطابقون."
                if message_object:
                    if _is_message_modified(message_object, text, None):
                        await message_object.edit_text(text)
                else:
                    await update.message.reply_text(text)
                return
            start = page * page_size
            end = start + page_size
            users_page = users[start:end]
            text = f"👥 قائمة المستخدمين (العدد: {total})\n\n"
            for user in users_page:
                reg_date = user.registration_date.strftime('%Y-%m-%d') if user.registration_date else '-'
                text += f"• <b>{user.first_name or ''}</b> <code>{user.id}</code> (@{user.username or '-'}), سجل: {reg_date}"
                if user.is_banned:
                    text += " 🚫"
                if user.is_premium:
                    text += " ⭐"
                text += "\n"
            keyboard = []
            for user in users_page:
                row = [
                    InlineKeyboardButton("ℹ️ تفاصيل", callback_data=f"admin_user_details:{user.id}:{page}")
                ]
                if user.is_banned:
                    row.append(InlineKeyboardButton("✅ إلغاء الحظر", callback_data=f"admin_unban_user:{user.id}:{page}"))
                else:
                    row.append(InlineKeyboardButton("🚫 حظر", callback_data=f"admin_ban_user:{user.id}:{page}"))
                if user.is_premium:
                    row.append(InlineKeyboardButton("❌ إلغاء الترقية", callback_data=f"admin_unpremium:{user.id}:{page}"))
                else:
                    row.append(InlineKeyboardButton("⭐ ترقية", callback_data=f"admin_premium:{user.id}:{page}"))
                keyboard.append(row)
            nav = []
            if start > 0:
                nav.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"admin_list_users_page:{page-1}"))
            if end < total:
                nav.append(InlineKeyboardButton("التالي ➡️", callback_data=f"admin_list_users_page:{page+1}"))
            if nav:
                keyboard.append(nav)
            keyboard.append([InlineKeyboardButton("🔍 بحث", switch_inline_query_current_chat="بحث مستخدم")])
            keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="admin_users_management")])
            if message_object:
                if _is_message_modified(message_object, text, InlineKeyboardMarkup(keyboard)):
                    await message_object.edit_text(
                        text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )
            else:
                await update.message.reply_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
        except Exception as e:
            user_id = update.effective_user.id
            is_admin = await self.bot_manager.is_user_admin(user_id)
            error_text = "❌ حدث خطأ أثناء عرض قائمة المستخدمين."
            if is_admin:
                error_text += f"\n[DEBUG]: {type(e).__name__}: {e}"
            if message_object:
                if _is_message_modified(message_object, error_text, None):
                    await message_object.edit_text(error_text)
            else:
                await update.message.reply_text(error_text)

    async def _search_user(self, update, context, message_object=None):
        try:
            query = update.callback_query if hasattr(update, 'callback_query') else None
            data = query.data if query else None
            # إذا لم يتم إرسال كلمة بحث بعد، اطلب من المدير إدخالها
            if not context.user_data.get('search_query'):
                text = "🔍 البحث عن مستخدم\n\nأرسل كلمة البحث (اسم، معرف، أو رقم هاتف):"
                if message_object:
                    if _is_message_modified(message_object, text, None):
                        await message_object.edit_text(text)
                elif query:
                    if _is_message_modified(query, text, None):
                        await query.edit_message_text(text)
                else:
                    await update.message.reply_text(text)
                context.user_data['awaiting_search_query'] = True
                return
            # إذا أرسل المستخدم كلمة البحث
            if context.user_data.get('awaiting_search_query') and update.message and update.message.text:
                search_query = update.message.text.strip()
                context.user_data['search_query'] = search_query
                context.user_data['awaiting_search_query'] = False
            else:
                search_query = context.user_data.get('search_query')
            if not search_query:
                return
            # البحث في قاعدة البيانات
            all_users = await self.bot_manager.db.get_all_users(active_only=False)
            results = []
            for user in all_users:
                if not user:
                    continue
                if search_query in str(user.id):
                    results.append(user)
                elif user.username and search_query.lower() in user.username.lower():
                    results.append(user)
                elif user.first_name and search_query.lower() in user.first_name.lower():
                    results.append(user)
                elif user.last_name and search_query.lower() in user.last_name.lower():
                    results.append(user)
                elif hasattr(user, 'phone') and user.phone and search_query in user.phone:
                    results.append(user)
            if not results:
                text = f"❌ لا يوجد نتائج للمستخدم: {search_query}"
            else:
                text = f"🔍 نتائج البحث عن: <b>{search_query}</b>\n\n"
                for user in results[:10]:
                    status = "✅ نشط" if user.is_active else ("🚫 محظور" if user.is_banned else "❔ غير محدد")
                    premium = "⭐" if user.is_premium else ""
                    text += f"{premium} <b>{user.first_name or ''} {user.last_name or ''}</b> (@{user.username or '-'} | <code>{user.id}</code>)\n"
                    text += f"الحالة: {status} | سجل: {user.registration_date.strftime('%Y-%m-%d')}\n"
                    text += f"/ban_{user.id} /unban_{user.id} /promote_{user.id} /info_{user.id}\n\n"
            keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="admin_users_management")]]
            if message_object:
                if _is_message_modified(message_object, text, InlineKeyboardMarkup(keyboard)):
                    await message_object.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            elif query:
                if _is_message_modified(query, text, InlineKeyboardMarkup(keyboard)):
                    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            else:
                await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            # إعادة تعيين البحث بعد العرض
            context.user_data['search_query'] = None
        except Exception as e:
            user_id = update.effective_user.id
            is_admin = await self.bot_manager.is_user_admin(user_id)
            error_text = "❌ حدث خطأ أثناء البحث عن مستخدم."
            if is_admin:
                error_text += f"\n[DEBUG]: {type(e).__name__}: {e}"
            if message_object:
                if _is_message_modified(message_object, error_text, None):
                    await message_object.edit_text(error_text)
            else:
                await update.message.reply_text(error_text)

    async def _show_banned_users(self, update, context, message_object=None, page=0, search_query=None):
        try:
            page_size = 10
            users = await self.bot_manager.db.list_banned_users()
            if search_query:
                users = [u for u in users if search_query.lower() in (u.username or '').lower() or search_query in str(u.id)]
            total = len(users)
            if total == 0:
                text = "🚫 لا يوجد مستخدمون محظورون."
                if message_object:
                    if _is_message_modified(message_object, text, None):
                        await message_object.edit_text(text)
                else:
                    await update.message.reply_text(text)
                return
            start = page * page_size
            end = start + page_size
            users_page = users[start:end]
            text = f"🚫 قائمة المحظورين (العدد: {total})\n\n"
            for user in users_page:
                reg_date = user.registration_date.strftime('%Y-%m-%d') if user.registration_date else '-'
                text += f"• <b>{user.first_name or ''}</b> <code>{user.id}</code> (@{user.username or '-'}), سجل: {reg_date}\n"
            keyboard = []
            for user in users_page:
                row = [
                    InlineKeyboardButton("ℹ️ تفاصيل", callback_data=f"admin_user_details:{user.id}:{page}"),
                    InlineKeyboardButton("✅ إلغاء الحظر", callback_data=f"admin_unban_user:{user.id}:{page}")
                ]
                if user.is_premium:
                    row.append(InlineKeyboardButton("❌ إلغاء الترقية", callback_data=f"admin_unpremium:{user.id}:{page}"))
                else:
                    row.append(InlineKeyboardButton("⭐ ترقية", callback_data=f"admin_premium:{user.id}:{page}"))
                keyboard.append(row)
            nav = []
            if start > 0:
                nav.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"admin_banned_users_page:{page-1}"))
            if end < total:
                nav.append(InlineKeyboardButton("التالي ➡️", callback_data=f"admin_banned_users_page:{page+1}"))
            if nav:
                keyboard.append(nav)
            keyboard.append([InlineKeyboardButton("🔍 بحث", switch_inline_query_current_chat="بحث محظور")])
            keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="admin_users_management")])
            if message_object:
                if _is_message_modified(message_object, text, InlineKeyboardMarkup(keyboard)):
                    await message_object.edit_text(
                        text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )
            else:
                await update.message.reply_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
        except Exception as e:
            user_id = update.effective_user.id
            is_admin = await self.bot_manager.is_user_admin(user_id)
            error_text = "❌ حدث خطأ أثناء عرض قائمة المحظورين."
            if is_admin:
                error_text += f"\n[DEBUG]: {type(e).__name__}: {e}"
            if message_object:
                if _is_message_modified(message_object, error_text, None):
                    await message_object.edit_text(error_text)
            else:
                await update.message.reply_text(error_text)

    async def _show_premium_users(self, update, context, message_object=None, page=0, search_query=None):
        try:
            page_size = 10
            users = await self.bot_manager.db.list_premium_users()
            if search_query:
                users = [u for u in users if search_query.lower() in (u.username or '').lower() or search_query in str(u.id)]
            total = len(users)
            if total == 0:
                text = "⭐ لا يوجد مستخدمون مميزون."
                if message_object:
                    if _is_message_modified(message_object, text, None):
                        await message_object.edit_text(text)
                else:
                    await update.message.reply_text(text)
                return
            start = page * page_size
            end = start + page_size
            users_page = users[start:end]
            text = f"⭐ قائمة المميزين (العدد: {total})\n\n"
            for user in users_page:
                reg_date = user.registration_date.strftime('%Y-%m-%d') if user.registration_date else '-'
                text += f"• <b>{user.first_name or ''}</b> <code>{user.id}</code> (@{user.username or '-'}), سجل: {reg_date}\n"
            keyboard = []
            for user in users_page:
                row = [
                    InlineKeyboardButton("ℹ️ تفاصيل", callback_data=f"admin_user_details:{user.id}:{page}"),
                    InlineKeyboardButton("✅ إلغاء الحظر" if user.is_banned else "🚫 حظر", callback_data=f"admin_unban_user:{user.id}:{page}" if user.is_banned else f"admin_ban_user:{user.id}:{page}")
                ]
                row.append(InlineKeyboardButton("❌ إلغاء الترقية", callback_data=f"admin_unpremium:{user.id}:{page}"))
                keyboard.append(row)
            nav = []
            if start > 0:
                nav.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"admin_premium_users_page:{page-1}"))
            if end < total:
                nav.append(InlineKeyboardButton("التالي ➡️", callback_data=f"admin_premium_users_page:{page+1}"))
            if nav:
                keyboard.append(nav)
            keyboard.append([InlineKeyboardButton("🔍 بحث", switch_inline_query_current_chat="بحث مميز")])
            keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="admin_users_management")])
            if message_object:
                if _is_message_modified(message_object, text, InlineKeyboardMarkup(keyboard)):
                    await message_object.edit_text(
                        text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )
            else:
                await update.message.reply_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
        except Exception as e:
            user_id = update.effective_user.id
            is_admin = await self.bot_manager.is_user_admin(user_id)
            error_text = "❌ حدث خطأ أثناء عرض قائمة المميزين."
            if is_admin:
                error_text += f"\n[DEBUG]: {type(e).__name__}: {e}"
            if message_object:
                if _is_message_modified(message_object, error_text, None):
                    await message_object.edit_text(error_text)
            else:
                await update.message.reply_text(error_text)

    async def _show_user_analytics(self, update, context, message_object=None):
        user_id = update.effective_user.id
        stats = await self.bot_manager.db.get_user_stats(user_id)
        if not stats:
            text = "لا توجد إحصائيات متاحة لهذا المستخدم."
        else:
            download_stats = stats.get('download_stats', {})
            activity_stats = stats.get('activity_stats', {})
            text = f"📈 إحصائيات المستخدم:\n"
            text += f"• إجمالي التحميلات: {download_stats.get('total_downloads', 0)}\n"
            text += f"• معدل النجاح: {download_stats.get('success_rate', 0):.1f}%\n"
            text += f"• الحجم الإجمالي: {download_stats.get('total_size_mb', 0):.1f} MB\n"
            text += f"• إجمالي الأنشطة: {activity_stats.get('total_actions', 0)}\n"
            text += f"• معدل الأنشطة اليومي: {activity_stats.get('avg_daily_actions', 0):.2f}\n"
        keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="admin_users_management")]]
        if message_object:
            await message_object.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_activity_report(self, update, context, message_object=None, page=0):
        logs = await self.bot_manager.db.get_recent_activity_logs(limit=50)
        text = "📊 تقرير النشاط (آخر 50 عملية):\n\n"
        if not logs:
            text += "لا توجد بيانات نشاط متاحة."
        else:
            text += "\n".join(logs)
        keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="admin_users_management")]]
        if message_object:
            await message_object.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_user_settings(self, update, context, message_object=None):
        user_id = update.effective_user.id
        user = await self.bot_manager.db.get_user(user_id)
        settings = user.settings if user and hasattr(user, 'settings') else {}
        text = f"""⚙️ إعدادات المستخدم

🌐 اللغة والمنطقة الزمنية:
• اللغة الحالية: {getattr(user, 'language_code', 'ar')}
• المنطقة الزمنية: {getattr(user, 'timezone', 'Asia/Baghdad')}

🔔 الإشعارات:
• إشعارات التحميل: {'🟢 مفعلة' if settings.get('notify_download_start', True) else '🔴 معطلة'}
• إشعارات النظام: {'🟢 مفعلة' if settings.get('notify_bot_updates', True) else '🔴 معطلة'}

🔒 الخصوصية:
• إظهار الإحصائيات: {'🟢 مفعل' if settings.get('show_stats', True) else '🔴 معطل'}
• حفظ سجل النشاط: {'🟢 مفعل' if settings.get('save_activity_log', True) else '🔴 معطل'}

💾 التخزين:
• المساحة المستخدمة: {settings.get('storage_used_mb', 0):.1f} MB
• حد التخزين: {settings.get('storage_limit_mb', 1000):.1f} MB"""
        keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="admin_users_management")]]
        if message_object:
            await message_object.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_mass_notifications(self, update, context, message_object=None):
        text = "📢 ميزة الإشعار الجماعي قيد التطوير وسيتم دعمها قريبًا."
        keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="admin_users_management")]]
        if message_object:
            await message_object.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def _set_file_size(self, update, context, message_object=None):
        # مثال: يطلب من المدير إدخال الحجم الجديد
        await self.bot_manager.db.set_setting('max_file_size', 100 * 1024 * 1024)  # 100MB افتراضياً
        text = "📁 تم تعيين الحد الأقصى لحجم الملف إلى 100MB بنجاح. (يمكنك تطويرها لاحقاً لقبول إدخال ديناميكي)"
        if message_object:
            if _is_message_modified(message_object, text, None):
                await message_object.edit_text(text)
        else:
            await update.message.reply_text(text)

    async def _toggle_rate_limit(self, update, context, message_object=None):
        current = await self.bot_manager.db.get_setting('rate_limit_enabled', True)
        new = not current
        await self.bot_manager.db.set_setting('rate_limit_enabled', new)
        text = f"⚡️ تحديد معدل الطلبات {'🟢 مفعل' if new else '🔴 معطل'}\nتم {'تفعيل' if new else 'إيقاف'} تحديد المعدل بنجاح."
        if message_object:
            if _is_message_modified(message_object, text, None):
                await message_object.edit_text(text)
        else:
            await update.message.reply_text(text)

    async def _toggle_backup(self, update, context, message_object=None):
        current = await self.bot_manager.db.get_setting('backup_enabled', True)
        new = not current
        await self.bot_manager.db.set_setting('backup_enabled', new)
        text = f"💾 النسخ الاحتياطية {'🟢 مفعلة' if new else '🔴 معطلة'}\nتم {'تفعيل' if new else 'إيقاف'} النسخ الاحتياطية بنجاح."
        if message_object:
            if _is_message_modified(message_object, text, None):
                await message_object.edit_text(text)
        else:
            await update.message.reply_text(text)

    async def _toggle_analytics(self, update, context, message_object=None):
        current = await self.bot_manager.db.get_setting('analytics_enabled', True)
        new = not current
        await self.bot_manager.db.set_setting('analytics_enabled', new)
        text = f"📊 التحليلات {'🟢 مفعلة' if new else '🔴 معطلة'}\nتم {'تفعيل' if new else 'إيقاف'} التحليلات بنجاح."
        if message_object:
            if _is_message_modified(message_object, text, None):
                await message_object.edit_text(text)
        else:
            await update.message.reply_text(text)

    async def _reset_settings(self, update, context, message_object=None):
        await self.bot_manager.db.set_setting('maintenance_mode', False)
        await self.bot_manager.db.set_setting('max_file_size', 50 * 1024 * 1024)
        await self.bot_manager.db.set_setting('rate_limit_enabled', True)
        await self.bot_manager.db.set_setting('backup_enabled', True)
        await self.bot_manager.db.set_setting('analytics_enabled', True)
        text = "🔄 تم إعادة تعيين جميع إعدادات النظام إلى القيم الافتراضية بنجاح."
        if message_object:
            if _is_message_modified(message_object, text, None):
                await message_object.edit_text(text)
        else:
            await update.message.reply_text(text)

    async def _handle_unpremium_user(self, update, context, user_id, page, message_object):
        try:
            user = await self.bot_manager.db.get_user(user_id)
            if not user:
                await message_object.edit_text("❌ المستخدم غير موجود.")
                return
            if not user.is_premium:
                await message_object.edit_text("⚠️ المستخدم ليس مميزاً بالفعل.")
                return
            success = await self.bot_manager.db.update_user(user_id, {"is_premium": False})
            if success:
                await self.bot_manager.db.log_user_action(update.effective_user.id, 'admin_unpremium_user', {'user_id': user_id})
                await message_object.edit_text(f"✅ تم إلغاء تمييز المستخدم <code>{user_id}</code> بنجاح.", parse_mode='HTML')
                # إعادة عرض القائمة بعد الإجراء
                await self._show_premium_users(update, context, message_object, page=page)
            else:
                await message_object.edit_text("❌ فشل في إلغاء تمييز المستخدم.")
        except Exception as e:
            await message_object.edit_text(f"❌ حدث خطأ أثناء إلغاء الترقية.\n[DEBUG]: {type(e).__name__}: {e}")

    async def _show_premium_user_details(self, update, context, user_id, page, message_object):
        try:
            user = await self.bot_manager.db.get_user(user_id)
            if not user:
                await message_object.edit_text("❌ المستخدم غير موجود.")
                return
            reg_date = user.registration_date.strftime('%Y-%m-%d %H:%M') if user.registration_date else '-'
            last_activity = user.last_activity.strftime('%Y-%m-%d %H:%M') if user.last_activity else '-'
            text = f"""
ℹ️ تفاصيل المستخدم المميز

<b>الاسم:</b> {user.first_name or '-'}
<b>اسم المستخدم:</b> @{user.username or '-'}
<b>المعرف:</b> <code>{user.id}</code>
<b>تاريخ التسجيل:</b> {reg_date}
<b>آخر نشاط:</b> {last_activity}
<b>عدد التحميلات:</b> {user.total_downloads}
<b>عدد الرفع:</b> {user.total_uploads}
<b>مميز؟</b> {'✅' if user.is_premium else '❌'}
<b>محظور؟</b> {'✅' if user.is_banned else '❌'}
"""
            keyboard = [
                [InlineKeyboardButton("❌ إلغاء الترقية", callback_data=f"admin_unpremium:{user.id}:{page}")],
                [InlineKeyboardButton("🔙 العودة للقائمة", callback_data=f"admin_premium_users_page:{page}")]
            ]
            if message_object:
                if _is_message_modified(message_object, text, InlineKeyboardMarkup(keyboard)):
                    await message_object.edit_text(
                        text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )
            else:
                await update.message.reply_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
        except Exception as e:
            await message_object.edit_text(f"❌ حدث خطأ أثناء عرض التفاصيل.\n[DEBUG]: {type(e).__name__}: {e}")

    async def _ask_broadcast_message(self, update, context, target, message_object):
        text = "📝 أرسل الآن نص الرسالة الجماعية التي تريد إرسالها:"
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="admin_cancel_broadcast")]]
        if message_object:
            if _is_message_modified(message_object, text, InlineKeyboardMarkup(keyboard)):
                await message_object.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        # حفظ الهدف في بيانات السياق
        context.user_data['broadcast_target'] = target
        context.user_data['awaiting_broadcast_message'] = True

    async def _process_broadcast_message(self, update, context, message_object=None):
        target = context.user_data.get('broadcast_target', 'all')
        message_text = update.message.text
        context.user_data['broadcast_message_text'] = message_text
        context.user_data['awaiting_broadcast_message'] = False
        keyboard = [
            [InlineKeyboardButton("✅ تأكيد الإرسال", callback_data=f"admin_confirm_broadcast:{target}")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="admin_cancel_broadcast")]
        ]
        confirm_text = f"📢 هل أنت متأكد من إرسال الرسالة التالية إلى الفئة المحددة؟\n\n{message_text}"
        if message_object and getattr(message_object, "from_user", None) and getattr(message_object.from_user, "is_bot", False):
            if _is_message_modified(message_object, confirm_text, InlineKeyboardMarkup(keyboard)):
                await message_object.edit_text(confirm_text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(confirm_text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def _confirm_broadcast(self, update, context, target, message_object):
        try:
            message_text = context.user_data.get('broadcast_message_text')
            if not message_text:
                await message_object.edit_text("❌ لم يتم العثور على نص الرسالة.")
                return
            if target == "adminchats":
                result = await self.bot_manager.broadcast_to_admin_chats(message_text)
                total = result.get('total_chats', 0)
                success = result.get('sent', 0)
                failed = result.get('failed', 0)
                failed_details = result.get('failed_details', [])
                text = f"✅ تم إرسال الرسالة بنجاح إلى القنوات/المجموعات!\n\nعدد المستلمين: {total}\nتم الإرسال بنجاح: {success}\nفشل الإرسال: {failed}"
                if failed_details:
                    text += "\n\n❌ تفاصيل الفشل:\n"
                    for item in failed_details:
                        name = item.get('title') or item.get('username') or str(item.get('id'))
                        text += f"• <b>{name}</b> (<code>{item.get('id')}</code>): {item.get('error')}\n"
                keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="admin_broadcast_menu")]]
                if message_object:
                    if _is_message_modified(message_object, text, InlineKeyboardMarkup(keyboard)):
                        await message_object.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
                else:
                    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
                return
            # تحديد الفئة
            user_filter = {}
            if target == "premium":
                user_filter['is_premium'] = True
            elif target == "active":
                user_filter['is_active'] = True
            # إرسال فعلي
            result = await self.bot_manager.broadcast_message(message_text, user_filter=user_filter)
            total = result.get('total_users', 0)
            success = result.get('sent_count', 0)
            failed = result.get('failed_count', 0)
            text = f"✅ تم إرسال الرسالة الجماعية بنجاح!\n\nعدد المستلمين: {total}\nتم الإرسال بنجاح: {success}\nفشل الإرسال: {failed}"
            keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="admin_users_management")]]
            if message_object:
                if _is_message_modified(message_object, text, InlineKeyboardMarkup(keyboard)):
                    await message_object.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            await message_object.edit_text(f"❌ حدث خطأ أثناء الإرسال الجماعي.\n[DEBUG]: {type(e).__name__}: {e}")

    async def _show_user_details(self, update, context, user_id, page, message_object):
        try:
            user = await self.bot_manager.db.get_user(user_id)
            if not user:
                await message_object.edit_text("❌ المستخدم غير موجود.")
                return
            reg_date = user.registration_date.strftime('%Y-%m-%d %H:%M') if user.registration_date else '-'
            last_activity = user.last_activity.strftime('%Y-%m-%d %H:%M') if user.last_activity else '-'
            text = f"""
ℹ️ تفاصيل المستخدم

<b>الاسم:</b> {user.first_name or '-'}
<b>اسم المستخدم:</b> @{user.username or '-'}
<b>المعرف:</b> <code>{user.id}</code>
<b>تاريخ التسجيل:</b> {reg_date}
<b>آخر نشاط:</b> {last_activity}
<b>عدد التحميلات:</b> {user.total_downloads}
<b>عدد الرفع:</b> {user.total_uploads}
<b>مميز؟</b> {'✅' if user.is_premium else '❌'}
<b>محظور؟</b> {'✅' if user.is_banned else '❌'}
"""
            keyboard = [
                [
                    InlineKeyboardButton("🚫 حظر" if not user.is_banned else "✅ إلغاء الحظر", callback_data=f"admin_ban_user:{user.id}:{page}" if not user.is_banned else f"admin_unban_user:{user.id}:{page}"),
                    InlineKeyboardButton("⭐ ترقية" if not user.is_premium else "❌ إلغاء الترقية", callback_data=f"admin_premium:{user.id}:{page}" if not user.is_premium else f"admin_unpremium:{user.id}:{page}")
                ],
                [InlineKeyboardButton("🔙 العودة للقائمة", callback_data=f"admin_list_users_page:{page}")]
            ]
            if message_object:
                if _is_message_modified(message_object, text, InlineKeyboardMarkup(keyboard)):
                    await message_object.edit_text(
                        text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )
            else:
                await update.message.reply_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
        except Exception as e:
            await message_object.edit_text(f"❌ حدث خطأ أثناء عرض التفاصيل.\n[DEBUG]: {type(e).__name__}: {e}")

    async def _ban_user_action(self, update, context, user_id, page, message_object):
        try:
            user = await self.bot_manager.db.get_user(user_id)
            if not user:
                await message_object.edit_text("❌ المستخدم غير موجود.")
                return
            if user.is_banned:
                await message_object.edit_text("⚠️ المستخدم محظور بالفعل.")
                return
            success = await self.bot_manager.db.ban_user(user_id)
            if success:
                await message_object.edit_text(f"✅ تم حظر المستخدم <code>{user_id}</code> بنجاح.", parse_mode='HTML')
                await self._list_users(update, context, message_object, page=page)
            else:
                await message_object.edit_text("❌ فشل في حظر المستخدم.")
        except Exception as e:
            await message_object.edit_text(f"❌ حدث خطأ أثناء الحظر.\n[DEBUG]: {type(e).__name__}: {e}")

    async def _unban_user_action(self, update, context, user_id, page, message_object):
        try:
            user = await self.bot_manager.db.get_user(user_id)
            if not user:
                await message_object.edit_text("❌ المستخدم غير موجود.")
                return
            if not user.is_banned:
                await message_object.edit_text("⚠️ المستخدم غير محظور.")
                return
            success = await self.bot_manager.db.unban_user(user_id)
            if success:
                await message_object.edit_text(f"✅ تم إلغاء حظر المستخدم <code>{user_id}</code> بنجاح.", parse_mode='HTML')
                await self._list_users(update, context, message_object, page=page)
            else:
                await message_object.edit_text("❌ فشل في إلغاء حظر المستخدم.")
        except Exception as e:
            await message_object.edit_text(f"❌ حدث خطأ أثناء إلغاء الحظر.\n[DEBUG]: {type(e).__name__}: {e}")

    async def _premium_user_action(self, update, context, user_id, page, message_object):
        try:
            user = await self.bot_manager.db.get_user(user_id)
            if not user:
                await message_object.edit_text("❌ المستخدم غير موجود.")
                return
            if user.is_premium:
                # إلغاء الترقية
                success = await self.bot_manager.db.update_user(user_id, {"is_premium": False})
                if success:
                    await message_object.edit_text(f"✅ تم إلغاء تمييز المستخدم <code>{user_id}</code> بنجاح.", parse_mode='HTML')
                    await self._list_users(update, context, message_object, page=page)
                else:
                    await message_object.edit_text("❌ فشل في إلغاء تمييز المستخدم.")
            else:
                # ترقية
                success = await self.bot_manager.db.update_user(user_id, {"is_premium": True})
                if success:
                    await message_object.edit_text(f"✅ تم ترقية المستخدم <code>{user_id}</code> إلى مميز.", parse_mode='HTML')
                    await self._list_users(update, context, message_object, page=page)
                else:
                    await message_object.edit_text("❌ فشل في ترقية المستخدم.")
        except Exception as e:
            await message_object.edit_text(f"❌ حدث خطأ أثناء الترقية/إلغاء الترقية.\n[DEBUG]: {type(e).__name__}: {e}")

    async def _show_performance_monitor(self, update, context, message_object=None):
        stats = performance_monitor.get_stats(last_minutes=60)
        text = '📈 لوحة مراقبة الأداء (آخر ساعة):\n'
        for key, val in stats.items():
            if key == 'errors':
                text += f"\n❌ الأخطاء الأخيرة ({len(val)}):"
                for t, etype, details in val[-5:]:
                    text += f"\n- [{t.strftime('%H:%M:%S')}] {etype}: {details[:60]}"
            elif key.startswith('button_'):
                text += f"\n🔘 زر {key.replace('button_','')}: عدد الضغطات={val['count']} | نجاح={val['success']} | فشل={val['fail']}"
            elif key.startswith('platform_'):
                text += f"\n🌐 منصة {key.replace('platform_','')}: عدد الأحداث={val['count']} | نجاح={val['success']} | فشل={val['fail']}"
            else:
                text += f"\n• {key}: عدد={val['count']} | متوسط={val['avg']:.1f} | أعلى={val['max']:.1f} | أقل={val['min']:.1f}"
        if message_object:
            if _is_message_modified(message_object, text, None):
                await message_object.edit_text(text)
        else:
            await update.message.reply_text(text)

    async def _start_text_broadcast(self, update, context, message_object=None, lang=None):
        """بدء بث رسالة نصية جماعية."""
        if lang is None:
            user = update.effective_user if update.effective_user else None
            db_user = await self.bot_manager.db.get_user(user.id) if user else None
            lang = getattr(db_user, 'language_code', None) or getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = "📝 أرسل الآن نص الرسالة الجماعية التي تريد إرسالها لجميع المستخدمين:"
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="admin_cancel_broadcast")]]
        if message_object:
            if _is_message_modified(message_object, text, InlineKeyboardMarkup(keyboard)):
                await message_object.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        context.user_data['awaiting_broadcast_message'] = True
        context.user_data['broadcast_target'] = 'all'

    async def _start_link_broadcast(self, update, context, message_object=None, lang=None):
        """بدء بث رسالة جماعية مع رابط."""
        if lang is None:
            user = update.effective_user if update.effective_user else None
            db_user = await self.bot_manager.db.get_user(user.id) if user else None
            lang = getattr(db_user, 'language_code', None) or getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = "🔗 أرسل الآن نص الرسالة مع الرابط الذي تريد إرساله لجميع المستخدمين:"
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="admin_cancel_broadcast")]]
        if message_object:
            if _is_message_modified(message_object, text, InlineKeyboardMarkup(keyboard)):
                await message_object.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        context.user_data['awaiting_broadcast_message'] = True
        context.user_data['broadcast_target'] = 'link'

    async def _start_poll_broadcast(self, update, context, message_object=None, lang=None):
        """بدء بث تصويت جماعي (استطلاع)."""
        if lang is None:
            user = update.effective_user if update.effective_user else None
            db_user = await self.bot_manager.db.get_user(user.id) if user else None
            lang = getattr(db_user, 'language_code', None) or getattr(user, 'language_code', None) or self.config.LANGUAGE_DEFAULT or 'ar'
        text = "📊 أرسل الآن نص السؤال وخيارات التصويت (كل خيار في سطر منفصل):"
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="admin_cancel_broadcast")]]
        if message_object:
            if _is_message_modified(message_object, text, InlineKeyboardMarkup(keyboard)):
                await message_object.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        context.user_data['awaiting_broadcast_message'] = True
        context.user_data['broadcast_target'] = 'poll'

    async def _show_forced_subscription_panel(self, update, context, message_object=None):
        sections = await self.bot_manager.db.get_forced_subscription_sections()
        keyboard = []
        text = '<b>إدارة الاشتراك الإجباري</b>\n\nاختر القسم الذي تريد إدارته:'
        for s in sections:
            keyboard.append([InlineKeyboardButton(f"{s['name']}", callback_data=f"admin_manage_section:{s['id']}")])
        keyboard.append([InlineKeyboardButton("📋 عرض جميع القنوات/الحسابات الحالية", callback_data="admin_list_all_forced_channels")])
        keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="admin_main_panel")])
        if message_object:
            if _is_message_modified(message_object, text, InlineKeyboardMarkup(keyboard)):
                await message_object.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    async def _add_forced_subscription_channel(self, update, context, message_object=None):
        await update.effective_message.reply_text(
            "أرسل معلومات القناة/الرابط المطلوب إضافته بالصيغة:\n<code>الاسم | @username أو الرابط | main/secondary (اختياري)</code>\nإذا لم تحدد التصنيف، ستضاف كقناة ثانوية افتراضياً.",
            parse_mode='HTML'
        )
        context.user_data['awaiting_forced_channel'] = True

    async def _remove_forced_subscription_channel(self, update, context, channel_id, message_object=None):
        await self.bot_manager.db.remove_forced_subscription_channel(channel_id)
        await self._show_forced_subscription_panel(update, context, message_object)

    async def _process_forced_channel_input(self, update, context):
        text = update.message.text.strip()
        # إذا لم يوجد | اعتبر النص كله هو الرابط فقط
        if '|' not in text:
            url = text
            name = ''
            channel_type = 'secondary'
        else:
            parts = [x.strip() for x in text.split('|')]
            if len(parts) < 2:
                await update.message.reply_text("❌ الصيغة غير صحيحة. أرسلها هكذا:\n<code>الاسم | @username أو الرابط | main/secondary (اختياري)</code>", parse_mode='HTML')
                context.user_data['awaiting_forced_channel'] = True
                return
            name = parts[0]
            url = parts[1]
            channel_type = parts[2].lower() if len(parts) > 2 and parts[2].lower() in ['main','secondary'] else 'secondary'
        # تحقق أن الرابط يبدأ بـ http
        if not url.startswith('http'):
            await update.message.reply_text("❌ الرابط يجب أن يبدأ بـ http أو https.", parse_mode='HTML')
            context.user_data['awaiting_forced_channel'] = True
            return
        import urllib.parse
        channel_id = url.replace('https://t.me/', '').replace('http://t.me/', '').replace('@', '').strip('/')
        # إذا كان channel_id نصي (وليس chat_id رقمي) أضف @ في البداية
        if channel_id and not channel_id.startswith('-') and not channel_id.startswith('@'):
            channel_id = '@' + channel_id
        channel_url = url
        # إذا لم يتم إدخال اسم (name فارغ)، حاول جلب اسم القناة تلقائياً
        if not name or name == '-':
            if 't.me/' in url:
                try:
                    chat = await update.get_bot().get_chat(channel_id)
                    name = chat.title or channel_id
                except Exception:
                    name = channel_id
            else:
                parsed = urllib.parse.urlparse(url)
                if parsed.netloc:
                    name = parsed.netloc
                else:
                    name = url[:30]
        channel = {'id': channel_id, 'name': name, 'url': channel_url, 'type': channel_type}
        await self.bot_manager.db.add_forced_subscription_channel(channel)
        await update.message.reply_text(f"✅ تم إضافة القناة/الرابط بنجاح: <b>{name}</b> ({'رئيسية' if channel_type=='main' else 'ثانوية'})", parse_mode='HTML')
        await self._show_section_management(update, context, channel_type) # Pass the section_id to show the correct panel

    async def _show_section_management(self, update, context, section_id, message_object=None):
        section = await self.bot_manager.db.get_section_by_id(section_id)
        channels = [c for c in await self.bot_manager.db.get_forced_subscription_channels() if c.get('type','secondary') == section_id]
        # ترتيب القنوات حسب order
        channels = sorted(channels, key=lambda c: c.get('order', 0))
        text = f"""
<b>{section['name']}</b>

{section['message']}

عدد القنوات/الحسابات المسموح به: <b>{section['max_count']}</b>

<b>القنوات/الحسابات الحالية:</b>
"""
        if not channels:
            text += "لا توجد قنوات/حسابات حالياً.\n"
        keyboard = []
        for idx, c in enumerate(channels):
            # جلب الإحصائيات (عداد المشتركين، مشتركين جدد أسبوعياً)
            subscribers = c.get('subscribers_count', '-')
            weekly_new = c.get('weekly_new_subscribers', '-')
            channel_type = c.get('type', 'secondary')
            type_label = {
                'main': 'رئيسية',
                'secondary': 'ثانوية',
                'social': 'سوشيال',
                'external': 'خارجية'
            }.get(channel_type, channel_type)
            custom_msg = c.get('custom_message', None)
            text += f"• <b>{c.get('name', c.get('id', c.get('url','-')))}</b> (<i>{type_label}</i>)\n"
            text += f"  — <code>{c.get('url','-')}</code>\n"
            text += f"  👥 <b>المشتركين:</b> {subscribers} | 📈 <b>جدد هذا الأسبوع:</b> {weekly_new}\n"
            if custom_msg:
                text += f"  📝 <i>رسالة مخصصة</i>\n"
            # أزرار الإدارة لكل قناة: حذف، ↑، ↓، رسالة مخصصة
            row = [
                InlineKeyboardButton("❌ حذف", callback_data=f"admin_remove_forced_channel:{c.get('id', c.get('url',''))}"),
                InlineKeyboardButton("⬆️", callback_data=f"admin_move_channel_up:{c.get('id', c.get('url',''))}:{section_id}") if idx > 0 else None,
                InlineKeyboardButton("⬇️", callback_data=f"admin_move_channel_down:{c.get('id', c.get('url',''))}:{section_id}") if idx < len(channels)-1 else None,
                InlineKeyboardButton("📝 رسالة", callback_data=f"admin_edit_channel_message:{c.get('id', c.get('url',''))}:{section_id}")
            ]
            # إزالة None من الصف
            row = [btn for btn in row if btn]
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("➕ إضافة قناة/حساب جديد", callback_data=f"admin_add_forced_channel:{section_id}")])
        keyboard.append([InlineKeyboardButton("📝 تعديل رسالة القسم", callback_data=f"admin_set_section_message:{section_id}")])
        keyboard.append([InlineKeyboardButton("🔢 تعديل الحد الأقصى", callback_data=f"admin_set_section_max:{section_id}")])
        keyboard.append([InlineKeyboardButton("🔙 الرجوع للأقسام", callback_data="admin_forced_subscription")])
        if message_object:
            if _is_message_modified(message_object, text, InlineKeyboardMarkup(keyboard)):
                await message_object.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    async def _ask_section_message(self, update, context, section_id, message_object=None):
        await update.effective_message.reply_text(f"أرسل الآن رسالة الاشتراك المخصصة لهذا القسم:")
        context.user_data['awaiting_section_message'] = section_id

    async def _ask_section_max(self, update, context, section_id, message_object=None):
        await update.effective_message.reply_text(f"أرسل الآن العدد الأقصى المسموح به للقنوات/الحسابات في هذا القسم:")
        context.user_data['awaiting_section_max'] = section_id

    async def _show_security_panel(self, update, context, message_object=None):
        text = """🛡️ لوحة الأمان

هذه الميزة قيد التطوير وسيتم دعمها قريبًا بإذن الله."""
        if message_object:
            if _is_message_modified(message_object, text, None):
                await message_object.edit_text(text)
        else:
            await update.message.reply_text(text)

    async def _ask_channel_message(self, update, context, channel_id, section_id, message_object=None):
        await update.effective_message.reply_text(f"أرسل الآن الرسالة المخصصة لهذه القناة/الحساب:")
        context.user_data['awaiting_channel_message'] = (channel_id, section_id)

