"""
로케일 서비스 - 사용자별 로케일 관리
"""

import logging
from typing import Dict, Optional

from .manager import get_i18n_manager

logger = logging.getLogger(__name__)


class LocaleService:
    """로케일 서비스 클래스"""

    def __init__(self):
        """LocaleService 초기화"""
        self._user_locales: Dict[str, str] = {}  # {user_id: locale}
        self._session_locales: Dict[str, str] = {}  # {session_id: locale}

        logger.info("LocaleService 초기화")

    def set_user_locale(self, user_id: str, locale: str) -> bool:
        """
        사용자 로케일 설정

        Args:
            user_id: 사용자 ID
            locale: 로케일

        Returns:
            bool: 설정 성공 여부
        """
        try:
            # 지원되는 로케일인지 확인
            if not self._is_valid_locale(locale):
                logger.warning(f"지원되지 않는 로케일: {locale}")
                return False

            self._user_locales[user_id] = locale
            logger.info(f"사용자 로케일 설정: {user_id} -> {locale}")
            return True

        except Exception as e:
            logger.error(f"사용자 로케일 설정 실패: {e}")
            return False

    def get_user_locale(self, user_id: str, default: str = 'en') -> str:
        """
        사용자 로케일 조회

        Args:
            user_id: 사용자 ID
            default: 기본 로케일

        Returns:
            str: 사용자 로케일
        """
        return self._user_locales.get(user_id, default)

    def set_session_locale(self, session_id: str, locale: str) -> bool:
        """
        세션 로케일 설정

        Args:
            session_id: 세션 ID
            locale: 로케일

        Returns:
            bool: 설정 성공 여부
        """
        try:
            if not self._is_valid_locale(locale):
                logger.warning(f"지원되지 않는 로케일: {locale}")
                return False

            self._session_locales[session_id] = locale
            logger.debug(f"세션 로케일 설정: {session_id} -> {locale}")
            return True

        except Exception as e:
            logger.error(f"세션 로케일 설정 실패: {e}")
            return False

    def get_session_locale(self, session_id: str, default: str = 'en') -> str:
        """
        세션 로케일 조회

        Args:
            session_id: 세션 ID
            default: 기본 로케일

        Returns:
            str: 세션 로케일
        """
        return self._session_locales.get(session_id, default)

    def remove_user_locale(self, user_id: str) -> None:
        """사용자 로케일 제거"""
        if user_id in self._user_locales:
            del self._user_locales[user_id]
            logger.info(f"사용자 로케일 제거: {user_id}")

    def remove_session_locale(self, session_id: str) -> None:
        """세션 로케일 제거"""
        if session_id in self._session_locales:
            del self._session_locales[session_id]
            logger.debug(f"세션 로케일 제거: {session_id}")

    def _is_valid_locale(self, locale: str) -> bool:
        """로케일 유효성 검사"""
        # I18nManager의 지원 로케일과 동기화
        supported_locales = ['en', 'ko']  # 하드코딩 대신 I18nManager에서 가져올 수도 있음
        return locale in supported_locales

    async def get_text_for_user(self, user_id: str, key: str, **kwargs) -> str:
        """
        사용자별 번역 텍스트 조회

        Args:
            user_id: 사용자 ID
            key: 번역 키
            **kwargs: 포맷팅 매개변수

        Returns:
            str: 번역된 텍스트
        """
        try:
            locale = self.get_user_locale(user_id)
            i18n = await get_i18n_manager()
            return i18n.get_text(key, locale, **kwargs)
        except Exception as e:
            logger.error(f"사용자별 번역 텍스트 조회 실패: {e}")
            return f"[{key}]"

    async def get_text_for_session(self, session_id: str, key: str, **kwargs) -> str:
        """
        세션별 번역 텍스트 조회

        Args:
            session_id: 세션 ID
            key: 번역 키
            **kwargs: 포맷팅 매개변수

        Returns:
            str: 번역된 텍스트
        """
        try:
            locale = self.get_session_locale(session_id)
            i18n = await get_i18n_manager()
            return i18n.get_text(key, locale, **kwargs)
        except Exception as e:
            logger.error(f"세션별 번역 텍스트 조회 실패: {e}")
            return f"[{key}]"

    def get_locale_stats(self) -> Dict[str, int]:
        """로케일 사용 통계"""
        stats = {}

        # 사용자 로케일 통계
        for locale in self._user_locales.values():
            stats[f"users_{locale}"] = stats.get(f"users_{locale}", 0) + 1

        # 세션 로케일 통계
        for locale in self._session_locales.values():
            stats[f"sessions_{locale}"] = stats.get(f"sessions_{locale}", 0) + 1

        stats['total_users'] = len(self._user_locales)
        stats['total_sessions'] = len(self._session_locales)

        return stats

    def clear_all_locales(self) -> None:
        """모든 로케일 정보 초기화"""
        self._user_locales.clear()
        self._session_locales.clear()
        logger.info("모든 로케일 정보 초기화")


# 전역 LocaleService 인스턴스
_locale_service: Optional[LocaleService] = None


def get_locale_service() -> LocaleService:
    """
    전역 LocaleService 인스턴스 반환

    Returns:
        LocaleService: LocaleService 인스턴스
    """
    global _locale_service

    if _locale_service is None:
        _locale_service = LocaleService()

    return _locale_service


def close_locale_service() -> None:
    """전역 LocaleService 종료"""
    global _locale_service

    if _locale_service:
        _locale_service.clear_all_locales()
        _locale_service = None
        logger.info("LocaleService 종료 완료")


# 편의 함수들
def set_user_locale(user_id: str, locale: str) -> bool:
    """사용자 로케일 설정 (편의 함수)"""
    service = get_locale_service()
    return service.set_user_locale(user_id, locale)


def get_user_locale(user_id: str, default: str = 'en') -> str:
    """사용자 로케일 조회 (편의 함수)"""
    service = get_locale_service()
    return service.get_user_locale(user_id, default)


async def get_text_for_user(user_id: str, key: str, **kwargs) -> str:
    """사용자별 번역 텍스트 조회 (편의 함수)"""
    service = get_locale_service()
    return await service.get_text_for_user(user_id, key, **kwargs)