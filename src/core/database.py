#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Database Manager
===============

Advanced database management with SQLAlchemy ORM, connection pooling,
and comprehensive data models for the Telegram bot.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Boolean,
    Text, BigInteger, Float, JSON, ForeignKey, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import StaticPool
import json

Base = declarative_base()

class User(Base):
    """User model for storing user information."""
    __tablename__ = 'users'

    id = Column(BigInteger, primary_key=True)  # Telegram user ID
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language_code = Column(String(10), default='ar')
    timezone = Column(String(50), default='Asia/Riyadh')
    is_active = Column(Boolean, default=True)
    is_banned = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    registration_date = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    total_downloads = Column(Integer, default=0)
    total_uploads = Column(Integer, default=0)
    storage_used = Column(BigInteger, default=0)  # in bytes
    settings = Column(JSON, default=dict)

    # Relationships
    downloads = relationship("Download", back_populates="user")
    analytics = relationship("UserAnalytics", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")

    # Indexes
    __table_args__ = (
        Index('idx_user_username', 'username'),
        Index('idx_user_active', 'is_active'),
        Index('idx_user_registration', 'registration_date'),
    )

class Download(Base):
    """Download model for tracking file downloads."""
    __tablename__ = 'downloads'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    url = Column(Text, nullable=False)
    filename = Column(String(500), nullable=True)
    file_size = Column(BigInteger, nullable=True)
    file_type = Column(String(50), nullable=True)
    download_status = Column(String(20), default='pending')  # pending, downloading, completed, failed
    download_progress = Column(Float, default=0.0)
    download_speed = Column(Float, nullable=True)  # bytes per second
    start_time = Column(DateTime, default=datetime.utcnow)
    completion_time = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    file_path = Column(String(1000), nullable=True)
    extra_data = Column(JSON, default=dict)

    # Relationships
    user = relationship("User", back_populates="downloads")

    # Indexes
    __table_args__ = (
        Index('idx_download_user', 'user_id'),
        Index('idx_download_status', 'download_status'),
        Index('idx_download_date', 'start_time'),
    )

class UserAnalytics(Base):
    """User analytics model for tracking usage patterns."""
    __tablename__ = 'user_analytics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    action_type = Column(String(50), nullable=False)  # command, download, upload, etc.
    action_data = Column(JSON, default=dict)
    session_duration = Column(Integer, nullable=True)  # in seconds
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="analytics")

    # Indexes
    __table_args__ = (
        Index('idx_analytics_user', 'user_id'),
        Index('idx_analytics_date', 'date'),
        Index('idx_analytics_action', 'action_type'),
    )

class Subscription(Base):
    """Subscription model for forced subscription feature."""
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    channel_id = Column(String(100), nullable=False)
    channel_name = Column(String(255), nullable=True)
    subscription_date = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    last_check = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="subscriptions")

    # Indexes
    __table_args__ = (
        Index('idx_subscription_user', 'user_id'),
        Index('idx_subscription_channel', 'channel_id'),
        Index('idx_subscription_active', 'is_active'),
    )

class ScheduledTask(Base):
    """Scheduled task model for automation."""
    __tablename__ = 'scheduled_tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    task_name = Column(String(255), nullable=False)
    task_type = Column(String(50), nullable=False)  # download, backup, notification, etc.
    task_data = Column(JSON, default=dict)
    schedule_expression = Column(String(100), nullable=False)  # cron expression
    next_run = Column(DateTime, nullable=False)
    last_run = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_date = Column(DateTime, default=datetime.utcnow)
    run_count = Column(Integer, default=0)
    max_runs = Column(Integer, nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_task_user', 'user_id'),
        Index('idx_task_next_run', 'next_run'),
        Index('idx_task_active', 'is_active'),
    )

class BotSettings(Base):
    """Bot settings model for configuration storage."""
    __tablename__ = 'bot_settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_settings_key', 'key'),
    )

class FileCache(Base):
    """File cache model for storing file metadata."""
    __tablename__ = 'file_cache'

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_hash = Column(String(64), unique=True, nullable=False)  # SHA256 hash
    original_url = Column(Text, nullable=True)
    filename = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_type = Column(String(50), nullable=False)
    file_path = Column(String(1000), nullable=False)
    access_count = Column(Integer, default=0)
    created_date = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    extra_info = Column(JSON, default=dict)

    # Indexes
    __table_args__ = (
        Index('idx_cache_hash', 'file_hash'),
        Index('idx_cache_expires', 'expires_at'),
        Index('idx_cache_accessed', 'last_accessed'),
    )

class ForcedSubscriptionChannel(Base):
    __tablename__ = 'forced_subscription_channels'
    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(String(255), nullable=False, unique=True)  # @username أو رابط أو معرف خارجي
    name = Column(String(255), nullable=False)
    url = Column(String(1000), nullable=False)
    type = Column(String(50), nullable=False, default='telegram_secondary')  # telegram_main, telegram_secondary, social, external
    order = Column(Integer, default=0)
    custom_message = Column(Text, nullable=True)
    subscribers_count = Column(Integer, default=0)
    weekly_new_subscribers = Column(Integer, default=0)
    added_date = Column(DateTime, default=datetime.utcnow)
    section = Column(String(50), default='secondary')  # main, secondary, accounts

    # Indexes
    __table_args__ = (
        Index('idx_forced_channel_type', 'type'),
        Index('idx_forced_channel_order', 'order'),
        Index('idx_forced_channel_section', 'section'),
    )

class UserChannelSubscription(Base):
    __tablename__ = 'user_channel_subscription'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    channel_id = Column(String(255), nullable=False)
    status = Column(String(20), default='pending')  # pending, verified, rejected
    last_check = Column(DateTime, default=datetime.utcnow)
    # Indexes
    __table_args__ = (
        Index('idx_user_channel', 'user_id', 'channel_id'),
        Index('idx_channel_status', 'channel_id', 'status'),
    )

class BotAdminChat(Base):
    __tablename__ = 'bot_admin_chats'
    id = Column(BigInteger, primary_key=True)  # chat_id
    type = Column(String(20), nullable=False)  # group, supergroup, channel
    title = Column(String(255), nullable=True)
    username = Column(String(255), nullable=True)
    date_added = Column(DateTime, default=datetime.utcnow)

class DatabaseManager:
    """Advanced database manager with connection pooling and ORM."""

    def __init__(self, database_url: str):
        """Initialize database manager."""
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialize database connection and create tables."""
        try:
            # Create engine with connection pooling
            if self.database_url.startswith('sqlite'):
                self.engine = create_engine(
                    self.database_url,
                    poolclass=StaticPool,
                    connect_args={
                        "check_same_thread": False,
                        "timeout": 30
                    },
                    echo=False
                )
            else:
                self.engine = create_engine(
                    self.database_url,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True,
                    echo=False
                )

            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )

            # Create all tables
            Base.metadata.create_all(bind=self.engine)

            # Initialize default settings
            await self._initialize_default_settings()

            self.logger.info("✅ Database initialized successfully")

        except Exception as e:
            self.logger.error(f"❌ Failed to initialize database: {e}")
            raise

    async def _initialize_default_settings(self):
        """Initialize default bot settings."""
        default_settings = {
            'bot_version': '2.0.0',
            'maintenance_mode': False,
            'max_file_size': 50 * 1024 * 1024,  # 50MB
            'allowed_file_types': ['mp4', 'mp3', 'pdf', 'jpg', 'png', 'gif'],
            'rate_limit_enabled': True,
            'backup_enabled': True,
            'analytics_enabled': True
        }

        with self.get_session() as session:
            for key, value in default_settings.items():
                existing = session.query(BotSettings).filter_by(key=key).first()
                if not existing:
                    setting = BotSettings(key=key, value=value)
                    session.add(setting)
            session.commit()

    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()

    async def close(self):
        """Close database connections."""
        if self.engine:
            self.engine.dispose()
            self.logger.info("✅ Database connections closed")

    # User management methods
    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        with self.get_session() as session:
            return session.query(User).filter_by(id=user_id).first()

    async def create_user(self, user_data: Dict[str, Any]) -> User:
        """Create new user."""
        with self.get_session() as session:
            user = User(**user_data)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    async def update_user(self, user_id: int, update_data: Dict[str, Any]) -> bool:
        """Update user information."""
        with self.get_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                for key, value in update_data.items():
                    setattr(user, key, value)
                user.last_activity = datetime.utcnow()
                session.commit()
                return True
            return False

    async def get_all_users(self, active_only: bool = True) -> List[User]:
        """Get all users."""
        with self.get_session() as session:
            query = session.query(User)
            if active_only:
                query = query.filter_by(is_active=True)
            return query.all()

    async def ban_user(self, user_id: int) -> bool:
        """Ban user."""
        return await self.update_user(user_id, {'is_banned': True, 'is_active': False})

    async def unban_user(self, user_id: int) -> bool:
        """Unban user."""
        return await self.update_user(user_id, {'is_banned': False, 'is_active': True})

    # Download management methods
    async def create_download(self, download_data: Dict[str, Any]) -> Download:
        """Create new download record."""
        with self.get_session() as session:
            download = Download(**download_data)
            session.add(download)
            session.commit()
            session.refresh(download)
            return download

    async def update_download(self, download_id: int, update_data: Dict[str, Any]) -> bool:
        """Update download record."""
        with self.get_session() as session:
            download = session.query(Download).filter_by(id=download_id).first()
            if download:
                for key, value in update_data.items():
                    setattr(download, key, value)
                session.commit()
                return True
            return False

    async def get_user_downloads(self, user_id: int, limit: int = 50) -> List[Download]:
        """Get user downloads."""
        with self.get_session() as session:
            return (session.query(Download)
                   .filter_by(user_id=user_id)
                   .order_by(Download.start_time.desc())
                   .limit(limit)
                   .all())

    # Analytics methods
    async def log_user_action(self, user_id: int, action_type: str, action_data: Dict = None):
        """Log user action for analytics."""
        with self.get_session() as session:
            analytics = UserAnalytics(
                user_id=user_id,
                action_type=action_type,
                action_data=action_data or {}
            )
            session.add(analytics)
            session.commit()

    async def get_user_analytics(self, user_id: int, days: int = 30) -> List[UserAnalytics]:
        """Get user analytics for specified days."""
        with self.get_session() as session:
            start_date = datetime.utcnow() - timedelta(days=days)
            return (session.query(UserAnalytics)
                   .filter(UserAnalytics.user_id == user_id)
                   .filter(UserAnalytics.date >= start_date)
                   .order_by(UserAnalytics.date.desc())
                   .all())

    async def get_bot_statistics(self) -> Dict[str, Any]:
        """Get comprehensive bot statistics."""
        with self.get_session() as session:
            total_users = session.query(User).count()
            active_users = session.query(User).filter_by(is_active=True).count()
            total_downloads = session.query(Download).count()
            completed_downloads = session.query(Download).filter_by(download_status='completed').count()

            # Recent activity (last 24 hours)
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_users = session.query(User).filter(User.last_activity >= yesterday).count()
            recent_downloads = session.query(Download).filter(Download.start_time >= yesterday).count()

            return {
                'total_users': total_users,
                'active_users': active_users,
                'recent_active_users': recent_users,
                'total_downloads': total_downloads,
                'completed_downloads': completed_downloads,
                'recent_downloads': recent_downloads,
                'success_rate': (completed_downloads / total_downloads * 100) if total_downloads > 0 else 0
            }

    # Settings methods
    async def get_setting(self, key: str, default=None):
        """Get bot setting."""
        with self.get_session() as session:
            setting = session.query(BotSettings).filter_by(key=key).first()
            return setting.value if setting else default

    async def set_setting(self, key: str, value: Any, description: str = None):
        """Set bot setting."""
        with self.get_session() as session:
            setting = session.query(BotSettings).filter_by(key=key).first()
            if setting:
                setting.value = value
                setting.updated_date = datetime.utcnow()
                if description:
                    setting.description = description
            else:
                setting = BotSettings(key=key, value=value, description=description)
                session.add(setting)
            session.commit()

    # Cleanup methods
    async def cleanup_old_data(self, days: int = 30):
        """Clean up old data to maintain performance."""
        with self.get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Clean old analytics
            old_analytics = session.query(UserAnalytics).filter(UserAnalytics.date < cutoff_date)
            deleted_analytics = old_analytics.count()
            old_analytics.delete()

            # Clean old failed downloads
            old_downloads = session.query(Download).filter(
                Download.start_time < cutoff_date,
                Download.download_status == 'failed'
            )
            deleted_downloads = old_downloads.count()
            old_downloads.delete()

            # Clean expired cache
            expired_cache = session.query(FileCache).filter(
                FileCache.expires_at < datetime.utcnow()
            )
            deleted_cache = expired_cache.count()
            expired_cache.delete()

            session.commit()

            self.logger.info(f"🧹 Cleaned up: {deleted_analytics} analytics, {deleted_downloads} downloads, {deleted_cache} cache entries")

            return {
                'analytics_deleted': deleted_analytics,
                'downloads_deleted': deleted_downloads,
                'cache_deleted': deleted_cache
            }

    async def get_user(self, user_id):
        """Get user by ID."""
        with self.get_session() as session:
            return session.query(User).filter_by(id=user_id).first()

    async def list_users(self):
        """Get all users."""
        with self.get_session() as session:
            return session.query(User).all()

    async def list_banned_users(self):
        """Get all banned users (is_banned=True)."""
        with self.get_session() as session:
            return session.query(User).filter_by(is_banned=True).all()

    async def list_premium_users(self):
        """Get all premium users (is_premium=True)."""
        with self.get_session() as session:
            return session.query(User).filter_by(is_premium=True).all()

    async def get_user_stats(self):
        """Get user statistics using boolean fields only."""
        with self.get_session() as session:
            total = session.query(User).count()
            active = session.query(User).filter_by(is_active=True).count()
            premium = session.query(User).filter_by(is_premium=True).count()
            banned = session.query(User).filter_by(is_banned=True).count()
            return {'total': total, 'active': active, 'premium': premium, 'banned': banned}

    async def get_bot_stats(self):
        with self.get_session() as session:
            users = session.query(User).count()
            downloads = session.query(Download).count()
            active_users = session.query(User).filter_by(status='نشط').count()
            return {'users': users, 'downloads': downloads, 'active_users': active_users}

    async def get_detailed_stats(self):
        with self.get_session() as session:
            top_users = ', '.join([u.username for u in session.query(User).order_by(User.total_downloads.desc()).limit(3) if u.username])
            top_files = ', '.join([f.filename for f in session.query(Download).order_by(Download.file_size.desc()).limit(3) if f.filename])
            avg_daily_downloads = session.query(Download).count() // 30
            return {'top_users': top_users, 'top_files': top_files, 'avg_daily_downloads': avg_daily_downloads}

    async def get_system_settings(self):
        with self.get_session() as session:
            settings = session.query(BotSettings).first()
            return {
                'language': settings.value.get('language', 'ar'),
                'timezone': settings.value.get('timezone', 'Asia/Riyadh'),
                'max_download': settings.value.get('max_file_size', '50MB'),
                'backup': settings.value.get('backup_enabled', 'يومي')
            } if settings else {'language': 'ar', 'timezone': 'Asia/Riyadh', 'max_download': '50MB', 'backup': 'يومي'}

    async def get_system_logs(self):
        with self.get_session() as session:
            logs = session.query(UserAnalytics).order_by(UserAnalytics.date.desc()).limit(10).all()
            return [f"[{log.date}] {log.action_type}: {log.action_data}" for log in logs]

    async def create_backup(self):
        # تنفيذ منطق النسخ الاحتياطي الحقيقي هنا
        try:
            # ... منطق النسخ الاحتياطي ...
            return True
        except Exception:
            return False

    async def schedule_auto_backup(self, interval_seconds: int = 86400):
        """جدولة النسخ الاحتياطي التلقائي كل فترة محددة مع إشعار ذكي وإرسال للقنوات/المجموعات."""
        from asyncio import create_task, sleep
        async def backup_loop():
            while True:
                try:
                    await self.create_backup()
                    # إشعار ذكي وإرسال للقنوات بعد النسخ الاحتياطي التلقائي
                    if hasattr(self, 'bot_manager') and hasattr(self.bot_manager, 'notification_service'):
                        backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                        await self.bot_manager.notification_service.send_backup_notification(
                            user_id=self.bot_manager.config.OWNER_ID,
                            backup_file=backup_filename,
                            success=True
                        )
                        if getattr(self.bot_manager.config, 'TARGET_CHANNELS', []):
                            await self.bot_manager.send_to_target_channels(
                                text=f"💾 تم إنشاء نسخة احتياطية تلقائية: {backup_filename}",
                                document=f"data/backups/{backup_filename}"
                            )
                except Exception as e:
                    if hasattr(self, 'bot_manager') and hasattr(self.bot_manager, 'notification_service'):
                        await self.bot_manager.notification_service.send_backup_notification(
                            user_id=self.bot_manager.config.OWNER_ID,
                            backup_file='غير معروف',
                            success=False
                        )
                await sleep(interval_seconds)
        create_task(backup_loop())

    async def get_recent_activity_logs(self, limit: int = 50):
        """استرجاع أحدث النشاطات من سجل الأناليتكس."""
        with self.get_session() as session:
            logs = session.query(UserAnalytics).order_by(UserAnalytics.date.desc()).limit(limit).all()
            return [f"[{log.date}] {log.action_type}: {log.action_data}" for log in logs]

    async def get_forced_subscription_channels(self) -> list:
        """Get the list of forced subscription channels from bot_settings."""
        with self.get_session() as session:
            setting = session.query(BotSettings).filter_by(key='forced_subscription_channels').first()
            if setting and setting.value:
                return setting.value
            return []

    async def set_forced_subscription_channels(self, channels: list):
        """Set the list of forced subscription channels in bot_settings."""
        await self.set_setting('forced_subscription_channels', channels, description='قائمة القنوات/الروابط للاشتراك الإجباري')

    async def add_forced_subscription_channel(self, channel: dict):
        channels = await self.get_forced_subscription_channels()
        # إذا لم يحدد التصنيف، اعتبرها ثانوية افتراضياً
        if 'type' not in channel:
            channel['type'] = 'secondary'
        channels.append(channel)
        await self.set_forced_subscription_channels(channels)

    async def set_forced_subscription_channel_type(self, channel_id: str, new_type: str):
        channels = await self.get_forced_subscription_channels()
        for c in channels:
            if c.get('id') == channel_id or c.get('url') == channel_id:
                c['type'] = new_type
        await self.set_forced_subscription_channels(channels)

    async def remove_forced_subscription_channel(self, channel_id: str):
        """Remove a channel from the forced subscription list by id or url."""
        channels = await self.get_forced_subscription_channels()
        channels = [c for c in channels if c.get('id') != channel_id and c.get('url') != channel_id]
        await self.set_forced_subscription_channels(channels)

    async def clear_forced_subscription_channels(self):
        """Clear all forced subscription channels."""
        await self.set_forced_subscription_channels([])

    async def get_forced_subscription_sections(self) -> list:
        # جلب جميع الأقسام (main, secondary, accounts)
        with self.get_session() as session:
            setting = session.query(BotSettings).filter_by(key='forced_subscription_sections').first()
            if setting and setting.value:
                return setting.value
            # افتراضي: main, secondary, accounts
            return [
                {'id': 'main', 'name': 'القسم الرئيسي', 'message': 'يرجى الاشتراك في القنوات الرئيسية التالية:', 'max_count': 5},
                {'id': 'secondary', 'name': 'القسم الثانوي', 'message': 'يرجى الاشتراك في القنوات الثانوية التالية:', 'max_count': 5},
                {'id': 'accounts', 'name': 'قسم الحسابات', 'message': 'أرسل كليشة الاشتراك مع رابط حسابك الذي قمت بتعيينه.', 'max_count': 5}
            ]
    async def set_forced_subscription_sections(self, sections: list):
        await self.set_setting('forced_subscription_sections', sections, description='أقسام الاشتراك الإجباري')
    async def set_section_message(self, section_id: str, message: str):
        sections = await self.get_forced_subscription_sections()
        for s in sections:
            if s['id'] == section_id:
                s['message'] = message
        await self.set_forced_subscription_sections(sections)
    async def set_section_max_count(self, section_id: str, max_count: int):
        sections = await self.get_forced_subscription_sections()
        for s in sections:
            if s['id'] == section_id:
                s['max_count'] = max_count
        await self.set_forced_subscription_sections(sections)
    async def get_section_by_id(self, section_id: str):
        sections = await self.get_forced_subscription_sections()
        for s in sections:
            if s['id'] == section_id:
                return s
        return None

    async def add_admin_chat(self, chat_id, chat_type, title=None, username=None):
        with self.get_session() as session:
            chat = session.query(BotAdminChat).filter_by(id=chat_id).first()
            if not chat:
                chat = BotAdminChat(id=chat_id, type=chat_type, title=title, username=username)
                session.add(chat)
                session.commit()
    async def remove_admin_chat(self, chat_id):
        with self.get_session() as session:
            chat = session.query(BotAdminChat).filter_by(id=chat_id).first()
            if chat:
                session.delete(chat)
                session.commit()
    async def get_all_admin_chats(self):
        with self.get_session() as session:
            return session.query(BotAdminChat).all()



