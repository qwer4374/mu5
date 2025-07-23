#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Advanced Logger
===============

Comprehensive logging system with file rotation, colored output,
and structured logging for the Telegram bot.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        """Format log record with colors."""
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset_color = self.COLORS['RESET']
        
        # Add color to level name
        record.levelname = f"{log_color}{record.levelname}{reset_color}"
        
        return super().format(record)

class AdvancedLogger:
    """Advanced logging system with multiple handlers and formatters."""
    
    def __init__(self, name: str = "AdvancedTelegramBot", log_dir: str = "data/logs"):
        """Initialize the advanced logger."""
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Setup handlers
        self._setup_console_handler()
        self._setup_file_handler()
        self._setup_error_handler()
        
    def _setup_console_handler(self):
        """Setup colored console handler."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Colored formatter for console
        console_formatter = ColoredFormatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
    
    def _setup_file_handler(self):
        """Setup rotating file handler for all logs."""
        log_file = self.log_dir / "bot.log"
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Detailed formatter for file
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
    
    def _setup_error_handler(self):
        """Setup separate handler for errors and critical logs."""
        error_file = self.log_dir / "errors.log"
        
        error_handler = logging.handlers.RotatingFileHandler(
            error_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        
        # Detailed formatter for errors
        error_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s\n'
            'Exception: %(exc_info)s\n' + '-' * 80,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        error_handler.setFormatter(error_formatter)
        self.logger.addHandler(error_handler)
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger."""
        return self.logger

def setup_logging(log_level: str = "INFO", log_dir: str = "data/logs") -> logging.Logger:
    """Setup and configure logging for the bot."""
    
    # Create log directory
    Path(log_dir).mkdir(parents=True, exist_ok=True)    
    # Set log level from environment or parameter
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create advanced logger
    advanced_logger = AdvancedLogger("AdvancedTelegramBot", log_dir)
    logger = advanced_logger.get_logger()
    logger.setLevel(level)
    
    # Log startup message
    logger.info("🚀 Advanced Telegram Bot Logger initialized")
    logger.info(f"📁 Log directory: {log_dir}")
    logger.info(f"📊 Log level: {log_level}")
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)

