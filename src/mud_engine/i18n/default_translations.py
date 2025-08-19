"""
기본 번역 텍스트 정의

이 파일은 시스템의 핵심 번역 텍스트를 정의합니다.
새로운 번역 키를 추가할 때는 이 파일을 수정하세요.
"""

from typing import Dict

# 기본 번역 텍스트 (최소한의 핵심 메시지만 포함)
DEFAULT_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    'en': {
        # 시스템 메시지
        'system_error': 'System error occurred.',
        'system_starting': 'System is starting...',
        'system_ready': 'System is ready.',
        'system_shutdown': 'System is shutting down.',

        # 기본 오류 메시지
        'translation_missing': 'Translation missing: {key}',
        'invalid_input': 'Invalid input.',
        'access_denied': 'Access denied.',
        'not_found': 'Not found.',

        # 최소한의 게임 메시지
        'welcome': 'Welcome!',
        'goodbye': 'Goodbye!',
        'loading': 'Loading...',
        'please_wait': 'Please wait...',
    },
    'ko': {
        # 시스템 메시지
        'system_error': '시스템 오류가 발생했습니다.',
        'system_starting': '시스템을 시작하는 중...',
        'system_ready': '시스템이 준비되었습니다.',
        'system_shutdown': '시스템을 종료하는 중...',

        # 기본 오류 메시지
        'translation_missing': '번역 누락: {key}',
        'invalid_input': '잘못된 입력입니다.',
        'access_denied': '접근이 거부되었습니다.',
        'not_found': '찾을 수 없습니다.',

        # 최소한의 게임 메시지
        'welcome': '환영합니다!',
        'goodbye': '안녕히 가세요!',
        'loading': '로딩 중...',
        'please_wait': '잠시만 기다려주세요...',
    }
}


def get_default_translations() -> Dict[str, Dict[str, str]]:
    """기본 번역 텍스트 반환"""
    return DEFAULT_TRANSLATIONS.copy()


def get_core_translation_keys() -> set:
    """핵심 번역 키 목록 반환"""
    keys = set()
    for locale_translations in DEFAULT_TRANSLATIONS.values():
        keys.update(locale_translations.keys())
    return keys


def validate_default_translations() -> Dict[str, any]:
    """기본 번역 텍스트 유효성 검사"""
    validation_result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'missing_keys': {}
    }

    # 모든 로케일에서 동일한 키를 가지고 있는지 확인
    all_keys = set()
    locale_keys = {}

    for locale, translations in DEFAULT_TRANSLATIONS.items():
        locale_keys[locale] = set(translations.keys())
        all_keys.update(translations.keys())

    # 누락된 키 확인
    for locale, keys in locale_keys.items():
        missing = all_keys - keys
        if missing:
            validation_result['missing_keys'][locale] = list(missing)
            validation_result['warnings'].append(
                f"로케일 '{locale}'에서 누락된 키: {', '.join(missing)}"
            )

    # 빈 번역 확인
    for locale, translations in DEFAULT_TRANSLATIONS.items():
        for key, value in translations.items():
            if not value or not value.strip():
                validation_result['errors'].append(
                    f"빈 번역 값: {locale}.{key}"
                )
                validation_result['valid'] = False

    return validation_result