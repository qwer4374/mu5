import pytest
from src.utils.localization_core import get_text

ALL_LANGS = ['ar', 'en', 'fr', 'es', 'de', 'ru']

@pytest.mark.parametrize("lang", ALL_LANGS)
def test_main_menu_translations(lang):
    # تحقق من وجود نصوص القوائم الرئيسية في كل لغة
    assert get_text('msg_welcome', lang) != 'msg_welcome'
    assert get_text('button_download_menu', lang) != 'button_download_menu'
    assert get_text('button_user_stats', lang) != 'button_user_stats'
    assert get_text('button_settings', lang) != 'button_settings'
    assert get_text('button_admin_panel', lang) != 'button_admin_panel'
    assert get_text('button_help', lang) != 'button_help'
    assert get_text('button_check_subscription', lang) != 'button_check_subscription'

@pytest.mark.parametrize("lang", ALL_LANGS)
def test_settings_menu_translations(lang):
    assert get_text('msg_settings', lang) != 'msg_settings'
    assert get_text('button_language_ar', lang) != 'button_language_ar'
    assert get_text('button_timezone', lang) != 'button_timezone'
    assert get_text('button_notifications', lang) != 'button_notifications'
    assert get_text('button_back', lang) != 'button_back'

@pytest.mark.parametrize("lang", ALL_LANGS)
def test_admin_panel_translations(lang):
    assert get_text('msg_admin_panel', lang) != 'msg_admin_panel'
    assert get_text('button_detailed_stats', lang) != 'button_detailed_stats'
    assert get_text('button_users_management', lang) != 'button_users_management'
    assert get_text('button_broadcast_menu', lang) != 'button_broadcast_menu'
    assert get_text('button_system_settings', lang) != 'button_system_settings'
    assert get_text('button_system_logs', lang) != 'button_system_logs'
    assert get_text('button_create_backup', lang) != 'button_create_backup'
    assert get_text('button_restart_bot', lang) != 'button_restart_bot'
    assert get_text('button_maintenance_mode', lang) != 'button_maintenance_mode'
    assert get_text('button_performance_monitor', lang) != 'button_performance_monitor'
    assert get_text('button_security_panel', lang) != 'button_security_panel'

@pytest.mark.parametrize("lang", ALL_LANGS)
def test_error_messages_translations(lang):
    assert get_text('error_unknown_command', lang) != 'error_unknown_command'
    assert get_text('error_access_denied', lang) != 'error_access_denied'
    assert get_text('error_critical', lang) != 'error_critical'
    assert get_text('error_try_again', lang) != 'error_try_again'

@pytest.mark.parametrize("lang", ALL_LANGS)
def test_download_flow_translations(lang):
    assert get_text('msg_download_menu', lang) != 'msg_download_menu'
    assert get_text('button_download_history', lang) != 'button_download_history'
    assert get_text('button_download_new', lang) != 'button_download_new'
    assert get_text('msg_download_failed', lang) != 'msg_download_failed'
    assert get_text('msg_download_complete', lang) != 'msg_download_complete'

# يمكن إضافة اختبارات أكثر تفصيلاً لكل سيناريو أو زر أو رسالة حسب الحاجة
