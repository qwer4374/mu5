#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bot Manager
===========

Central bot management class that handles core bot operations,
user management, and coordination between different components.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from telegram import Bot, User as TelegramUser, ChatMember
from telegram.error import TelegramError
from telegram.constants import ChatType
import shutil
import os

from .database import DatabaseManager, User

class BotManager:
    """Central bot manager for coordinating bot operations."""

    def __init__(self, application, config, db_manager):
        self.application = application
        self.bot = application.bot
        self.config = config
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        self._bot_info = None
        self.admin_handler = None  # Will be set after initialization
        self.user_handler = None  # Will be set after initialization
        # أزل جدولة المهام الدورية من هنا
        # سيتم استدعاؤها بعد بدء التطبيق

    def set_admin_handler(self, handler):
        self.admin_handler = handler

    def set_user_handler(self, handler):
        self.user_handler = handler

    async def get_bot_info(self) -> Dict[str, Any]:
        """Get bot information."""
        if not self._bot_info:
            try:
                bot_user = await self.bot.get_me()
                self._bot_info = {
                    'id': getattr(bot_user, 'id', 0),
                    'username': getattr(bot_user, 'username', ''),
                    'first_name': getattr(bot_user, 'first_name', ''),
                    'can_join_groups': getattr(bot_user, 'can_join_groups', False),
                    'can_read_all_group_messages': getattr(bot_user, 'can_read_all_group_messages', False),
                    'supports_inline_queries': getattr(bot_user, 'supports_inline_queries', False)
                }
            except Exception as e:
                self.logger.error(f"Failed to get bot info: {e}")
                self._bot_info = {}
        return self._bot_info if isinstance(self._bot_info, dict) else {}

    async def register_user(self, telegram_user: TelegramUser) -> User:
        """Register or update user in database."""
        try:
            # Check if user exists
            user = await self.db.get_user(telegram_user.id)

            user_data = {
                'username': telegram_user.username,
                'first_name': telegram_user.first_name,
                'last_name': telegram_user.last_name,
                'language_code': telegram_user.language_code or 'ar',
                'last_activity': datetime.utcnow()
            }

            is_new = False
            if user:
                # Update existing user
                await self.db.update_user(telegram_user.id, user_data)
                user = await self.db.get_user(telegram_user.id)
            else:
                # Create new user
                user_data['id'] = telegram_user.id
                user_data['registration_date'] = datetime.utcnow()
                user = await self.db.create_user(user_data)
                is_new = True

                # Log registration
                await self.db.log_user_action(
                    telegram_user.id,
                    'registration',
                    {'username': telegram_user.username}
                )

                self.logger.info(f"✅ New user registered: {telegram_user.id} (@{telegram_user.username})")

            # إشعار المالك عند دخول مستخدم جديد
            if is_new:
                from config import Config
                total_users = await self.db.get_all_users(active_only=False)
                total_users_count = len(total_users)
                first_name = user.first_name or "غير متوفر"
                last_name = user.last_name or ""
                username = f"@{user.username}" if user.username else "بدون معرف"
                user_id = user.id
                country = getattr(user, 'country', 'غير محددة')
                join_time = user.registration_date.strftime('%Y-%m-%d %H:%M') if getattr(user, 'registration_date', None) else datetime.now().strftime('%Y-%m-%d %H:%M')
                if user.username:
                    profile_link = f"https://t.me/{user.username}"
                else:
                    profile_link = f"https://t.me/user?id={user_id}"
                name_link = f'<a href="{profile_link}">{first_name} {last_name}</a>'
                notify_text = f"""
🚀 تم انضمام عضو جديد إلى البوت الخاص بك!

━━━━━━━━━━━━━━━
👤 معلومات العضو الجديد:

• الاسم: {name_link}
• المعرف: {username}
• الآيدي: <code>{user_id}</code>
• الدولة: {country}
• وقت الانضمام: {join_time}
━━━━━━━━━━━━━━━
👥 عدد الأعضاء الكلي الآن: <b>{total_users_count}</b>
━━━━━━━━━━━━━━━
✨ أهلاً وسهلاً به في عائلتنا الرقمية!
"""
                try:
                    await self.bot.send_message(Config.OWNER_ID, notify_text, parse_mode='HTML', disable_web_page_preview=True)
                except Exception as e:
                    self.logger.error(f"Failed to send new user notification: {e}")

            return user

        except Exception as e:
            self.logger.error(f"Failed to register user {telegram_user.id}: {e}")
            raise

    async def is_user_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        from config import Config
        return user_id in Config.ADMIN_USER_IDS or user_id == Config.OWNER_ID

    async def is_user_banned(self, user_id: int) -> bool:
        """Check if user is banned."""
        user = await self.db.get_user(user_id)
        return user.is_banned if user else False

    async def is_user_subscribed(self, user_id: int, channel_id: str) -> bool:
        try:
            member = await self.bot.get_chat_member(channel_id, user_id)
            return member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]
        except TelegramError as e:
            self.logger.warning(f"[SUBSCRIPTION] Could not verify subscription for channel {channel_id}: {e}")
            # أضف علامة خاصة في السياق أو أرجع False فقط
            return False

    async def check_user_subscription(self, user_id: int) -> List[Dict[str, str]]:
        """Check user subscription status for required channels (from DB)."""
        # جلب القنوات/الروابط من قاعدة البيانات
        required_channels = await self.db.get_forced_subscription_channels()
        if not required_channels:
            return []
        unsubscribed_channels = []
        for channel in required_channels:
            channel_id = channel.get('id', channel.get('username', ''))
            channel_name = channel.get('name', channel_id)
            channel_url = channel.get('url', f"https://t.me/{channel_id}")
            if not await self.is_user_subscribed(user_id, channel_id):
                unsubscribed_channels.append({
                    'id': channel_id,
                    'name': channel_name,
                    'url': channel_url
                })
        return unsubscribed_channels

    async def check_all_subscriptions(self, user_id: int, required_channels: List[str]) -> Dict[str, bool]:
        """Check user subscription status for all required channels."""
        subscription_status = {}

        for channel in required_channels:
            subscription_status[channel] = await self.is_user_subscribed(user_id, channel)

        return subscription_status

    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user statistics."""
        user = await self.db.get_user(user_id)
        if not user:
            return {}

        downloads = await self.db.get_user_downloads(user_id, limit=100)
        analytics = await self.db.get_user_analytics(user_id, days=30)

        # Calculate statistics
        total_downloads = len(downloads)
        successful_downloads = len([d for d in downloads if getattr(d, 'download_status', '') == 'completed'])
        failed_downloads = len([d for d in downloads if getattr(d, 'download_status', '') == 'failed'])
        total_size = sum([getattr(d, 'file_size', 0) or 0 for d in downloads if getattr(d, 'download_status', '') == 'completed'])

        # Activity statistics
        total_actions = len(analytics)
        action_types = {}
        for action in analytics:
            atype = getattr(action, 'action_type', '')
            if atype:
                action_types[atype] = action_types.get(atype, 0) + 1

        return {
            'user_info': {
                'id': getattr(user, 'id', 0),
                'username': getattr(user, 'username', ''),
                'first_name': getattr(user, 'first_name', ''),
                'registration_date': getattr(user, 'registration_date', None),
                'last_activity': getattr(user, 'last_activity', None),
                'is_premium': getattr(user, 'is_premium', False),
                'language': getattr(user, 'language_code', 'ar'),
                'timezone': getattr(user, 'timezone', 'Asia/Riyadh')
            },
            'download_stats': {
                'total_downloads': total_downloads,
                'successful_downloads': successful_downloads,
                'failed_downloads': failed_downloads,
                'success_rate': (successful_downloads / total_downloads * 100) if total_downloads > 0 else 0,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'storage_used_mb': round(getattr(user, 'storage_used', 0) / (1024 * 1024), 2)
            },
            'activity_stats': {
                'total_actions': total_actions,
                'action_breakdown': action_types,
                'avg_daily_actions': round(total_actions / 30, 2) if total_actions > 0 else 0
            }
        }

    async def send_message_safe(self, chat_id: int, text: str, **kwargs) -> bool:
        """Send message with error handling."""
        try:
            await self.bot.send_message(chat_id, text, **kwargs)
            return True
        except TelegramError as e:
            self.logger.error(f"Failed to send message to {chat_id}: {e}")
            return False

    async def send_document_safe(self, chat_id: int, document, **kwargs) -> bool:
        """Send document with error handling."""
        try:
            await self.bot.send_document(chat_id, document, **kwargs)
            return True
        except TelegramError as e:
            self.logger.error(f"Failed to send document to {chat_id}: {e}")
            return False

    async def broadcast_message(self, message: str, user_filter: Dict[str, Any] = None) -> Dict[str, int]:
        """Broadcast message to users with optional filtering."""
        users = await self.db.get_all_users(active_only=True)

        # Apply filters if provided
        if user_filter:
            filtered_users = []
            for user in users:
                include_user = True

                if 'is_premium' in user_filter and getattr(user, 'is_premium', False) != user_filter['is_premium']:
                    include_user = False

                if 'language_code' in user_filter and getattr(user, 'language_code', 'ar') != user_filter['language_code']:
                    include_user = False

                if 'min_downloads' in user_filter and getattr(user, 'total_downloads', 0) < user_filter['min_downloads']:
                    include_user = False

                if include_user:
                    filtered_users.append(user)

            users = filtered_users

        # Send messages
        sent_count = 0
        failed_count = 0

        for user in users:
            success = await self.send_message_safe(getattr(user, 'id', 0), message)
            if success:
                sent_count += 1
            else:
                failed_count += 1

        self.logger.info(f"📢 Broadcast completed: {sent_count} sent, {failed_count} failed")

        return {
            'total_users': len(users),
            'sent_count': sent_count,
            'failed_count': failed_count
        }

    async def get_chat_info(self, chat_id: str) -> Dict[str, Any]:
        """Get chat information."""
        if not chat_id:
            return {}
        try:
            chat = await self.bot.get_chat(chat_id)
            return {
                'id': getattr(chat, 'id', 0),
                'type': getattr(chat, 'type', ''),
                'title': getattr(chat, 'title', ''),
                'username': getattr(chat, 'username', ''),
                'description': getattr(chat, 'description', ''),
                'member_count': await self.bot.get_chat_member_count(chat_id) if getattr(chat, 'type', '') in ['group', 'supergroup', 'channel'] else 0
            }
        except Exception as e:
            self.logger.error(f"Failed to get chat info for {chat_id}: {e}")
            return {}

    async def update_user_activity(self, user_id: int, action_type: str, action_data: Dict = None):
        """Update user activity and log action."""
        # Update last activity
        await self.db.update_user(user_id, {'last_activity': datetime.utcnow()})

        # Log action for analytics
        await self.db.log_user_action(user_id, action_type, action_data)

    async def get_bot_statistics(self) -> Dict[str, Any]:
        """Get comprehensive bot statistics."""
        db_stats = await self.db.get_bot_statistics()
        bot_info = await self.get_bot_info()

        return {
            'bot_info': bot_info,
            'database_stats': db_stats,
            'uptime': self._calculate_uptime(),
            'version': '2.0.0'
        }

    def _calculate_uptime(self) -> str:
        """Calculate bot uptime (placeholder - would need start time tracking)."""
        # This would need to be implemented with actual start time tracking
        return "Running"

    async def maintenance_mode(self, enabled: bool, message: str = None):
        """Enable or disable maintenance mode."""
        await self.db.set_setting('maintenance_mode', enabled)
        if message:
            await self.db.set_setting('maintenance_message', message)

        self.logger.info(f"🔧 Maintenance mode {'enabled' if enabled else 'disabled'}")

    async def is_maintenance_mode(self) -> bool:
        """Check if maintenance mode is enabled."""
        return await self.db.get_setting('maintenance_mode', False)

    async def get_maintenance_message(self) -> str:
        """Get maintenance mode message."""
        msg = await self.db.get_setting(
            'maintenance_message',
            "🔧 البوت في وضع الصيانة حالياً. يرجى المحاولة لاحقاً."
        )
        return msg if isinstance(msg, str) else ""

    async def send_to_target_channels(self, text: str, document: str = None):
        """إرسال رسالة أو ملف إلى جميع القنوات/المجموعات المستهدفة."""
        for channel in getattr(self.config, 'TARGET_CHANNELS', []):
            try:
                if document:
                    await self.send_document_safe(getattr(channel, 'id', 0), document, caption=text)
                else:
                    await self.send_message_safe(getattr(channel, 'id', 0), text)
            except Exception as e:
                self.logger.error(f"Failed to send to channel/group {getattr(channel, 'id', 0)}: {e}")

    async def update_channels_stats(self):
        """تحديث عداد المشتركين والإحصائيات الأسبوعية لكل قناة اشتراك إجباري."""
        channels = await self.db.get_forced_subscription_channels()
        for channel in channels:
            channel_id = getattr(channel, 'id', getattr(channel, 'username', ''))
            info = await self.get_chat_info(channel_id)
            if info and getattr(info, 'member_count', None) is not None:
                prev_count = getattr(channel, 'subscribers_count', 0)
                new_count = info['member_count']
                weekly_new = new_count - prev_count
                channel['weekly_new_subscribers'] = weekly_new
                channel['subscribers_count'] = new_count
        await self.db.set_forced_subscription_channels(channels)

    async def schedule_channels_stats_update(self, interval_seconds: int = 604800):
        """جدولة تحديث إحصائيات القنوات أسبوعياً (افتراضي: كل أسبوع)."""
        from asyncio import create_task, sleep
        async def stats_loop():
            while True:
                try:
                    await self.update_channels_stats()
                except Exception as e:
                    self.logger.error(f"[StatsUpdate] {e}")
                await sleep(interval_seconds)
        create_task(stats_loop())

    async def start_background_tasks(self):
        import asyncio
        asyncio.create_task(self.schedule_channels_stats_update())
        asyncio.create_task(self.schedule_daily_backup())
        asyncio.create_task(self.schedule_weekly_pip_update())

    async def schedule_daily_backup(self):
        import asyncio
        while True:
            try:
                await self.create_database_backup()
            except Exception as e:
                self.logger.error(f"[AutoBackup] {e}")
            await asyncio.sleep(24 * 60 * 60)  # 24 ساعة

    async def create_database_backup(self):
        backup_dir = os.path.join("data", "backups")
        os.makedirs(backup_dir, exist_ok=True)
        db_path = os.path.abspath("advanced_telegram_bot.db")
        if not os.path.exists(db_path):
            self.logger.warning(f"[AutoBackup] Database file not found: {db_path}")
            return
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"backup_{now}.db")
        shutil.copy2(db_path, backup_path)
        self.logger.info(f"[AutoBackup] Database backup created: {backup_path}")

    async def schedule_weekly_pip_update(self):
        import asyncio
        while True:
            try:
                await self.update_python_packages()
            except Exception as e:
                self.logger.error(f"[AutoPipUpdate] {e}")
            await asyncio.sleep(7 * 24 * 60 * 60)  # أسبوع

    async def update_python_packages(self):
        import subprocess
        packages = ["python-telegram-bot", "sqlalchemy"]
        for pkg in packages:
            try:
                result = subprocess.run(["pip", "install", "--upgrade", pkg], capture_output=True, text=True)
                if result.returncode == 0:
                    self.logger.info(f"[AutoPipUpdate] Successfully updated {pkg}: {result.stdout}")
                else:
                    self.logger.warning(f"[AutoPipUpdate] Failed to update {pkg}: {result.stderr}")
            except Exception as e:
                self.logger.error(f"[AutoPipUpdate] Exception updating {pkg}: {e}")

    async def handle_my_chat_member(self, update, context):
        chat = update.effective_chat
        member = update.my_chat_member
        if member and member.new_chat_member.status in ['administrator', 'creator']:
            await self.db.add_admin_chat(chat.id, chat.type, getattr(chat, 'title', None), getattr(chat, 'username', None))
        elif member and member.new_chat_member.status in ['left', 'kicked']:
            await self.db.remove_admin_chat(chat.id)

    async def broadcast_to_admin_chats(self, message: str) -> dict:
        chats = await self.db.get_all_admin_chats()
        sent, failed = 0, 0
        failed_details = []
        for chat in chats:
            try:
                await self.send_message_safe(chat.id, message)
                sent += 1
            except Exception as e:
                self.logger.error(f"Failed to send to admin chat {chat.id}: {e}")
                failed += 1
                failed_details.append({
                    'id': chat.id,
                    'title': getattr(chat, 'title', ''),
                    'username': getattr(chat, 'username', ''),
                    'type': getattr(chat, 'type', ''),
                    'error': str(e)
                })
        return {'total_chats': len(chats), 'sent': sent, 'failed': failed, 'failed_details': failed_details}

