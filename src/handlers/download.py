#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Download Handler
===============

Advanced download handler with support for multiple file types,
progress tracking, resume capability, and comprehensive error handling.
"""

import os
import asyncio
import logging
import hashlib
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import aiohttp
import aiofiles
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.services.download_service import DownloadService
import base64
import threading
import json
import shutil
import re
from src.utils.performance_monitor import performance_monitor
from src.utils.localization_core import get_text
from src.services.download_service import get_youtube_playlist_items
from telegram.constants import ParseMode
from src.services.download_service import get_youtube_search_results
from src.services.download_service import get_youtube_video_details

def sanitize_filename(filename, fallback="video.mp4"):
    base, ext = os.path.splitext(filename)
    base = re.sub(r'[^\w\u0600-\u06FF\-\s]', '_', base)
    if len(base) > 55:
        base = base[:55]
    safe_name = base.strip() + ext
    if not safe_name or len(safe_name) < 5:
        return fallback
    return safe_name

class DownloadHandler:
    """Advanced download handler with progress tracking and resume capability."""

    def __init__(self, bot_manager, config, db_manager):
        """Initialize download handler."""
        self.bot_manager = bot_manager
        self.config = config
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        self.active_downloads = {}  # Track active downloads
        # DownloadService now auto-loads cookies from data/cookies/ if available
        self.download_service = DownloadService(self.config.DOWNLOAD_DIRECTORY)
        self.url_map = {}  # mapping: short_id -> url
        self.active_playlists = {}  # user_id -> {'cancel': False, 'progress': int}

        # Ensure download directory exists
        os.makedirs(self.config.DOWNLOAD_DIRECTORY, exist_ok=True)

    async def handle_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # إذا كان هناك انتظار إداري، تجاهل الرسالة فوراً
        if (
            context.user_data.get('awaiting_broadcast_message') or
            context.user_data.get('awaiting_forced_channel') or
            context.user_data.get('awaiting_section_message') or
            context.user_data.get('awaiting_section_max')
        ):
            return
        self.logger.info(f"[DIAG] Command Triggered: {update.message.text if update.message else ''}")
        """Handle URL download requests."""
        user = update.effective_user
        message = update.message
        url = message.text.strip()

        try:
            # Register user and update activity
            await self.bot_manager.register_user(user)
            await self.bot_manager.update_user_activity(
                user.id,
                'download_request',
                {'url': url}
            )

            # Check if user is banned
            if await self.bot_manager.is_user_banned(user.id):
                await message.reply_text("❌ تم حظرك من استخدام البوت.")
                return

            # Validate URL
            if not self._is_valid_url(url):
                await message.reply_text(
                    "❌ الرابط غير صحيح. يرجى إرسال رابط صالح للملف."
                )
                return

            # Check if download is already in progress
            if user.id in self.active_downloads:
                await message.reply_text(
                    "⏳ لديك تحميل جاري بالفعل. يرجى انتظار انتهائه أولاً."
                )
                return

            # Start download process
            await self._start_download(update, context, url)

        except Exception as e:
            self.logger.error(f"Error in URL handler: {e}")
            await message.reply_text(
                "❌ حدث خطأ أثناء معالجة الرابط. يرجى المحاولة مرة أخرى."
            )

    async def handle_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.logger.info(f"[DIAG] File Upload Triggered: {update.message.document or update.message.photo or update.message.video or update.message.audio}")
        """Handle direct file uploads."""
        user = update.effective_user
        message = update.message

        try:
            # Register user and update activity
            await self.bot_manager.register_user(user)

            # Get file info
            file_obj = None
            file_name = None
            file_size = None

            if message.document:
                file_obj = message.document
                file_name = file_obj.file_name
                file_size = file_obj.file_size
            elif message.photo:
                file_obj = message.photo[-1]  # Get highest resolution
                file_name = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                file_size = file_obj.file_size
            elif message.video:
                file_obj = message.video
                file_name = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                file_size = file_obj.file_size
            elif message.audio:
                file_obj = message.audio
                file_name = file_obj.file_name or f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
                file_size = file_obj.file_size

            if not file_obj:
                await message.reply_text("❌ نوع الملف غير مدعوم.")
                return

            # Check file size
            if file_size and file_size > self.config.MAX_DOWNLOAD_SIZE:
                size_mb = file_size / (1024 * 1024)
                max_mb = self.config.MAX_DOWNLOAD_SIZE / (1024 * 1024)
                await message.reply_text(
                    f"❌ حجم الملف ({size_mb:.1f} MB) يتجاوز الحد المسموح ({max_mb} MB)."
                )
                return

            # Check file type
            file_ext = Path(file_name).suffix.lower().lstrip('.')
            if file_ext not in self.config.ALLOWED_FORMATS:
                await message.reply_text(
                    f"❌ نوع الملف .{file_ext} غير مدعوم.\n"
                    f"الأنواع المدعومة: {', '.join(self.config.ALLOWED_FORMATS)}"
                )
                return

            await self.bot_manager.update_user_activity(
                user.id,
                'file_upload',
                {'filename': file_name, 'size': file_size}
            )

            # Start file processing
            await self._process_uploaded_file(update, context, file_obj, file_name, file_size)

        except Exception as e:
            self.logger.error(f"Error in file handler: {e}")
            await message.reply_text(
                "❌ حدث خطأ أثناء معالجة الملف. يرجى المحاولة مرة أخرى."
            )

    async def _start_download(self, update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
        user = update.effective_user
        message = update.message

        # Send initial message
        status_message = await message.reply_text(
            "🔍 جاري فحص الرابط...",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data=f"cancel_download_{user.id}")]])
        )

        try:
            # إذا كان الرابط لقائمة تشغيل يوتيوب، أظهر أزرار تحميل القائمة كاملة
            if ("youtube.com/playlist" in url or ("youtube.com" in url and "list=" in url)):
                playlist_id = self._extract_playlist_id(url)
                if playlist_id:
                    playlist_items = get_youtube_playlist_items(playlist_id)
                    if not playlist_items:
                        await status_message.edit_text(
                            "❌ لم يتم العثور على أي أغاني في قائمة التشغيل (YouTube Data API).\nيرجى التأكد من صحة الرابط أو المحاولة لاحقًا.",
                            parse_mode='HTML',
                            reply_markup=None
                        )
                        return
                    # رسالة احترافية مع أزرار تحميل القائمة كاملة
                    playlist_title = playlist_items[0]['title'] if playlist_items else 'قائمة تشغيل'
                    total = len(playlist_items)
                    text = (
                        f"📃 <b>قائمة التشغيل:</b> {playlist_title}\n"
                        f"🎶 <b>عدد الفيديوهات:</b> {total}\n\n"
                        f"اختر نوع التحميل الكامل للقائمة:"
                    )
                    keyboard = [
                        [InlineKeyboardButton("⬇️ تحميل القائمة كاملة كفيديوهات (mp4)", callback_data=f"ytpl_dl|video|{playlist_id}")],
                        [InlineKeyboardButton("⬇️ تحميل القائمة كاملة كأغاني (mp3)", callback_data=f"ytpl_dl|audio|{playlist_id}")]
                    ]
                    await status_message.edit_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
                    return
            # Get file info بالطريقة القديمة (yt-dlp)
            info = await self._extract_info_async(url)
            if not info:
                await status_message.edit_text("❌ لا يمكن الوصول للرابط أو غير مدعوم.")
                return
            if 'entries' in info:  # قائمة تشغيل
                await self._show_playlist_menu(update, context, info, url, status_message)
                return
            await self._show_download_options(update, context, info, url, status_message)
        except Exception as e:
            self.logger.error(f"Download error: {e}")
            await status_message.edit_text(f"❌ فشل التحميل: {str(e)}")
        finally:
            if user.id in self.active_downloads:
                del self.active_downloads[user.id]

    async def _extract_info_async(self, url):
        from concurrent.futures import ThreadPoolExecutor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(ThreadPoolExecutor(), lambda: self.download_service.extract_info(url))

    def _get_short_id(self, url: str) -> str:
        # استخدم hash قصير (8 رموز) لكل رابط
        return hashlib.sha256(url.encode()).hexdigest()[:8]

    def _register_url(self, url: str) -> str:
        short_id = self._get_short_id(url)
        self.url_map[short_id] = url
        return short_id

    def _get_url(self, short_id: str) -> str:
        return self.url_map.get(short_id, short_id)  # fallback: short_id

    async def _show_download_options(self, update, context, info, url, status_message):
        short_id = self._register_url(url)
        formats = self.download_service.get_formats(url, info)
        video_formats = [f for f in formats if f.get('vcodec') != 'none']
        audio_formats = [f for f in formats if f.get('acodec') != 'none']
        keyboard = []
        if video_formats:
            keyboard.append([InlineKeyboardButton("🎬 تحميل فيديو (أفضل جودة)", callback_data=f"dlv|{short_id}")])
            keyboard.append([InlineKeyboardButton("🎵 تحميل كأغنية (mp3)", callback_data=f"dlva|{short_id}")])
        elif audio_formats:
            keyboard.append([InlineKeyboardButton("🎵 تحميل صوت (mp3)", callback_data=f"dla|{short_id}")])
        keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="main_menu")])
        # تحديد المنصة
        platform = self.download_service._get_platform(url)
        platform_name = platform.__class__.__name__ if platform else "Unknown"
        # منطق الرسالة: فقط YouTube يظهر العنوان والمعلومات
        if platform_name == "YoutubeDownloader":
            title = info.get('title', '-')
            duration = info.get('duration')
            duration_str = f"⏱️ المدة: {duration//60} دقيقة {duration%60} ثانية" if duration else ""
            text = f"🎬 العنوان: {title}\n{duration_str}\nاختر نوع التحميل:"
        else:
            text = "اختر نوع التحميل:"  # بدون عنوان أو تفاصيل
        await status_message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _show_playlist_menu(self, update, context, info, url, status_message, page=0):
        user_id = update.effective_user.id
        if not hasattr(self, 'last_playlist_info'):
            self.last_playlist_info = {}
        self.last_playlist_info[user_id] = info
        short_id = self._register_url(url)
        playlist = self.download_service.list_playlist(info)
        page_size = 5
        total = len(playlist)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        start = page * page_size
        end = min(start + page_size, total)
        items = playlist[start:end]

        # Debug: طباعة محتوى entries
        try:
            print("[DEBUG] info['entries']:", info.get('entries'))
        except Exception as e:
            print(f"[DEBUG] Exception printing entries: {e}")

        # إذا كانت القائمة فارغة
        if total == 0:
            await status_message.edit_text(
                "❌ لم يتم العثور على أي أغاني في قائمة التشغيل.\nيرجى التأكد من صحة الرابط أو المحاولة لاحقًا.",
                parse_mode='HTML',
                reply_markup=None
            )
            return

        # بناء نص الرسالة
        text = (
            f"📃 <b>قائمة التشغيل:</b> {info.get('title','-')}\n"
            f"🎶 <b>عدد الأغاني:</b> {total}\n"
            f"📄 <b>صفحة:</b> {page+1} من {total_pages}\n\n"
            f"اختر أغنية من القائمة أدناه لتصفح خيارات التحميل، أو استخدم الأزرار بالأسفل لتحميل القائمة كاملة."
        )

        # بناء الأزرار للأغاني
        keyboard = []
        for idx, item in enumerate(items, start=start):
            keyboard.append([
                InlineKeyboardButton(f"🎵 {idx+1}. {item['title']}", callback_data=f"dpop|{short_id}|{idx}")
            ])

        # أزرار التنقل بين الصفحات
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"ppg|{short_id}|{page-1}"))
        if end < total:
            nav.append(InlineKeyboardButton("التالي ➡️", callback_data=f"ppg|{short_id}|{page+1}"))
        if nav:
            keyboard.append(nav)

        # أزرار تحميل القائمة كاملة
        keyboard.append([
            InlineKeyboardButton("⬇️ تحميل القائمة كاملة (فيديو)", callback_data=f"dpa|{short_id}"),
            InlineKeyboardButton("⬇️ تحميل القائمة كاملة (mp3)", callback_data=f"dpaa|{short_id}")
        ])
        # زر العودة
        keyboard.append([InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")])

        await status_message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    async def _show_playlist_item_options(self, update, context, short_id, idx):
        user_id = update.effective_user.id
        info = self.last_playlist_info.get(user_id)
        playlist = self.download_service.list_playlist(info)
        total = len(playlist)
        if not playlist or idx >= total:
            await update.callback_query.edit_message_text("❌ لم يتم العثور على رابط العنصر المطلوب.")
            return
        item = playlist[idx]
        title = item.get('title', 'العنصر المطلوب')
        # حساب رقم الصفحة الحالية
        page_size = 5
        page = idx // page_size
        text = (
            f"🎵 <b>{title}</b>\n"
            f"🔢 <b>الأغنية رقم:</b> {idx+1} من {total}\n\n"
            f"اختر نوع التحميل المطلوب أو اضغط الرجوع للعودة إلى صفحة التصفح السابقة."
        )
        keyboard = [
            [InlineKeyboardButton("🎬 تحميل كفيديو (mp4)", callback_data=f"dpopv|{short_id}|{idx}")],
            [InlineKeyboardButton("🎵 تحميل كصوت (mp3)", callback_data=f"dpopa|{short_id}|{idx}")],
            [InlineKeyboardButton("🔙 رجوع للصفحة السابقة", callback_data=f"ppg|{short_id}|{page}")]
        ]
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

    async def _download_playlist_sequential(self, update, context, url, playlist_items, audio_only=False, delete_after_send=False):
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        total = len(playlist_items)
        self.active_playlists[user_id] = {'cancel': False, 'progress': 0}
        sent = 0
        failed = 0
        status_message = await context.bot.send_message(
            chat_id,
            f"⏳ جاري تحميل القائمة (0/{total})...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ إلغاء التحميل", callback_data="cancel_playlist")]
            ])
        )
        for idx, item in enumerate(playlist_items):
            await asyncio.sleep(0.1)  # للسماح بمعالجة الأحداث وزر الإلغاء
            self.logger.debug(f"[CANCEL_CHECK] User {user_id} cancel={self.active_playlists.get(user_id, {}).get('cancel', None)} at idx={idx}")
            if user_id not in self.active_playlists or self.active_playlists[user_id].get('cancel'):
                self.logger.info(f"[CANCELLED] Playlist download cancelled for user {user_id} after {sent} sent.")
                await status_message.edit_text(
                    f"⏹️ تم إلغاء تحميل القائمة بعد إرسال {sent} من {total}.",
                    reply_markup=None
                )
                if user_id in self.active_playlists:
                    del self.active_playlists[user_id]
                return
            try:
                # تحميل فقط من نفس عناصر القائمة
                file_obj = await self._download_playlist_item_async(item['url'], audio_only=audio_only)
                import io
                if isinstance(file_obj, io.BytesIO):
                    file_obj.seek(0)
                    if audio_only:
                        # اسم الملف من عنوان المقطع
                        ext = 'mp3'
                        base_title = item.get('title', f'item_{idx+1}')
                        safe_title = sanitize_filename(base_title, fallback=f'item_{idx+1}.mp3')
                        filename = f"{safe_title}.mp3" if not safe_title.endswith('.mp3') else safe_title
                        caption = f"🎵 {base_title}\nتم التحميل بواسطة - @Z9QBOT"
                        await context.bot.send_audio(chat_id, audio=file_obj, filename=filename, caption=caption)
                    else:
                        ext = 'mp4'
                        base_title = item.get('title', f'item_{idx+1}')
                        safe_title = sanitize_filename(base_title, fallback=f'item_{idx+1}.mp4')
                        filename = f"{safe_title}.mp4" if not safe_title.endswith('.mp4') else safe_title
                        caption = f"🎬 {base_title}\nتم التحميل بواسطة - @Z9QBOT"
                        await context.bot.send_video(chat_id, video=file_obj, filename=filename, caption=caption, supports_streaming=True)
                else:
                    # fallback: إرسال كملف document
                    base_title = item.get('title', f'item_{idx+1}')
                    safe_title = sanitize_filename(base_title, fallback=f'item_{idx+1}.mp3' if audio_only else f'item_{idx+1}.mp4')
                    filename = f"{safe_title}.mp3" if audio_only and not safe_title.endswith('.mp3') else safe_title
                    filename = f"{safe_title}.mp4" if not audio_only and not safe_title.endswith('.mp4') else filename
                    caption = f"🎵 {base_title}\nتم التحميل بواسطة - @Z9QBOT" if audio_only else f"🎬 {base_title}\nتم التحميل بواسطة - @Z9QBOT"
                    await context.bot.send_document(chat_id, open(file_obj, 'rb'), filename=filename, caption=caption)
                if delete_after_send and not isinstance(file_obj, io.BytesIO):
                    try:
                        os.remove(file_obj)
                    except Exception:
                        pass
                sent += 1
            except Exception as e:
                failed += 1
                self.logger.error(f"[PLAYLIST_ITEM_FAIL] User {user_id} idx={idx} error: {e}")
            self.active_playlists[user_id]['progress'] = idx+1
            if user_id in self.active_playlists and not self.active_playlists[user_id].get('cancel'):
                await status_message.edit_text(
                    f"⏳ جاري تحميل القائمة ({sent+failed}/{total})...\n✅ تم الإرسال: {sent}\n❌ فشل: {failed}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❌ إلغاء التحميل", callback_data="cancel_playlist")]
                    ])
                )

    async def _download_playlist_item_async(self, url, audio_only=False):
        from concurrent.futures import ThreadPoolExecutor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(ThreadPoolExecutor(), lambda: self.download_service.download(url, audio_only=audio_only))

    async def _download_and_send(self, update, context, url, audio_only=False, delete_after_send=False, as_voice=False, status_message=None):
        import time
        start_time = time.time()
        query = update.callback_query
        msg = query.message if query else update.message
        user_id = update.effective_user.id
        max_size = 50 * 1024 * 1024  # 50MB
        if not status_message:
            status_message = await msg.reply_text("⏳ جاري التحميل...")
        from concurrent.futures import ThreadPoolExecutor
        loop = asyncio.get_event_loop()
        try:
            info = await self._extract_info_async(url)
            formats = self.download_service.get_formats(url, info)
            # فيديو: اختر أعلى دقة متاحة أقل من 50MB
            if not audio_only:
                video_formats = [f for f in formats if f.get('vcodec') != 'none' and ((f.get('filesize') and f.get('filesize') < max_size) or (f.get('filesize_approx') and f.get('filesize_approx') < max_size))]
                if not video_formats:
                    keyboard = [
                        [InlineKeyboardButton("🎵 تحميل كصوت (mp3)", callback_data=f"dlva|{self._register_url(url)}")],
                        [InlineKeyboardButton("🔙 العودة", callback_data="main_menu")]
                    ]
                    await status_message.edit_text(
                        "❌ لا توجد أي دقة فيديو متاحة أقل من 50MB. يمكنك تحميل الملف كصوت mp3 فقط.",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    return
            file_obj = await loop.run_in_executor(ThreadPoolExecutor(), lambda: self.download_service.download(url, audio_only=audio_only))
            if not file_obj or (hasattr(file_obj, 'getbuffer') and file_obj.getbuffer().nbytes < 1024):
                await status_message.edit_text("❌ فشل التحميل. الرابط غير صالح أو الملف غير متاح.")
                self.logger.error(f"[DOWNLOAD] File not found or too small: {file_obj}")
                return
            # تحديد المنصة
            platform = self.download_service._get_platform(url)
            platform_name = platform.__class__.__name__ if platform else "Unknown"
            # منطق التسمية: فقط YouTube استخدم العنوان، الباقي اسم افتراضي
            if platform_name == "YoutubeDownloader":
                safe_filename = "video.mp4"
                caption = f"🎬 {safe_filename}\nتم التحميل بواسطة - @Z9QBOT"
            else:
                if audio_only:
                    safe_filename = "audio.mp3"
                else:
                    safe_filename = "video.mp4"
                caption = "تم التحميل بواسطة - @Z9QBOT"
            # أرسل الفيديو أو الصوت مباشرة من BytesIO
            try:
                file_obj.seek(0)
                if audio_only:
                    await context.bot.send_audio(
                        chat_id=msg.chat_id,
                        audio=file_obj,
                        filename=safe_filename,
                        caption=caption
                    )
                else:
                    await context.bot.send_video(
                        chat_id=msg.chat_id,
                        video=file_obj,
                        filename=safe_filename,
                        caption=caption,
                        supports_streaming=True
                    )
                await status_message.delete()
                performance_monitor.log_response_time('download_success', (time.time()-start_time)*1000)
                return
            except Exception as ve:
                self.logger.error(f"[SEND_VIDEO] Failed to send video/audio as {safe_filename}: {ve}")
                try:
                    file_obj.seek(0)
                    await context.bot.send_document(chat_id=msg.chat_id, document=file_obj, filename=safe_filename, caption=caption)
                    await status_message.delete()
                    performance_monitor.log_response_time('download_success', (time.time()-start_time)*1000)
                    return
                except Exception as e2:
                    await status_message.edit_text(f"❌ فشل التحميل أو الإرسال: {ve}")
                    self.logger.error(f"[SEND_DOC] {e2}")
                    return
        except Exception as e:
            await status_message.edit_text(f"❌ فشل التحميل أو الإرسال: {e}")
            self.logger.error(f"[DOWNLOAD][EXCEPTION] {e}")
            return

    async def _process_uploaded_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   file_obj, filename: str, file_size: int):
        """Process uploaded file."""
        user = update.effective_user
        message = update.message

        # Send processing message
        status_message = await message.reply_text("📤 جاري معالجة الملف...")

        try:
            # Download file from Telegram
            file = await file_obj.get_file()

            # Create file path
            file_path = os.path.join(
                self.config.DOWNLOAD_DIRECTORY,
                f"upload_{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            )

            # Download file
            await file.download_to_drive(file_path)

            # Create download record
            download_data = {
                'user_id': user.id,
                'url': f"telegram_upload_{file.file_id}",
                'filename': filename,
                'file_size': file_size,
                'file_type': Path(filename).suffix.lower().lstrip('.'),
                'download_status': 'completed',
                'file_path': file_path,
                'completion_time': datetime.utcnow(),
                'download_progress': 100.0
            }

            download_record = await self.bot_manager.db.create_download(download_data)

            # Update user stats
            user_data = await self.bot_manager.db.get_user(user.id)
            await self.bot_manager.db.update_user(
                user.id,
                {
                    'total_uploads': user_data.total_uploads + 1,
                    'storage_used': user_data.storage_used + file_size
                }
            )

            # Send completion message
            await self._send_completion_message(status_message, {'filename': filename, 'size': file_size}, download_record)

        except Exception as e:
            self.logger.error(f"File processing error: {e}")
            await status_message.edit_text(f"❌ فشل في معالجة الملف: {str(e)}")

    async def _send_completion_message(self, status_message, file_info: Dict, download_record):
        """Send download completion message + إشعار ذكي + إرسال للقنوات/المجموعات + تسجيل النشاط."""
        completion_text = (
            f"✅ تم التحميل بنجاح!\n\n"
            f"📊 الحجم: {self._format_size(file_info['size'])}\n"
            f"🆔 معرف التحميل: {download_record.id}\n"
            f"⏰ وقت الانتهاء: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        keyboard = [
            [InlineKeyboardButton("📋 عرض التفاصيل", callback_data=f"download_details_{download_record.id}" )],
            [InlineKeyboardButton("📤 مشاركة", callback_data=f"share_file_{download_record.id}")],
            [InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_download_{download_record.id}")]
        ]
        await status_message.edit_text(
            completion_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        # 1) سجل النشاط
        await self.bot_manager.update_user_activity(download_record.user_id, 'download_completed', {'download_id': download_record.id, 'filename': download_record.filename})
        # 2) إشعار ذكي
        if getattr(self.config, 'SMART_NOTIFICATIONS_ENABLED', False):
            from src.services.notification_service import NotificationType
            await self.bot_manager.notification_service.send_notification(
                user_id=download_record.user_id,
                notification_type=NotificationType.DOWNLOAD_COMPLETE,
                data={'filename': download_record.filename, 'file_size_mb': round(download_record.file_size/1024/1024,2)},
            )
        # 3) إرسال للقنوات/المجموعات
        if getattr(self.config, 'TARGET_CHANNELS', []):
            await self.bot_manager.send_to_target_channels(
                text=f"📥 تم تحميل ملف جديد: {download_record.filename}",
                document=download_record.file_path
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        user = update.effective_user
        text = message.text.strip()
        # إذا كانت الرسالة معرف فيديو مختصر مثل /k_xxxxxxx
        if text.startswith('/k_') and len(text) > 4:
            video_id = text[3:]
            await self._show_youtube_video_details_menu(message, context, video_id, query=None, force_from_code=True)
            return
        # إذا كانت الرسالة رابط أو أمر معروف، تجاهل البحث
        if text.startswith('/') or text.startswith('http://') or text.startswith('https://'):
            return
        # أي نص آخر اعتبره بحث في يوتيوب
        query = text
        if not query:
            await message.reply_text("يرجى كتابة كلمة البحث.")
            return
        await self._search_youtube_and_show_results(update, context, query)

    async def _search_youtube_and_show_results(self, update, context, query, page_token=None):
        msg = update.message or (update.callback_query and update.callback_query.message)
        results, next_page_token = get_youtube_search_results(query, page_token=page_token, max_results=10)
        if not results:
            await msg.reply_text("❌ لم يتم العثور على نتائج.")
            return
        lines = [f"📍 <b>نتائج البحث ({query})</b>:"]
        for idx, item in enumerate(results, 1):
            video_id = item['video_id']
            details = get_youtube_video_details(video_id)
            if not details:
                continue
            title = details['title']
            channel = details['channel']
            duration = details['duration']
            views = int(details['views'])
            url = f"https://www.youtube.com/watch?v={video_id}"
            lines.append(
                f"\n🎬 <a href='{url}'>{title}</a>\n"
                f"<b>القناة:</b> {channel}\n"
                f"<b>⏱️</b> {duration} دقيقة | <b>👁️</b> {views:,} views\n"
                f"/k_{video_id}"
            )
        if next_page_token:
            lines.append(f"\n➡️ للنتائج التالية أرسل: /next_{query}_{next_page_token}")
        await msg.reply_text("\n".join(lines), parse_mode=ParseMode.HTML, disable_web_page_preview=True)

    async def _show_youtube_video_details_menu(self, message_or_update, context, video_id, query=None, force_from_code=False):
        from telegram.constants import ParseMode
        # دعم الاستدعاء من handle_callback أو handle_message
        if hasattr(message_or_update, 'callback_query') and message_or_update.callback_query:
            query_obj = message_or_update.callback_query
        else:
            query_obj = None
        details = get_youtube_video_details(video_id)
        if not details:
            if query_obj:
                await query_obj.edit_message_text("❌ لم يتم جلب تفاصيل الفيديو.")
            else:
                await message_or_update.reply_text("❌ لم يتم جلب تفاصيل الفيديو.")
            return
        caption = (
            f"<b>🎬 {details['title']}</b>\n"
            f"<b>القناة:</b> {details['channel']}\n"
            f"<b>⏱️ المدة:</b> {details['duration']} دقيقة\n"
            f"<b>👁️ المشاهدات:</b> {int(details['views']):,}\n"
            f"https://www.youtube.com/watch?v={video_id}"
        )
        keyboard = [
            [InlineKeyboardButton("🎬 مقطع فيديو", callback_data=f"ytsearch_dl|video|{video_id}|{query or ''}")],
            [InlineKeyboardButton("🎵 ملف صوتي", callback_data=f"ytsearch_dl|audio|{video_id}|{query or ''}"),
             InlineKeyboardButton("🎤 مقطع صوتي", callback_data=f"ytsearch_dl|voice|{video_id}|{query or ''}")]
        ]
        if query_obj:
            await query_obj.edit_message_media(
                media=telegram.InputMediaPhoto(media=details['thumbnail'], caption=caption, parse_mode=ParseMode.HTML),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await message_or_update.reply_photo(
                photo=details['thumbnail'],
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def _download_youtube_search_result(self, update, context, mode, video_id, query):
        query_obj = update.callback_query
        url = f"https://www.youtube.com/watch?v={video_id}"
        # إذا كانت الرسالة ليست نصية (صورة أو فيديو)، احذفها وأرسل رسالة نصية جديدة
        msg = None
        try:
            await query_obj.delete_message()
        except Exception:
            pass
        msg = await query_obj.message.reply_text("⏳ جاري التحميل...")
        if mode == 'voice':
            await self._download_and_send(update, context, url, audio_only=True, delete_after_send=True, as_voice=True, status_message=msg)
        else:
            await self._download_and_send(update, context, url, audio_only=(mode=='audio'), status_message=msg)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        data = update.callback_query.data if update.callback_query else None
        print(f"[DEBUG] Callback data: {data}")
        user_id = update.effective_user.id if update.effective_user else None
        # لوج متقدم لكل زر
        self.logger.debug(f"[CALLBACK] User {user_id} data={data}")
        # مراقبة الأزرار
        try:
            performance_monitor.log_button(data, user_id=user_id, success=True)
        except Exception as e:
            performance_monitor.log_button(data, user_id=user_id, success=False, error=str(e))
        if data.startswith("cancel_download_"):
            await self._handle_cancel_download(update, context)
        elif data.startswith("download_details_"):
            await self._handle_download_details(update, context)
        elif data.startswith("share_file_"):
            await self._handle_share_file(update, context)
        elif data.startswith("delete_download_"):
            await self._handle_delete_download(update, context)
        elif data.startswith("file_details_"):
            await self._handle_file_details(update, context)
        elif data.startswith("delete_file_"):
            await self._handle_delete_file(update, context)
        elif data == "main_menu":
            if query and query.message:
                await context.bot.send_message(chat_id=query.message.chat_id, text="تم الرجوع للقائمة الرئيسية.")
            else:
                await context.bot.send_message(chat_id=query.from_user.id, text="تم الرجوع للقائمة الرئيسية.")
        elif data.startswith("dlv|"):
            short_id = data.split("|",1)[1]
            url = self._get_url(short_id)
            if not url.startswith('http'):
                await query.edit_message_text("❌ الرابط غير صالح داخلياً. يرجى إعادة المحاولة من البداية.")
                return
            await self._download_and_send(update, context, url, audio_only=False)
            # مراقبة المنصات عند التحميل
            platform = self._detect_platform_from_url(url)
            try:
                performance_monitor.log_platform(platform, 'download', user_id=user_id, success=True)
            except Exception as e:
                performance_monitor.log_platform(platform, 'download', user_id=user_id, success=False, error=str(e))
        elif data.startswith("dla|"):
            short_id = data.split("|",1)[1]
            url = self._get_url(short_id)
            if not url.startswith('http'):
                await query.edit_message_text("❌ الرابط غير صالح داخلياً. يرجى إعادة المحاولة من البداية.")
                return
            await self._download_and_send(update, context, url, audio_only=True)
            # مراقبة المنصات عند التحميل
            platform = self._detect_platform_from_url(url)
            try:
                performance_monitor.log_platform(platform, 'download', user_id=user_id, success=True)
            except Exception as e:
                performance_monitor.log_platform(platform, 'download', user_id=user_id, success=False, error=str(e))
        elif data.startswith("dlva|"):
            short_id = data.split("|",1)[1]
            url = self._get_url(short_id)
            if not url.startswith('http'):
                await query.edit_message_text("❌ الرابط غير صالح داخلياً. يرجى إعادة المحاولة من البداية.")
                return
            await self._download_and_send(update, context, url, audio_only=True, delete_after_send=True)
            # مراقبة المنصات عند التحميل
            platform = self._detect_platform_from_url(url)
            try:
                performance_monitor.log_platform(platform, 'download', user_id=user_id, success=True)
            except Exception as e:
                performance_monitor.log_platform(platform, 'download', user_id=user_id, success=False, error=str(e))
        elif data.startswith("dpop|"):
            # الضغط على اسم عنصر من القائمة: عرض نافذة خيارات التحميل
            short_id, idx = data.split("|",2)[1:]
            idx = int(idx)
            await self._show_playlist_item_options(update, context, short_id, idx)
        elif data.startswith("dpopv|"):
            # تحميل العنصر كفيديو
            short_id, idx = data.split("|",2)[1:]
            idx = int(idx)
            url = self.last_playlist_info.get(user_id, {}).get(idx)
            if not url:
                await query.edit_message_text("❌ لم يتم العثور على رابط العنصر المطلوب.")
                return
            await self._download_and_send(update, context, url, audio_only=False)
            # مراقبة المنصات عند التحميل
            platform = self._detect_platform_from_url(url)
            try:
                performance_monitor.log_platform(platform, 'download', user_id=user_id, success=True)
            except Exception as e:
                performance_monitor.log_platform(platform, 'download', user_id=user_id, success=False, error=str(e))
        elif data.startswith("dpopa|"):
            # تحميل العنصر كصوت mp3
            short_id, idx = data.split("|",2)[1:]
            idx = int(idx)
            url = self.last_playlist_info.get(user_id, {}).get(idx)
            if not url:
                await query.edit_message_text("❌ لم يتم العثور على رابط العنصر المطلوب.")
                return
            await self._download_and_send(update, context, url, audio_only=True, delete_after_send=True)
            # مراقبة المنصات عند التحميل
            platform = self._detect_platform_from_url(url)
            try:
                performance_monitor.log_platform(platform, 'download', user_id=user_id, success=True)
            except Exception as e:
                performance_monitor.log_platform(platform, 'download', user_id=user_id, success=False, error=str(e))
        elif data.startswith("dpa|"):
            short_id = data.split("|",1)[1]
            url = self._get_url(short_id)
            if not url.startswith('http'):
                await query.edit_message_text("❌ الرابط غير صالح داخلياً. يرجى إعادة المحاولة من البداية.")
                return
            await self._download_and_send(update, context, url)
            # مراقبة المنصات عند التحميل
            platform = self._detect_platform_from_url(url)
            try:
                performance_monitor.log_platform(platform, 'download', user_id=user_id, success=True)
            except Exception as e:
                performance_monitor.log_platform(platform, 'download', user_id=user_id, success=False, error=str(e))
        elif data.startswith("dpaa|"):
            short_id = data.split("|",1)[1]
            url = self._get_url(short_id)
            if not url.startswith('http'):
                await query.edit_message_text("❌ الرابط غير صالح داخلياً. يرجى إعادة المحاولة من البداية.")
                return
            playlist_info = self.last_playlist_info.get(user_id)
            if playlist_info:
                playlist_items = self.download_service.list_playlist(playlist_info)
                asyncio.create_task(self._download_playlist_sequential(update, context, url, playlist_items, audio_only=True, delete_after_send=True))
            else:
                await query.edit_message_text("❌ لا توجد قائمة تشغيل محفوظة.")
            return
        elif data.startswith("ppg|"):
            short_id, page = data.split("|",2)[1:]
            url = self._get_url(short_id)
            info = await self._extract_info_async(url)
            await self._show_playlist_menu(update, context, info, url, update.callback_query.message, page=int(page))
        elif data.startswith("ytapi_ppg|"):
            short_id, page = data.split("|",2)[1:]
            url = self._get_url(short_id)
            playlist_id = self._extract_playlist_id(url)
            if playlist_id:
                playlist_items = get_youtube_playlist_items(playlist_id)
                if not playlist_items:
                    await update.callback_query.edit_message_text(
                        "❌ لم يتم العثور على أي أغاني في قائمة التشغيل (YouTube Data API).\nيرجى التأكد من صحة الرابط أو المحاولة لاحقًا.",
                        parse_mode='HTML',
                        reply_markup=None
                    )
                    return
                await self._show_youtube_api_playlist_menu(update, context, playlist_items, url, update.callback_query.message, page=int(page))
            else:
                await update.callback_query.edit_message_text("❌ لم يتم العثور على معرف القائمة في الرابط.")
            return
        elif data == "cancel_playlist":
            self.logger.info(f"[CANCEL_PLAYLIST_BTN] User {user_id} pressed cancel.")
            if user_id not in self.active_playlists:
                await update.callback_query.answer("لا يوجد تحميل نشط أو تم الإلغاء بالفعل.", show_alert=True)
                return
            self.active_playlists[user_id]['cancel'] = True
            await update.callback_query.answer("تم إرسال طلب الإلغاء. سيتم إيقاف التحميل خلال ثوانٍ.", show_alert=True)
            return
        elif data and data.startswith("ytsearch_next|"):
            _, query, page_token = data.split("|", 2)
            await self._search_youtube_and_show_results(update, context, query, page_token=page_token)
            return
        elif data and data.startswith("ytsearch_dlmenu|"):
            _, video_id, query = data.split("|", 2)
            await self._show_youtube_search_download_menu(update, context, video_id, query)
            return
        elif data and data.startswith("ytsearch_dl|"):
            _, mode, video_id, query = data.split("|", 3)
            await self._download_youtube_search_result(update, context, mode, video_id, query)
            return
        elif data and data.startswith("ytsearch_back|"):
            _, query = data.split("|", 1)
            await self._search_youtube_and_show_results(update, context, query)
            return
        elif data and data.startswith("ytsearch_details|"):
            _, video_id, query = data.split("|", 2)
            await self._show_youtube_video_details_menu(update, context, video_id, query)
            return
        elif data and data.startswith("ytpl_dl|"):
            _, mode, playlist_id = data.split("|", 2)
            playlist_items = get_youtube_playlist_items(playlist_id)
            if not playlist_items:
                await update.callback_query.edit_message_text("❌ لم يتم العثور على أي فيديوهات في القائمة.")
                return
            self.active_playlists[user_id] = {'cancel': False, 'progress': 0}
            total = len(playlist_items)
            status_msg = await update.callback_query.edit_message_text(
                f"⏳ جاري تحميل القائمة (0/{total})...",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ إلغاء التحميل", callback_data="cancel_playlist")]
                ])
            )
            # أطلق التحميل في مهمة مستقلة ولا تنتظرها
            asyncio.create_task(self._download_playlist_sequential(update, context, f"https://www.youtube.com/playlist?list={playlist_id}", playlist_items, audio_only=(mode=='audio')))
            return
        else:
            await query.edit_message_text("❌ هذا الزر غير معروف أو لم يتم ربطه بعد.")

    async def _handle_cancel_download(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle download cancellation."""
        query = update.callback_query
        user_id = query.from_user.id

        if user_id in self.active_downloads:
            self.active_downloads[user_id]['cancelled'] = True
            await query.edit_message_text("❌ تم إلغاء التحميل.")
            await query.answer("تم إلغاء التحميل")
        else:
            await query.answer("لا يوجد تحميل نشط للإلغاء")

    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        if not size_bytes:
            return "غير معروف"

        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    async def _handle_download_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle download details request."""
        query = update.callback_query
        download_id = int(query.data.split("_")[-1])

        # Get download details from database
        # Implementation would fetch and display detailed download information
        await query.answer("عرض تفاصيل التحميل...")

    async def _handle_share_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle file sharing request."""
        query = update.callback_query
        download_id = int(query.data.split("_")[-1])

        # Implementation would create shareable link or send file
        await query.answer("مشاركة الملف...")

    async def _handle_delete_download(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle download deletion request."""
        query = update.callback_query
        download_id = int(query.data.split("_")[-1])

        # Implementation would delete file and update database
        await query.answer("حذف التحميل...")

    async def _handle_file_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle file details request."""
        query = update.callback_query
        file_id = int(query.data.split("_")[-1])

        # Implementation would show file details
        await query.answer("عرض تفاصيل الملف...")

    async def _handle_delete_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle file deletion request."""
        query = update.callback_query
        file_id = int(query.data.split("_")[-1])

        # Implementation would delete uploaded file
        await query.answer("حذف الملف...")

    def _extract_playlist_id(self, url):
        import re
        match = re.search(r'list=([a-zA-Z0-9_-]+)', url)
        return match.group(1) if match else None

    def _detect_platform_from_url(self, url):
        if 'youtube.com' in url or 'youtu.be' in url:
            return 'youtube'
        elif 'tiktok.com' in url:
            return 'tiktok'
        elif 'instagram.com' in url:
            return 'instagram'
        elif 'facebook.com' in url:
            return 'facebook'
        elif 'twitter.com' in url or 'x.com' in url:
            return 'twitter'
        else:
            return 'other'

    async def _show_youtube_api_playlist_menu(self, update, context, playlist_items, url, status_message, page=0):
        user_id = update.effective_user.id
        if not hasattr(self, 'last_youtube_api_playlist_info'):
            self.last_youtube_api_playlist_info = {}
        self.last_youtube_api_playlist_info[user_id] = {'items': playlist_items, 'url': url}
        short_id = self._register_url(url)
        page_size = 5
        total = len(playlist_items)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        start = page * page_size
        end = min(start + page_size, total)
        items = playlist_items[start:end]

        if total == 0:
            await status_message.edit_text(
                "❌ لم يتم العثور على أي أغاني في قائمة التشغيل (YouTube Data API).\nيرجى التأكد من صحة الرابط أو المحاولة لاحقًا.",
                parse_mode='HTML',
                reply_markup=None
            )
            return

        text = (
            f"📃 <b>قائمة التشغيل (YouTube API):</b>\n"
            f"🎶 <b>عدد الأغاني:</b> {total}\n"
            f"📄 <b>صفحة:</b> {page+1} من {total_pages}\n\n"
            f"اختر أغنية من القائمة أدناه لتصفح خيارات التحميل (رابط مباشر)، أو استخدم الأزرار بالأسفل."
        )
        keyboard = []
        for idx, item in enumerate(items, start=start):
            keyboard.append([
                InlineKeyboardButton(f"🎵 {idx+1}. {item['title']}", url=item['url'])
            ])
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"ytapi_ppg|{short_id}|{page-1}"))
        if end < total:
            nav.append(InlineKeyboardButton("التالي ➡️", callback_data=f"ytapi_ppg|{short_id}|{page+1}"))
        if nav:
            keyboard.append(nav)
        keyboard.append([InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")])
        await status_message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

