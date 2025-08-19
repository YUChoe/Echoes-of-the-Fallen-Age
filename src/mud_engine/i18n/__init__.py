"""
다국어 지원 모듈

영어/한국어 지원 및 번역 텍스트 관리 기능을 제공합니다.
"""

from .manager import I18nManager, get_i18n_manager, close_i18n_manager, get_text, add_translation
from .locale_service import LocaleService, get_locale_service, close_locale_service, set_user_locale, get_user_locale, get_text_for_user
from .utils import TranslationFileManager, create_default_translation_files, validate_translation_key, format_direction_name

__all__ = [
    # 매니저
    'I18nManager',
    'get_i18n_manager',
    'close_i18n_manager',
    'get_text',
    'add_translation',

    # 로케일 서비스
    'LocaleService',
    'get_locale_service',
    'close_locale_service',
    'set_user_locale',
    'get_user_locale',
    'get_text_for_user',

    # 유틸리티
    'TranslationFileManager',
    'create_default_translation_files',
    'validate_translation_key',
    'format_direction_name'
]