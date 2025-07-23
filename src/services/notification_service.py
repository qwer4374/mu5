#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Advanced Notification Service
==============================

Comprehensive notification system with smart scheduling, personalization,
and multi-channel delivery capabilities.
"""

import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import pytz

class NotificationType(Enum):
    """Notification types."""
    DOWNLOAD_START = "download_start"
    DOWNLOAD_COMPLETE = "download_complete"
    DOWNLOAD_FAILED = "download_failed"
    SYSTEM_UPDATE = "system_update"
    ADMIN_MESSAGE = "admin_message"
    SECURITY_ALERT = "security_alert"
    MAINTENANCE = "maintenance"
    REMINDER = "reminder"
    ACHIEVEMENT = "achievement"
    RECOMMENDATION = "recommendation"

class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

class NotificationChannel(Enum):
    """Notification delivery channels."""
    TELEGRAM = "telegram"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"

class AdvancedNotificationService:
    """Advanced notification service with intelligent delivery."""

    def __init__(self, bot_manager, db_manager, config):
        """Initialize notification service."""
        self.bot_manager = bot_manager
        self.db = db_manager
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Notification queue
        self.notification_queue = asyncio.Queue()
        self.processing_task = None

        # Notification templates
        self.templates = self._load_notification_templates()

        # Rate limiting
        self.rate_limits = {
            NotificationPriority.LOW: 10,      # 10 per hour
            NotificationPriority.MEDIUM: 20,   # 20 per hour
            NotificationPriority.HIGH: 50,     # 50 per hour
            NotificationPriority.URGENT: 100   # 100 per hour
        }

        # User notification history for rate limiting
        self.user_notification_history = {}

    async def start_service(self):
        """Start the notification service."""
        self.processing_task = asyncio.create_task(self._process_notification_queue())
        self.logger.info("Notification service started")

    async def stop_service(self):
        """Stop the notification service."""
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Notification service stopped")

    async def send_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        data: Dict[str, Any],
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        channels: List[NotificationChannel] = None,
        scheduled_time: Optional[datetime] = None,
        personalize: bool = True
    ) -> bool:
        """Send a notification to a user."""
        try:
            # Default to Telegram if no channels specified
            if channels is None:
                channels = [NotificationChannel.TELEGRAM]

            # Check if user wants to receive this type of notification
            if not await self._should_send_notification(user_id, notification_type, priority):
                self.logger.debug(f"Notification blocked for user {user_id}: {notification_type}")
                return False

            # Create notification object
            notification = {
                'id': f"{user_id}_{notification_type.value}_{datetime.now().timestamp()}",
                'user_id': user_id,
                'type': notification_type,
                'data': data,
                'priority': priority,
                'channels': channels,
                'scheduled_time': scheduled_time or datetime.now(),
                'personalize': personalize,
                'created_at': datetime.now(),
                'attempts': 0,
                'max_attempts': 3
            }

            # Add to queue
            await self.notification_queue.put(notification)

            # Log notification creation
            await self.db.log_notification(
                user_id=user_id,
                notification_type=notification_type.value,
                data=data,
                status='queued'
            )

            return True

        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")
            return False

    async def send_bulk_notification(
        self,
        user_ids: List[int],
        notification_type: NotificationType,
        data: Dict[str, Any],
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        channels: List[NotificationChannel] = None,
        batch_size: int = 100
    ) -> Dict[str, int]:
        """Send bulk notifications to multiple users."""
        results = {'sent': 0, 'failed': 0, 'skipped': 0}

        # Process in batches
        for i in range(0, len(user_ids), batch_size):
            batch = user_ids[i:i + batch_size]

            # Send notifications for this batch
            tasks = []
            for user_id in batch:
                task = self.send_notification(
                    user_id=user_id,
                    notification_type=notification_type,
                    data=data,
                    priority=priority,
                    channels=channels
                )
                tasks.append(task)

            # Wait for batch completion
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count results
            for result in batch_results:
                if isinstance(result, Exception):
                    results['failed'] += 1
                elif result:
                    results['sent'] += 1
                else:
                    results['skipped'] += 1

            # Small delay between batches to avoid overwhelming
            await asyncio.sleep(0.1)

        self.logger.info(f"Bulk notification completed: {results}")
        return results

    async def schedule_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        data: Dict[str, Any],
        scheduled_time: datetime,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        channels: List[NotificationChannel] = None
    ) -> str:
        """Schedule a notification for future delivery."""
        notification_id = f"scheduled_{user_id}_{notification_type.value}_{scheduled_time.timestamp()}"

        # Store scheduled notification in database
        await self.db.store_scheduled_notification(
            notification_id=notification_id,
            user_id=user_id,
            notification_type=notification_type.value,
            data=data,
            scheduled_time=scheduled_time,
            priority=priority.value,
            channels=[c.value for c in (channels or [NotificationChannel.TELEGRAM])]
        )

        self.logger.info(f"Notification scheduled: {notification_id} for {scheduled_time}")
        return notification_id

    async def cancel_scheduled_notification(self, notification_id: str) -> bool:
        """Cancel a scheduled notification."""
        try:
            success = await self.db.cancel_scheduled_notification(notification_id)
            if success:
                self.logger.info(f"Scheduled notification cancelled: {notification_id}")
            return success
        except Exception as e:
            self.logger.error(f"Error cancelling scheduled notification: {e}")
            return False

    async def send_achievement_notification(self, user_id: int, achievement: Dict[str, Any]):
        """Send achievement notification with special formatting."""
        data = {
            'achievement_name': achievement.get('name', 'إنجاز جديد'),
            'achievement_description': achievement.get('description', ''),
            'achievement_icon': achievement.get('icon', '🏆'),
            'points_earned': achievement.get('points', 0),
            'level_up': achievement.get('level_up', False)
        }

        await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.ACHIEVEMENT,
            data=data,
            priority=NotificationPriority.HIGH,
            personalize=True
        )

    async def send_download_progress_notification(
        self,
        user_id: int,
        download_id: str,
        progress: float,
        filename: str
    ):
        """Send download progress notification."""
        # Only send progress notifications at certain intervals
        if progress % 25 != 0 and progress != 100:  # 25%, 50%, 75%, 100%
            return

        data = {
            'download_id': download_id,
            'filename': filename,
            'progress': progress,
            'is_complete': progress >= 100
        }

        notification_type = (NotificationType.DOWNLOAD_COMPLETE
                           if progress >= 100
                           else NotificationType.DOWNLOAD_START)

        await self.send_notification(
            user_id=user_id,
            notification_type=notification_type,
            data=data,
            priority=NotificationPriority.MEDIUM
        )

    async def send_security_alert(
        self,
        user_id: int,
        alert_type: str,
        details: Dict[str, Any],
        immediate: bool = True
    ):
        """Send security alert notification."""
        data = {
            'alert_type': alert_type,
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'action_required': details.get('action_required', False)
        }

        priority = NotificationPriority.URGENT if immediate else NotificationPriority.HIGH

        await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.SECURITY_ALERT,
            data=data,
            priority=priority,
            channels=[NotificationChannel.TELEGRAM]  # Security alerts only via Telegram
        )

    async def send_maintenance_notification(
        self,
        user_ids: List[int],
        maintenance_info: Dict[str, Any],
        advance_notice_hours: int = 24
    ):
        """Send maintenance notification to users."""
        # Send immediate notification
        await self.send_bulk_notification(
            user_ids=user_ids,
            notification_type=NotificationType.MAINTENANCE,
            data=maintenance_info,
            priority=NotificationPriority.HIGH
        )

        # Schedule reminder notification
        if advance_notice_hours > 1:
            reminder_time = datetime.now() + timedelta(hours=advance_notice_hours - 1)

            for user_id in user_ids:
                await self.schedule_notification(
                    user_id=user_id,
                    notification_type=NotificationType.REMINDER,
                    data={
                        'reminder_type': 'maintenance',
                        'maintenance_info': maintenance_info
                    },
                    scheduled_time=reminder_time,
                    priority=NotificationPriority.MEDIUM
                )

    async def send_backup_notification(self, user_id: int, backup_file: str, success: bool):
        """إرسال إشعار عند اكتمال النسخ الاحتياطي التلقائي."""
        from .notification_service import NotificationType
        data = {
            'backup_file': backup_file,
            'status': 'نجاح' if success else 'فشل'
        }
        await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.SYSTEM_UPDATE,
            data=data,
            priority=self.NotificationPriority.HIGH
        )

    async def _process_notification_queue(self):
        """Process notifications from the queue."""
        while True:
            try:
                # Get notification from queue
                notification = await self.notification_queue.get()

                # Check if it's time to send
                if notification['scheduled_time'] > datetime.now():
                    # Put back in queue for later
                    await asyncio.sleep(1)
                    await self.notification_queue.put(notification)
                    continue

                # Process the notification
                success = await self._deliver_notification(notification)

                if not success and notification['attempts'] < notification['max_attempts']:
                    # Retry failed notification
                    notification['attempts'] += 1
                    await asyncio.sleep(5)  # Wait before retry
                    await self.notification_queue.put(notification)

                # Mark task as done
                self.notification_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error processing notification queue: {e}")
                await asyncio.sleep(1)

    async def _deliver_notification(self, notification: Dict[str, Any]) -> bool:
        """Deliver a notification through specified channels."""
        user_id = notification['user_id']
        notification_type = notification['type']
        data = notification['data']
        channels = notification['channels']

        success = True

        for channel in channels:
            try:
                if channel == NotificationChannel.TELEGRAM:
                    await self._send_telegram_notification(user_id, notification_type, data, notification['personalize'])
                elif channel == NotificationChannel.EMAIL:
                    await self._send_email_notification(user_id, notification_type, data)
                elif channel == NotificationChannel.SMS:
                    await self._send_sms_notification(user_id, notification_type, data)
                elif channel == NotificationChannel.PUSH:
                    await self._send_push_notification(user_id, notification_type, data)

            except Exception as e:
                self.logger.error(f"Error delivering notification via {channel}: {e}")
                success = False

        # Log delivery attempt
        await self.db.log_notification(
            user_id=user_id,
            notification_type=notification_type.value,
            data=data,
            status='delivered' if success else 'failed'
        )

        return success

    async def _send_telegram_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        data: Dict[str, Any],
        personalize: bool = True
    ):
        """Send notification via Telegram."""
        # Get user preferences
        user = await self.db.get_user(user_id)
        if not user:
            raise Exception(f"User {user_id} not found")

        # Generate message content
        message = await self._generate_notification_message(
            notification_type, data, user, personalize
        )

        # Add inline keyboard if applicable
        keyboard = self._generate_notification_keyboard(notification_type, data)

        # Send message
        await self.bot_manager.send_message_safe(
            user_id=user_id,
            text=message,
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    async def _send_email_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        data: Dict[str, Any]
    ):
        """Send notification via email (placeholder)."""
        # This would implement email sending
        self.logger.info(f"Email notification sent to user {user_id}: {notification_type}")

    async def _send_sms_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        data: Dict[str, Any]
    ):
        """Send notification via SMS (placeholder)."""
        # This would implement SMS sending
        self.logger.info(f"SMS notification sent to user {user_id}: {notification_type}")

    async def _send_push_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        data: Dict[str, Any]
    ):
        """Send push notification (placeholder)."""
        # This would implement push notification sending
        self.logger.info(f"Push notification sent to user {user_id}: {notification_type}")

    async def _generate_notification_message(
        self,
        notification_type: NotificationType,
        data: Dict[str, Any],
        user: Any,
        personalize: bool = True
    ) -> str:
        """Generate notification message content."""
        template = self.templates.get(notification_type.value, {})

        # Get base message
        message = template.get('message', 'إشعار جديد')

        # Personalize if requested
        if personalize and user:
            greeting = f"مرحباً {user.first_name}،\n\n"
            message = greeting + message

        # Replace placeholders with actual data
        for key, value in data.items():
            placeholder = f"{{{key}}}"
            if placeholder in message:
                message = message.replace(placeholder, str(value))

        # Add emoji if specified in template
        emoji = template.get('emoji', '')
        if emoji:
            message = f"{emoji} {message}"

        return message

    def _generate_notification_keyboard(
        self,
        notification_type: NotificationType,
        data: Dict[str, Any]
    ) -> Optional[Any]:
        """Generate inline keyboard for notification."""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        keyboard_config = self.templates.get(notification_type.value, {}).get('keyboard')

        if not keyboard_config:
            return None

        keyboard = []

        for row in keyboard_config:
            button_row = []
            for button in row:
                text = button['text']
                callback_data = button['callback_data']

                # Replace placeholders in callback data
                for key, value in data.items():
                    callback_data = callback_data.replace(f"{{{key}}}", str(value))

                button_row.append(InlineKeyboardButton(text, callback_data=callback_data))

            keyboard.append(button_row)

        return InlineKeyboardMarkup(keyboard) if keyboard else None

    async def _should_send_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        priority: NotificationPriority
    ) -> bool:
        """Check if notification should be sent based on user preferences and rate limits."""
        try:
            # Get user notification preferences
            user = await self.db.get_user(user_id)
            if not user or not user.is_active:
                return False

            # Check if user has disabled this type of notification
            user_settings = user.settings or {}
            notification_settings = user_settings.get('notifications', {})

            if not notification_settings.get(notification_type.value, True):
                return False

            # Check quiet hours
            if await self._is_quiet_hours(user_id):
                # Only allow urgent notifications during quiet hours
                if priority != NotificationPriority.URGENT:
                    return False

            # Check rate limits
            if not await self._check_rate_limit(user_id, priority):
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error checking notification permissions: {e}")
            return False

    async def _is_quiet_hours(self, user_id: int) -> bool:
        """Check if current time is within user's quiet hours."""
        try:
            user = await self.db.get_user(user_id)
            if not user:
                return False

            user_settings = user.settings or {}
            quiet_hours = user_settings.get('quiet_hours')

            if not quiet_hours:
                return False

            # Get user timezone
            user_tz = pytz.timezone(user.timezone or 'UTC')
            current_time = datetime.now(user_tz).time()

            # Parse quiet hours (format: "22:00-08:00")
            start_str, end_str = quiet_hours.split('-')
            start_time = datetime.strptime(start_str, '%H:%M').time()
            end_time = datetime.strptime(end_str, '%H:%M').time()

            # Check if current time is within quiet hours
            if start_time <= end_time:
                return start_time <= current_time <= end_time
            else:  # Quiet hours span midnight
                return current_time >= start_time or current_time <= end_time

        except Exception as e:
            self.logger.error(f"Error checking quiet hours: {e}")
            return False

    async def _check_rate_limit(self, user_id: int, priority: NotificationPriority) -> bool:
        """Check if user has exceeded rate limit for this priority level."""
        try:
            current_time = datetime.now()
            hour_ago = current_time - timedelta(hours=1)

            # Get user's notification history for the last hour
            if user_id not in self.user_notification_history:
                self.user_notification_history[user_id] = []

            # Clean old entries
            self.user_notification_history[user_id] = [
                timestamp for timestamp in self.user_notification_history[user_id]
                if timestamp > hour_ago
            ]

            # Check rate limit
            current_count = len(self.user_notification_history[user_id])
            limit = self.rate_limits.get(priority, 20)

            if current_count >= limit:
                return False

            # Add current notification to history
            self.user_notification_history[user_id].append(current_time)
            return True

        except Exception as e:
            self.logger.error(f"Error checking rate limit: {e}")
            return True  # Allow notification if check fails

    def _load_notification_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load notification templates."""
        return {
            'download_start': {
                'message': 'بدأ تحميل الملف: {filename}\nالحجم: {file_size_mb} MB',
                'emoji': '📥'
            },
            'download_complete': {
                'message': 'تم تحميل الملف بنجاح! 🎉\n\n📁 اسم الملف: {filename}\n📊 الحجم: {file_size_mb} MB\n⏱️ مدة التحميل: {duration} ثانية',
                'emoji': '✅',
                'keyboard': [
                    [
                        {'text': '📊 عرض التفاصيل', 'callback_data': 'download_details_{download_id}'},
                        {'text': '📥 تحميل آخر', 'callback_data': 'new_download'}
                    ]
                ]
            },
            'download_failed': {
                'message': 'فشل في تحميل الملف: {filename}\nالسبب: {error_message}',
                'emoji': '❌',
                'keyboard': [
                    [
                        {'text': '🔄 إعادة المحاولة', 'callback_data': 'retry_download_{download_id}'},
                        {'text': '❓ المساعدة', 'callback_data': 'download_help'}
                    ]
                ]
            },
            'achievement': {
                'message': 'تهانينا! لقد حصلت على إنجاز جديد:\n\n{achievement_icon} {achievement_name}\n{achievement_description}\n\n🏆 النقاط المكتسبة: {points_earned}',
                'emoji': '🎉'
            },
            'security_alert': {
                'message': '🚨 تنبيه أمني\n\nنوع التنبيه: {alert_type}\nالتفاصيل: {details}\n\nيرجى اتخاذ الإجراء المناسب فوراً.',
                'emoji': '🚨'
            },
            'maintenance': {
                'message': '🔧 إشعار صيانة\n\nسيتم إجراء صيانة للنظام:\n📅 التاريخ: {maintenance_date}\n⏰ الوقت: {maintenance_time}\n⏱️ المدة المتوقعة: {duration}\n\nنعتذر عن أي إزعاج.',
                'emoji': '🔧'
            },
            'system_update': {
                'message': '🆕 تحديث النظام\n\nتم إصدار تحديث جديد للبوت:\n📋 الإصدار: {version}\n✨ الميزات الجديدة:\n{features}\n\nالتحديث متاح الآن!',
                'emoji': '🆕'
            },
            'admin_message': {
                'message': '📢 رسالة من الإدارة\n\n{message_content}',
                'emoji': '📢'
            },
            'reminder': {
                'message': '⏰ تذكير\n\n{reminder_content}',
                'emoji': '⏰'
            },
            'recommendation': {
                'message': '💡 توصية شخصية\n\n{recommendation_title}\n{recommendation_description}',
                'emoji': '💡',
                'keyboard': [
                    [
                        {'text': '✅ تطبيق التوصية', 'callback_data': 'apply_recommendation_{recommendation_id}'},
                        {'text': '❌ تجاهل', 'callback_data': 'dismiss_recommendation_{recommendation_id}'}
                    ]
                ]
            }
        }

