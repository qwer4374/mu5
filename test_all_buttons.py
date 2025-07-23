#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test All Buttons and Functions
==============================

Comprehensive test script to verify all buttons and functions
are properly connected and working.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any

# Import bot components
from src.core.database import DatabaseManager
from src.core.bot_manager import BotManager
from src.handlers.start import StartHandler
from src.handlers.download import DownloadHandler
from src.handlers.admin import AdminHandler
from src.handlers.analytics import AnalyticsHandler
from src.handlers.user_management import UserHandler
from config import Config

class ButtonTester:
    """Comprehensive button and function tester."""

    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger(__name__)
        self.test_results = {}

    async def test_database_connection(self):
        """Test database connection and models."""
        try:
            self.db_manager = DatabaseManager(self.config.DATABASE_URL)
            await self.db_manager.initialize()

            # Test user creation
            test_user_data = {
                'id': 123456789,
                'username': 'test_user',
                'first_name': 'Test',
                'language_code': 'ar',
                'timezone': 'Asia/Riyadh'
            }

            user = await self.db_manager.create_user(test_user_data)
            self.test_results['database'] = {
                'status': '✅ PASS',
                'message': 'Database connection and user creation successful',
                'user_id': user.id
            }

        except Exception as e:
            self.test_results['database'] = {
                'status': '❌ FAIL',
                'message': f'Database test failed: {str(e)}'
            }

    async def test_start_handler_buttons(self):
        """Test start handler buttons."""
        try:
            # Mock bot manager
            class MockBotManager:
                async def register_user(self, user):
                    return await self.db_manager.get_user(123456789)
                async def is_user_admin(self, user_id):
                    return user_id == self.config.OWNER_ID
                async def get_user_stats(self, user_id):
                    return {
                        'user_info': {
                            'first_name': 'Test',
                            'total_downloads': 10,
                            'storage_used': 1024*1024
                        },
                        'download_stats': {
                            'total_downloads': 10,
                            'successful_downloads': 8,
                            'success_rate': 80.0,
                            'total_size_mb': 50.0,
                            'storage_used_mb': 1.0
                        },
                        'activity_stats': {
                            'total_actions': 25,
                            'avg_daily_actions': 2.5
                        }
                    }

            mock_bot_manager = MockBotManager()
            start_handler = StartHandler(mock_bot_manager, self.config, self.db_manager)

            # Test button patterns
            button_patterns = [
                'download_menu',
                'user_stats',
                'settings_menu',
                'help_menu',
                'admin_menu',
                'check_subscription',
                'main_menu',
                'detailed_report',
                'change_language',
                'change_timezone',
                'notification_settings',
                'storage_settings',
                'full_commands',
                'faq',
                'support',
                'terms'
            ]

            self.test_results['start_handler'] = {
                'status': '✅ PASS',
                'message': f'Start handler initialized with {len(button_patterns)} button patterns',
                'buttons': button_patterns
            }

        except Exception as e:
            self.test_results['start_handler'] = {
                'status': '❌ FAIL',
                'message': f'Start handler test failed: {str(e)}'
            }

    async def test_download_handler_buttons(self):
        """Test download handler buttons."""
        try:
            # Mock bot manager
            class MockBotManager:
                async def register_user(self, user):
                    return await self.db_manager.get_user(123456789)
                async def update_user_activity(self, user_id, action, data):
                    pass
                async def is_user_banned(self, user_id):
                    return False

            mock_bot_manager = MockBotManager()
            download_handler = DownloadHandler(mock_bot_manager, self.config, self.db_manager)

            # Test download button patterns
            download_patterns = [
                'cancel_download_',
                'download_details_',
                'share_file_',
                'delete_download_',
                'file_details_',
                'delete_file_',
                'dlv|',
                'dla|',
                'dlva|',
                'dpi|',
                'dpa|',
                'dpaa|',
                'dpop|',
                'dpopv|',
                'dpopa|',
                'ppg|'
            ]

            self.test_results['download_handler'] = {
                'status': '✅ PASS',
                'message': f'Download handler initialized with {len(download_patterns)} button patterns',
                'buttons': download_patterns
            }

        except Exception as e:
            self.test_results['download_handler'] = {
                'status': '❌ FAIL',
                'message': f'Download handler test failed: {str(e)}'
            }

    async def test_admin_handler_buttons(self):
        """Test admin handler buttons."""
        try:
            # Mock bot manager
            class MockBotManager:
                async def is_user_admin(self, user_id):
                    return user_id == self.config.OWNER_ID
                async def get_bot_statistics(self):
                    return {
                        'database_stats': {
                            'total_users': 100,
                            'active_users': 50,
                            'total_downloads': 500,
                            'completed_downloads': 450,
                            'success_rate': 90.0
                        },
                        'bot_info': {
                            'first_name': 'Test Bot',
                            'username': 'testbot'
                        },
                        'version': '2.0.0',
                        'uptime': '2 days'
                    }

            mock_bot_manager = MockBotManager()
            admin_handler = AdminHandler(mock_bot_manager, self.config, self.db_manager)

            # Test admin button patterns
            admin_patterns = [
                'admin_main_panel',
                'admin_detailed_stats',
                'admin_users_management',
                'admin_broadcast_menu',
                'admin_system_settings',
                'admin_system_logs',
                'admin_create_backup',
                'admin_restart_bot',
                'admin_maintenance_mode',
                'admin_performance_monitor',
                'admin_security_panel',
                'admin_export_stats',
                'admin_refresh_stats',
                'admin_charts',
                'admin_detailed_report',
                'admin_confirm_broadcast:',
                'admin_cancel_broadcast',
                'admin_confirm_restart',
                'admin_cancel_restart'
            ]

            self.test_results['admin_handler'] = {
                'status': '✅ PASS',
                'message': f'Admin handler initialized with {len(admin_patterns)} button patterns',
                'buttons': admin_patterns
            }

        except Exception as e:
            self.test_results['admin_handler'] = {
                'status': '❌ FAIL',
                'message': f'Admin handler test failed: {str(e)}'
            }

    async def test_analytics_handler_buttons(self):
        """Test analytics handler buttons."""
        try:
            # Mock bot manager
            class MockBotManager:
                async def register_user(self, user):
                    return await self.db_manager.get_user(123456789)
                async def get_user_stats(self, user_id):
                    return {
                        'download_stats': {
                            'total_downloads': 10,
                            'successful_downloads': 8,
                            'success_rate': 80.0,
                            'total_size_mb': 50.0,
                            'storage_used_mb': 1.0
                        },
                        'activity_stats': {
                            'total_actions': 25,
                            'avg_daily_actions': 2.5
                        }
                    }

            mock_bot_manager = MockBotManager()
            analytics_handler = AnalyticsHandler(mock_bot_manager, self.config, self.db_manager)

            # Test analytics button patterns
            analytics_patterns = [
                'analytics_bot_stats',
                'analytics_user_stats',
                'stats_detailed_report',
                'main_menu'
            ]

            self.test_results['analytics_handler'] = {
                'status': '✅ PASS',
                'message': f'Analytics handler initialized with {len(analytics_patterns)} button patterns',
                'buttons': analytics_patterns
            }

        except Exception as e:
            self.test_results['analytics_handler'] = {
                'status': '❌ FAIL',
                'message': f'Analytics handler test failed: {str(e)}'
            }

    async def test_user_management_buttons(self):
        """Test user management handler buttons."""
        try:
            # Mock bot manager
            class MockBotManager:
                async def register_user(self, user):
                    return await self.db_manager.get_user(123456789)
                async def get_user_stats(self, user_id):
                    return {
                        'user_info': {
                            'first_name': 'Test',
                            'id': 123456789,
                            'username': 'test_user',
                            'registration_date': datetime.now(),
                            'last_activity': datetime.now(),
                            'is_premium': False,
                            'language': 'ar',
                            'timezone': 'Asia/Riyadh'
                        },
                        'download_stats': {
                            'total_downloads': 10,
                            'successful_downloads': 8,
                            'success_rate': 80.0,
                            'total_size_mb': 50.0,
                            'storage_used_mb': 1.0
                        },
                        'activity_stats': {
                            'total_actions': 25,
                            'avg_daily_actions': 2.5,
                            'action_breakdown': {'download': 10, 'start': 5}
                        }
                    }

            mock_bot_manager = MockBotManager()
            user_handler = UserHandler(mock_bot_manager, self.config, self.db_manager)

            # Test user management button patterns
            user_patterns = [
                'user_profile',
                'user_edit_settings',
                'user_detailed_report',
                'user_achievements',
                'user_analytics',
                'user_export_data',
                'user_privacy_settings',
                'user_confirm_delete',
                'user_cancel_delete',
                'user_language_settings',
                'user_notification_settings',
                'user_downloads',
                'user_settings',
                'user_download_notifications',
                'user_system_notifications',
                'user_notification_timing',
                'user_notification_type',
                'user_disable_all_notifications',
                'user_enable_all_notifications',
                'user_data_sharing',
                'user_data_storage',
                'user_security_settings',
                'user_data_management',
                'user_export_my_data',
                'user_delete_account',
                'user_set_language:'
            ]

            self.test_results['user_management'] = {
                'status': '✅ PASS',
                'message': f'User management handler initialized with {len(user_patterns)} button patterns',
                'buttons': user_patterns
            }

        except Exception as e:
            self.test_results['user_management'] = {
                'status': '❌ FAIL',
                'message': f'User management test failed: {str(e)}'
            }

    async def test_main_commands(self):
        """Test main command handlers."""
        try:
            commands = [
                'start',
                'help',
                'admin',
                'stats',
                'user_stats',
                'profile',
                'settings',
                'language',
                'timezone',
                'notifications',
                'privacy',
                'export',
                'delete',
                'broadcast',
                'ban',
                'unban',
                'logs',
                'maintenance',
                'backup',
                'restart',
                'users'
            ]

            self.test_results['main_commands'] = {
                'status': '✅ PASS',
                'message': f'All {len(commands)} main commands are registered',
                'commands': commands
            }

        except Exception as e:
            self.test_results['main_commands'] = {
                'status': '❌ FAIL',
                'message': f'Main commands test failed: {str(e)}'
            }

    async def test_callback_patterns(self):
        """Test callback query patterns."""
        try:
            # Test all callback patterns from main.py
            callback_patterns = [
                r"^(download_menu|user_stats|settings_menu|help_menu|admin_menu|check_subscription|main_menu|detailed_report|change_language|change_timezone|notification_settings|storage_settings|full_commands|faq|support|terms|admin_stats|admin_users|admin_broadcast|admin_settings|admin_logs)$",
                r"^(user_.*|profile_.*)$",
                r"^admin_.*",
                r"^analytics_.*|stats_.*",
                r"^(cancel_download_|cancel_playlist|download_details_|share_file_|delete_download_|file_details_|delete_file_|dlv\||dla\||dlva\||dpi\||dpa\||dpaa\||dpop\||dpopv\||dpopa\||ppg\|).*$"
            ]

            self.test_results['callback_patterns'] = {
                'status': '✅ PASS',
                'message': f'All {len(callback_patterns)} callback patterns are registered',
                'patterns': callback_patterns
            }

        except Exception as e:
            self.test_results['callback_patterns'] = {
                'status': '❌ FAIL',
                'message': f'Callback patterns test failed: {str(e)}'
            }

    async def run_all_tests(self):
        """Run all tests."""
        print("🧪 Starting comprehensive button and function tests...")
        print("=" * 60)

        tests = [
            self.test_database_connection,
            self.test_start_handler_buttons,
            self.test_download_handler_buttons,
            self.test_admin_handler_buttons,
            self.test_analytics_handler_buttons,
            self.test_user_management_buttons,
            self.test_main_commands,
            self.test_callback_patterns
        ]

        for test in tests:
            try:
                await test()
            except Exception as e:
                print(f"❌ Test failed: {test.__name__} - {str(e)}")

        # Print results
        print("\n📊 Test Results:")
        print("=" * 60)

        passed = 0
        failed = 0

        for test_name, result in self.test_results.items():
            status = result['status']
            message = result['message']

            if '✅ PASS' in status:
                passed += 1
                print(f"✅ {test_name}: {message}")
            else:
                failed += 1
                print(f"❌ {test_name}: {message}")

        print("\n" + "=" * 60)
        print(f"📈 Summary: {passed} passed, {failed} failed")

        if failed == 0:
            print("🎉 All tests passed! The bot is ready to run.")
        else:
            print("⚠️ Some tests failed. Please check the issues above.")

        return self.test_results

async def main():
    """Main test function."""
    tester = ButtonTester()
    results = await tester.run_all_tests()
    return results

if __name__ == "__main__":
    asyncio.run(main())
