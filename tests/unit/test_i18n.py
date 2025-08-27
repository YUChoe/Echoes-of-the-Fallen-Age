"""
다국어 지원 시스템 단위 테스트
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path

import pytest

from src.mud_engine.i18n import (
    I18nManager,
    LocaleService,
    TranslationFileManager,
    create_default_translation_files,
    validate_translation_key,
    format_direction_name
)

# 테스트를 위한 모의 번역 데이터
MOCK_TRANSLATIONS = {
    "en": {
        "welcome_message": "Welcome to the MUD Engine!",
        "say_format": "{player} says: {message}",
    },
    "ko": {
        "welcome_message": "MUD 엔진에 오신 것을 환영합니다!",
        "say_format": "{player}님이 말합니다: {message}",
    },
}

@pytest.fixture
def i18n_manager_with_data() -> I18nManager:
    """테스트용 번역 데이터가 채워진 I18nManager 픽스처"""
    manager = I18nManager()
    # 내부 _translations 속성에 모의 데이터를 직접 주입
    manager._translations = MOCK_TRANSLATIONS
    return manager


class TestI18nManager:
    """I18nManager 테스트"""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """I18nManager 초기화 테스트"""
        manager = I18nManager()

        assert manager.SUPPORTED_LOCALES == ['en', 'ko']
        assert manager.DEFAULT_LOCALE == 'en'
        assert manager._fallback_locale == 'en'

    def test_get_text_basic(self, i18n_manager_with_data: I18nManager):
        """기본 텍스트 조회 테스트"""
        manager = i18n_manager_with_data

        # 영어 텍스트 조회
        text_en = manager.get_text('welcome_message', 'en')
        assert text_en == 'Welcome to the MUD Engine!'

        # 한국어 텍스트 조회
        text_ko = manager.get_text('welcome_message', 'ko')
        assert text_ko == 'MUD 엔진에 오신 것을 환영합니다!'

    def test_get_text_with_formatting(self, i18n_manager_with_data: I18nManager):
        """포맷팅이 있는 텍스트 조회 테스트"""
        manager = i18n_manager_with_data

        # 매개변수 포맷팅
        text = manager.get_text('say_format', 'en', player='Alice', message='Hello')
        assert text == 'Alice says: Hello'

        text_ko = manager.get_text('say_format', 'ko', player='앨리스', message='안녕하세요')
        assert text_ko == '앨리스님이 말합니다: 안녕하세요'

    def test_get_text_fallback(self, i18n_manager_with_data: I18nManager):
        """폴백 로케일 테스트"""
        manager = i18n_manager_with_data

        # 지원되지 않는 로케일 -> 폴백 로케일 사용
        text = manager.get_text('welcome_message', 'fr')
        assert text == 'Welcome to the MUD Engine!'  # 영어 폴백

    def test_get_text_missing_key(self, i18n_manager_with_data: I18nManager):
        """존재하지 않는 키 테스트"""
        manager = i18n_manager_with_data

        # 존재하지 않는 키
        text = manager.get_text('nonexistent_key', 'en')
        assert text == '[nonexistent_key]'

    def test_supported_locales(self):
        """지원 로케일 테스트"""
        manager = I18nManager()

        locales = manager.get_supported_locales()
        assert locales == ['en', 'ko']

        assert manager.is_supported_locale('en')
        assert manager.is_supported_locale('ko')
        assert not manager.is_supported_locale('fr')

    def test_fallback_locale(self):
        """폴백 로케일 설정 테스트"""
        manager = I18nManager()

        # 유효한 폴백 로케일 설정
        manager.set_fallback_locale('ko')
        assert manager._fallback_locale == 'ko'

        # 무효한 폴백 로케일 설정 (변경되지 않음)
        manager.set_fallback_locale('fr')
        assert manager._fallback_locale == 'ko'

    def test_translation_stats(self, i18n_manager_with_data: I18nManager):
        """번역 통계 테스트"""
        manager = i18n_manager_with_data
        stats = manager.get_translation_stats()

        assert stats['supported_locales'] == ['en', 'ko']
        assert stats['fallback_locale'] == 'en'
        assert stats['total_keys'] == 2
        assert 'en' in stats['locale_stats']
        assert 'ko' in stats['locale_stats']


class TestLocaleService:
    """LocaleService 테스트"""

    def test_user_locale_management(self):
        """사용자 로케일 관리 테스트"""
        service = LocaleService()

        # 사용자 로케일 설정
        success = service.set_user_locale('user1', 'ko')
        assert success is True

        # 사용자 로케일 조회
        locale = service.get_user_locale('user1')
        assert locale == 'ko'

        # 존재하지 않는 사용자 (기본값 반환)
        locale = service.get_user_locale('user2', 'en')
        assert locale == 'en'

    def test_session_locale_management(self):
        """세션 로케일 관리 테스트"""
        service = LocaleService()

        # 세션 로케일 설정
        success = service.set_session_locale('session1', 'ko')
        assert success is True

        # 세션 로케일 조회
        locale = service.get_session_locale('session1')
        assert locale == 'ko'

    def test_invalid_locale(self):
        """무효한 로케일 테스트"""
        service = LocaleService()

        # 지원되지 않는 로케일 설정 시도
        success = service.set_user_locale('user1', 'fr')
        assert success is False

        success = service.set_session_locale('session1', 'fr')
        assert success is False

    def test_locale_removal(self):
        """로케일 제거 테스트"""
        service = LocaleService()

        # 로케일 설정
        service.set_user_locale('user1', 'ko')
        service.set_session_locale('session1', 'ko')

        # 로케일 제거
        service.remove_user_locale('user1')
        service.remove_session_locale('session1')

        # 기본값 반환 확인
        assert service.get_user_locale('user1') == 'en'
        assert service.get_session_locale('session1') == 'en'

    def test_locale_stats(self):
        """로케일 통계 테스트"""
        service = LocaleService()

        # 여러 사용자/세션 설정
        service.set_user_locale('user1', 'en')
        service.set_user_locale('user2', 'ko')
        service.set_session_locale('session1', 'en')
        service.set_session_locale('session2', 'ko')

        stats = service.get_locale_stats()

        assert stats['users_en'] == 1
        assert stats['users_ko'] == 1
        assert stats['sessions_en'] == 1
        assert stats['sessions_ko'] == 1
        assert stats['total_users'] == 2
        assert stats['total_sessions'] == 2


class TestTranslationFileManager:
    """TranslationFileManager 테스트"""

    def test_file_creation_and_loading(self):
        """파일 생성 및 로딩 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = TranslationFileManager(temp_dir)

            # 번역 파일 생성
            translations = {
                'hello': 'Hello',
                'goodbye': 'Goodbye'
            }

            success = manager.create_translation_file('en', translations)
            assert success is True

            # 파일 존재 확인
            file_path = Path(temp_dir) / 'en.json'
            assert file_path.exists()

            # 파일 로딩
            loaded = manager.load_translation_file('en')
            assert loaded == translations

    def test_file_update(self):
        """파일 업데이트 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = TranslationFileManager(temp_dir)

            # 초기 번역 생성
            manager.create_translation_file('en', {'hello': 'Hello'})

            # 번역 업데이트
            success = manager.update_translation_file('en', 'goodbye', 'Goodbye')
            assert success is True

            # 업데이트 확인
            loaded = manager.load_translation_file('en')
            assert loaded['hello'] == 'Hello'
            assert loaded['goodbye'] == 'Goodbye'

    def test_key_removal(self):
        """키 제거 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = TranslationFileManager(temp_dir)

            # 번역 생성
            translations = {'hello': 'Hello', 'goodbye': 'Goodbye'}
            manager.create_translation_file('en', translations)

            # 키 제거
            success = manager.remove_translation_from_file('en', 'goodbye')
            assert success is True

            # 제거 확인
            loaded = manager.load_translation_file('en')
            assert 'hello' in loaded
            assert 'goodbye' not in loaded

    def test_available_locales(self):
        """사용 가능한 로케일 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = TranslationFileManager(temp_dir)

            # 여러 로케일 파일 생성
            manager.create_translation_file('en', {'hello': 'Hello'})
            manager.create_translation_file('ko', {'hello': '안녕하세요'})
            manager.create_translation_file('fr', {'hello': 'Bonjour'})

            locales = manager.get_available_locales()
            assert sorted(locales) == ['en', 'fr', 'ko']

    def test_file_stats(self):
        """파일 통계 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = TranslationFileManager(temp_dir)

            translations = {'hello': 'Hello', 'goodbye': 'Goodbye'}
            manager.create_translation_file('en', translations)

            stats = manager.get_file_stats('en')

            assert stats is not None
            assert stats['locale'] == 'en'
            assert stats['total_keys'] == 2
            assert 'hello' in stats['keys']
            assert 'goodbye' in stats['keys']

    def test_validation(self):
        """번역 파일 유효성 검사 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = TranslationFileManager(temp_dir)

            # 완전한 번역 파일들
            manager.create_translation_file('en', {'hello': 'Hello', 'goodbye': 'Goodbye'})
            manager.create_translation_file('ko', {'hello': '안녕하세요', 'goodbye': '안녕히 가세요'})

            validation = manager.validate_translation_files()

            assert validation['valid'] is True
            assert len(validation['errors']) == 0
            assert len(validation['missing_keys']) == 0

            # 불완전한 번역 파일 (누락된 키)
            manager.create_translation_file('fr', {'hello': 'Bonjour'})  # goodbye 누락

            validation = manager.validate_translation_files()

            assert 'fr' in validation['missing_keys']
            assert 'goodbye' in validation['missing_keys']['fr']


class TestUtilityFunctions:
    """유틸리티 함수 테스트"""

    def test_validate_translation_key(self):
        """번역 키 유효성 검사 테스트"""
        # 유효한 키들
        assert validate_translation_key('hello') is True
        assert validate_translation_key('welcome_message') is True
        assert validate_translation_key('test123') is True

        # 무효한 키들
        assert validate_translation_key('') is False
        assert validate_translation_key('hello world') is False  # 공백
        assert validate_translation_key('hello-world') is False  # 하이픈
        assert validate_translation_key('hello.world') is False  # 점
        assert validate_translation_key(None) is False
        assert validate_translation_key(123) is False

    def test_format_direction_name(self):
        """방향 이름 포맷팅 테스트"""
        # 영어
        assert format_direction_name('north', 'en') == 'north'
        assert format_direction_name('south', 'en') == 'south'

        # 한국어
        assert format_direction_name('north', 'ko') == '북쪽'
        assert format_direction_name('south', 'ko') == '남쪽'

        # 존재하지 않는 방향 (원본 반환)
        assert format_direction_name('unknown', 'en') == 'unknown'
        assert format_direction_name('unknown', 'ko') == 'unknown'

    def test_create_default_translation_files(self):
        """기본 번역 파일 생성 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 임시 디렉토리로 변경
            original_cwd = os.getcwd()
            os.chdir(temp_dir)

            try:
                success = create_default_translation_files()
                assert success is True

                # 파일 존재 확인
                en_file = Path('data/translations/en.json')
                ko_file = Path('data/translations/ko.json')

                assert en_file.exists()
                assert ko_file.exists()

                # 내용 확인
                with open(en_file, 'r', encoding='utf-8') as f:
                    en_data = json.load(f)

                with open(ko_file, 'r', encoding='utf-8') as f:
                    ko_data = json.load(f)

                assert 'welcome_message' in en_data
                assert 'welcome_message' in ko_data
                assert en_data['welcome_message'] != ko_data['welcome_message']

            finally:
                os.chdir(original_cwd)


if __name__ == "__main__":
    # 간단한 테스트 실행
    async def run_basic_test():
        print("🧪 다국어 지원 시스템 기본 테스트 실행...")

        try:
            # I18nManager 테스트
            manager = I18nManager()
            manager._load_default_translations()

            text_en = manager.get_text('welcome_message', 'en')
            text_ko = manager.get_text('welcome_message', 'ko')

            print(f"✅ 영어 텍스트: {text_en}")
            print(f"✅ 한국어 텍스트: {text_ko}")

            # LocaleService 테스트
            service = LocaleService()
            service.set_user_locale('user1', 'ko')

            locale = service.get_user_locale('user1')
            print(f"✅ 사용자 로케일: {locale}")

            # TranslationFileManager 테스트
            with tempfile.TemporaryDirectory() as temp_dir:
                file_manager = TranslationFileManager(temp_dir)
                success = file_manager.create_translation_file('test', {'hello': 'Hello'})
                print(f"✅ 번역 파일 생성: {'성공' if success else '실패'}")

            # 유틸리티 함수 테스트
            valid_key = validate_translation_key('test_key')
            direction = format_direction_name('north', 'ko')

            print(f"✅ 키 유효성: {'유효' if valid_key else '무효'}")
            print(f"✅ 방향 포맷팅: {direction}")

            print("🎉 모든 기본 테스트 통과!")

        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            raise

    asyncio.run(run_basic_test())