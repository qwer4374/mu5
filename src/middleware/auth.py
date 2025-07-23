#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Authentication Middleware
=========================

Authentication and authorization middleware for the bot.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class AuthMiddleware:
    """Authentication and authorization middleware."""
    
    def __init__(self, db_manager, config):
        """Initialize auth middleware."""
        self.db = db_manager
        self.config = config
    
    async def check(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Check user authentication and authorization."""
        if not update.effective_user:
            return
        
        user_id = update.effective_user.id
        
        # Check if user is banned
        user = await self.db.get_user(user_id)
        if user and user.is_banned:
            logger.warning(f"Banned user {user_id} attempted to use bot")
            
            if update.message:
                await update.message.reply_text(
                    "❌ تم حظرك من استخدام هذا البوت. للاستفسار، تواصل مع المدير."
                )
            return
        
        # Check maintenance mode (except for owner)
        if user_id != self.config.OWNER_ID:
            # This would check maintenance mode from database
            # Implementation depends on bot_manager
            pass

