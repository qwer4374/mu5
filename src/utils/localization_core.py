import importlib
import importlib.util
import os
import sys
import logging

LANG_DIR = os.path.dirname(__file__)
_language_cache = {}

logger = logging.getLogger(__name__)

def _load_translation_module(lang):
    """حاول تحميل ملف الترجمة كـ module بأي طريقة متاحة (importlib أو من المسار)."""
    # 1. حاول الاستيراد الديناميكي (مناسب إذا شغلت من src أو من الجذر)
    try:
        return importlib.import_module(f'src.utils.localization.{lang}')
    except ModuleNotFoundError:
        try:
            return importlib.import_module(f'.{lang}', package=__package__)
        except ModuleNotFoundError:
            # 2. fallback: تحميل من المسار الفعلي مباشرة
            lang_path = os.path.join(LANG_DIR, f'{lang}.py')
            if os.path.exists(lang_path):
                spec = importlib.util.spec_from_file_location(f'localization_{lang}', lang_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module
    return None

def get_text(key, lang='ar', **kwargs):
    """استرجاع النص المناسب للغة المطلوبة من ملف منفصل مع دعم التهيئة وبيئات التشغيل المختلفة."""
    if lang not in _language_cache:
        module = _load_translation_module(lang)
        if module:
            _language_cache[lang] = getattr(module, 'translations', {})
        else:
            logger.warning(f"[localization] Failed to import language '{lang}' by all methods.")
            _language_cache[lang] = {}
    # تأكد من تحميل العربية دائماً كـ fallback
    if 'ar' not in _language_cache:
        module = _load_translation_module('ar')
        if module:
            _language_cache['ar'] = getattr(module, 'translations', {})
        else:
            logger.error(f"[localization] Failed to import fallback Arabic by all methods.")
            _language_cache['ar'] = {}
    text = _language_cache[lang].get(key) or _language_cache['ar'].get(key) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
