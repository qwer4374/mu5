#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Analytics Handler
=================

Handles analytics-related commands and provides insights into bot usage.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

class AnalyticsHandler:
    """Handles analytics commands and provides statistics."""

    def __init__(self, bot_manager, config, db_manager):
        """Initialize analytics handler."""
        self.bot_manager = bot_manager
        self.config = config
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)

    async def handle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.logger.info(f"[DIAG] Command Triggered: {update.message.text if update.message else ''}")
        """Handle analytics commands."""
        user_id = update.effective_user.id
        command = update.message.text.split()[0][1:]  # Remove '/'

        await self.bot_manager.register_user(update.effective_user)

        if command == 'stats':
            await self._show_bot_statistics(update, context)
        elif command == 'user_stats':
            await self._show_user_statistics(update, context)
        else:
            await update.message.reply_text("❌ أمر تحليلات غير معروف. استخدم /stats أو /user_stats.")

    async def _show_bot_statistics(self, update, context, message_object=None):
        text = "📊 إحصائيات البوت (تحت التطوير)"
        if message_object:
            await message_object.edit_text(text)
        else:
            await update.message.reply_text(text)

    async def _show_user_statistics(self, update, context, message_object=None):
        text = "📊 إحصائيات المستخدم (تحت التطوير)"
        if message_object:
            await message_object.edit_text(text)
        else:
            await update.message.reply_text(text)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.logger.info(f"[DIAG] Button Triggered: {update.callback_query.data if update.callback_query else ''}")
        query = update.callback_query
        data = query.data if query else None
        user_id = query.from_user.id if query else None
        if not query:
            return

        if data == "analytics_bot_stats":
            await self._show_bot_statistics(update, context, message_object=query.message)
        elif data == "analytics_user_stats":
            await self._show_user_statistics(update, context, message_object=query.message)
        elif data == "stats_detailed_report":
            await self._show_bot_statistics(update, context, message_object=query.message)
        elif data == "main_menu":
            await self._show_bot_statistics(update, context, message_object=query.message)
        else:
            await query.edit_message_text("❌ هذا الزر غير معروف أو لم يتم ربطه بعد.")

    def get_stats_keyboard(self):
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = [
            [InlineKeyboardButton("تقرير مفصل", callback_data="stats_detailed_report")],
            [InlineKeyboardButton("العودة", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)


