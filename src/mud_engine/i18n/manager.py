"""
다국어 지원 시스템 - I18nManager
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..database import get_database_manager

logger = logging.getLogger(__name__)


class I18nManager:
    """다국어 관리 클래스"""

    # 지원되는 로케일
    SUPPORTED_LOCALES = ['en', 'ko']
    DEFAULT_LOCALE = 'en'

    def __init__(self):
        """I18nManager 초기화"""
        self._translations: Dict[str, Dict[str, str]] = {}  # {locale: {key: value}}
        self._cache_enabled = True
        self._fallback_locale = self.DEFAULT_LOCALE

        logger.info("I18nManager 초기화")

    async def initialize(self) -> None:
        """다국어 시스템 초기화"""
        try:
            await self.load_translations()
            logger.info("다국어 시스템 초기화 완료")
        except Exception as e:
            logger.error(f"다국어 시스템 초기화 실패: {e}")
            raise

    async def load_translations(self) -> None:
        """번역 텍스트 로딩"""
        try:
            # 데이터베이스에서 번역 텍스트 로드
            await self._load_from_database()

            # 파일에서 추가 번역 텍스트 로드
            await self._load_from_files()

            logger.info(f"번역 텍스트 로딩 완료: {len(self._translations)} 로케일")

        except Exception as e:
            logger.error(f"번역 텍스트 로딩 실패: {e}")
            raise

    async def _load_from_database(self) -> None:
        """데이터베이스에서 번역 텍스트 로드"""
        try:
            db_manager = await get_database_manager()

            # translations 테이블에서 모든 번역 텍스트 조회
            query = "SELECT key, locale, value FROM translations ORDER BY key, locale"
            results = await db_manager.fetch_all(query)

            for row in results:
                key = row['key']
                locale = row['locale']
                value = row['value']

                if locale not in self._translations:
                    self._translations[locale] = {}

                self._translations[locale][key] = value

            logger.info(f"데이터베이스에서 {len(results)}개 번역 텍스트 로드")

        except Exception as e:
            logger.error(f"데이터베이스 번역 텍스트 로드 실패: {e}")
            # 데이터베이스 로드 실패 시 기본 번역 텍스트 사용
            self._load_default_translations()

    async def _load_from_files(self) -> None:
        """파일에서 번역 텍스트 로드"""
        try:
            translations_dir = Path("data/translations")

            if not translations_dir.exists():
                logger.info("번역 파일 디렉토리가 존재하지 않음")
                return

            for locale in self.SUPPORTED_LOCALES:
                locale_file = translations_dir / f"{locale}.json"

                if locale_file.exists():
                    with open(locale_file, 'r', encoding='utf-8') as f:
                        file_translations = json.load(f)

                    if locale not in self._translations:
                        self._translations[locale] = {}

                    # 파일의 번역이 데이터베이스 번역을 덮어씀
                    self._translations[locale].update(file_translations)

                    logger.info(f"파일에서 {locale} 번역 {len(file_translations)}개 로드")

        except Exception as e:
            logger.warning(f"파일 번역 텍스트 로드 실패: {e}")

    def _load_default_translations(self) -> None:
        """기본 번역 텍스트 로드 (fallback)"""
        try:
            from .default_translations import get_default_translations

            self._translations = get_default_translations()
            logger.info("기본 번역 텍스트 로드 완료")

        except ImportError as e:
            logger.error(f"기본 번역 모듈 로드 실패: {e}")
            # 최소한의 하드코딩된 번역 (비상용)
            self._translations = {
                'en': {
                    'system_error': 'System error occurred.',
                    'translation_missing': 'Translation missing: {key}',
                    'welcome': 'Welcome!'
                },
                'ko': {
                    'system_error': '시스템 오류가 발생했습니다.',
                    'translation_missing': '번역 누락: {key}',
                    'welcome': '환영합니다!'
                }
            }
            logger.warning("최소한의 비상용 번역 텍스트 사용")

    def get_text(self, key: str, locale: str = None, **kwargs) -> str:
        """
        번역 텍스트 조회

        Args:
            key: 번역 키
            locale: 로케일 (기본값: DEFAULT_LOCALE)
            **kwargs: 텍스트 포맷팅용 매개변수

        Returns:
            str: 번역된 텍스트
        """
        if locale is None:
            locale = self.DEFAULT_LOCALE

        # 지원되지 않는 로케일인 경우 기본 로케일 사용
        if locale not in self.SUPPORTED_LOCALES:
            locale = self._fallback_locale

        # 번역 텍스트 조회
        text = self._get_translation(key, locale)

        # 매개변수가 있으면 포맷팅
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError) as e:
                logger.warning(f"텍스트 포맷팅 실패 ({key}, {locale}): {e}")

        return text

    def _get_translation(self, key: str, locale: str) -> str:
        """번역 텍스트 조회 (내부 메서드)"""
        # 요청된 로케일에서 조회
        if locale in self._translations and key in self._translations[locale]:
            return self._translations[locale][key]

        # 폴백 로케일에서 조회
        if (self._fallback_locale in self._translations and
            key in self._translations[self._fallback_locale]):
            logger.debug(f"폴백 로케일 사용: {key} ({locale} -> {self._fallback_locale})")
            return self._translations[self._fallback_locale][key]

        # 번역을 찾을 수 없는 경우
        logger.warning(f"번역 텍스트를 찾을 수 없음: {key} ({locale})")
        return f"[{key}]"  # 키를 그대로 반환

    def get_supported_locales(self) -> List[str]:
        """지원되는 로케일 목록 반환"""
        return self.SUPPORTED_LOCALES.copy()

    def is_supported_locale(self, locale: str) -> bool:
        """로케일 지원 여부 확인"""
        return locale in self.SUPPORTED_LOCALES

    def set_fallback_locale(self, locale: str) -> None:
        """폴백 로케일 설정"""
        if locale in self.SUPPORTED_LOCALES:
            self._fallback_locale = locale
            logger.info(f"폴백 로케일 설정: {locale}")
        else:
            logger.warning(f"지원되지 않는 폴백 로케일: {locale}")

    async def add_translation(self, key: str, locale: str, value: str, save_to_db: bool = True) -> None:
        """
        번역 텍스트 추가

        Args:
            key: 번역 키
            locale: 로케일
            value: 번역 값
            save_to_db: 데이터베이스에 저장 여부
        """
        try:
            if locale not in self.SUPPORTED_LOCALES:
                raise ValueError(f"지원되지 않는 로케일: {locale}")

            # 메모리 캐시에 추가
            if locale not in self._translations:
                self._translations[locale] = {}

            self._translations[locale][key] = value

            # 데이터베이스에 저장
            if save_to_db:
                await self._save_translation_to_db(key, locale, value)

            logger.info(f"번역 텍스트 추가: {key} ({locale})")

        except Exception as e:
            logger.error(f"번역 텍스트 추가 실패: {e}")
            raise

    async def _save_translation_to_db(self, key: str, locale: str, value: str) -> None:
        """데이터베이스에 번역 텍스트 저장"""
        try:
            db_manager = await get_database_manager()

            # UPSERT 쿼리 (INSERT OR REPLACE)
            query = """
                INSERT OR REPLACE INTO translations (key, locale, value)
                VALUES (?, ?, ?)
            """

            await db_manager.execute(query, (key, locale, value))
            await db_manager.commit()

        except Exception as e:
            logger.error(f"데이터베이스 번역 텍스트 저장 실패: {e}")
            raise

    async def remove_translation(self, key: str, locale: str = None) -> None:
        """
        번역 텍스트 제거

        Args:
            key: 번역 키
            locale: 로케일 (None이면 모든 로케일에서 제거)
        """
        try:
            if locale:
                # 특정 로케일에서만 제거
                if locale in self._translations and key in self._translations[locale]:
                    del self._translations[locale][key]

                await self._remove_translation_from_db(key, locale)
                logger.info(f"번역 텍스트 제거: {key} ({locale})")
            else:
                # 모든 로케일에서 제거
                for loc in self._translations:
                    if key in self._translations[loc]:
                        del self._translations[loc][key]

                await self._remove_translation_from_db(key)
                logger.info(f"번역 텍스트 제거 (모든 로케일): {key}")

        except Exception as e:
            logger.error(f"번역 텍스트 제거 실패: {e}")
            raise

    async def _remove_translation_from_db(self, key: str, locale: str = None) -> None:
        """데이터베이스에서 번역 텍스트 제거"""
        try:
            db_manager = await get_database_manager()

            if locale:
                query = "DELETE FROM translations WHERE key = ? AND locale = ?"
                await db_manager.execute(query, (key, locale))
            else:
                query = "DELETE FROM translations WHERE key = ?"
                await db_manager.execute(query, (key,))

            await db_manager.commit()

        except Exception as e:
            logger.error(f"데이터베이스 번역 텍스트 제거 실패: {e}")
            raise

    def get_translation_stats(self) -> Dict[str, Any]:
        """번역 통계 정보 반환"""
        stats = {
            'supported_locales': self.SUPPORTED_LOCALES,
            'fallback_locale': self._fallback_locale,
            'total_keys': set(),
            'locale_stats': {}
        }

        for locale, translations in self._translations.items():
            stats['locale_stats'][locale] = len(translations)
            stats['total_keys'].update(translations.keys())

        stats['total_keys'] = len(stats['total_keys'])

        return stats

    async def reload_translations(self) -> None:
        """번역 텍스트 다시 로드"""
        try:
            self._translations.clear()
            await self.load_translations()
            logger.info("번역 텍스트 다시 로드 완료")
        except Exception as e:
            logger.error(f"번역 텍스트 다시 로드 실패: {e}")
            raise

    def clear_cache(self) -> None:
        """번역 캐시 초기화"""
        self._translations.clear()
        logger.info("번역 캐시 초기화 완료")


# 전역 I18nManager 인스턴스
_i18n_manager: Optional[I18nManager] = None


async def get_i18n_manager() -> I18nManager:
    """
    전역 I18nManager 인스턴스 반환

    Returns:
        I18nManager: I18nManager 인스턴스
    """
    global _i18n_manager

    if _i18n_manager is None:
        _i18n_manager = I18nManager()
        await _i18n_manager.initialize()

    return _i18n_manager


async def close_i18n_manager() -> None:
    """전역 I18nManager 종료"""
    global _i18n_manager

    if _i18n_manager:
        _i18n_manager.clear_cache()
        _i18n_manager = None
        logger.info("I18nManager 종료 완료")


# 편의 함수들
async def get_text(key: str, locale: str = None, **kwargs) -> str:
    """번역 텍스트 조회 (편의 함수)"""
    i18n = await get_i18n_manager()
    return i18n.get_text(key, locale, **kwargs)


async def add_translation(key: str, locale: str, value: str) -> None:
    """번역 텍스트 추가 (편의 함수)"""
    i18n = await get_i18n_manager()
    await i18n.add_translation(key, locale, value)