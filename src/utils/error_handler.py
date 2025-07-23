#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Error Handler
=============

Comprehensive error handling system for the Telegram bot.
"""

import logging
import traceback
from telegram import Update
from telegram.ext import ContextTypes
from config import Config  # Import Config at the top

logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the bot."""
    
    # Log the error
    logger.error(f"Exception while handling an update: {context.error}")
    logger.error(f"Update: {update}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Try to send error message to user
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى لاحقاً."
            )
        except Exception as e:
            logger.error(f"Failed to send error message to user: {e}")
    
    # Notify admin about critical errors
    if context.error and "CRITICAL" in str(context.error).upper():
        try:
            await context.bot.send_message(
                chat_id=Config.OWNER_ID,
                text=f"🚨 خطأ حرج في البوت:\n\n{str(context.error)[:1000]}"
            )
        except Exception as e:
            logger.error(f"Failed to notify admin about critical error: {e}")

