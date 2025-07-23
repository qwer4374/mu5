#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Rate Limiter Middleware
=======================

Rate limiting middleware to prevent spam and abuse.
"""

import time
import logging
from collections import defaultdict
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter to prevent spam and abuse."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60, auto_ban_threshold: int = 3, db_manager=None):
        """Initialize rate limiter with auto-ban support."""
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.user_requests = defaultdict(list)
        self.auto_ban_threshold = auto_ban_threshold
        self.user_violations = defaultdict(int)
        self.db_manager = db_manager

    async def check(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Check if user is within rate limits."""
        if not update.effective_user:
            return

        user_id = update.effective_user.id
        current_time = time.time()

        # Clean old requests
        self.user_requests[user_id] = [
            req_time for req_time in self.user_requests[user_id]
            if current_time - req_time < self.window_seconds
        ]

        # Check if user exceeded rate limit
        if len(self.user_requests[user_id]) >= self.max_requests:
            self.user_violations[user_id] += 1
            if self.user_violations[user_id] >= self.auto_ban_threshold and self.db_manager:
                await self.db_manager.ban_user(user_id)
                if update.message:
                    await update.message.reply_text("🚫 تم حظرك تلقائياً بسبب تجاوز الحد المسموح من الطلبات.")
                return

            logger.warning(f"Rate limit exceeded for user {user_id}")

            if update.message:
                await update.message.reply_text(
                    "⚠️ لقد تجاوزت الحد المسموح من الطلبات. يرجى الانتظار قليلاً قبل المحاولة مرة أخرى."
                )
            return

        # Add current request
        self.user_requests[user_id].append(current_time)

