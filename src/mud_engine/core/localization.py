"""
다국어 지원 시스템
"""

import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class LocalizationManager:
    """다국어 메시지 관리자"""
    messages: Dict[str, Dict[str, str]]
    default_locale: str
    supported_locales: list

    def __init__(self):
        """초기화"""
        self.messages = {}
        self.default_locale = "en"
        self.supported_locales = ["en", "ko"]
        self._load_default_messages()

    def _load_default_messages(self) -> None:
        """기본 메시지 로드"""
        # 기본 시스템 메시지들
        self.load_from_file('data/translations/auth.json')
        self.load_from_file('data/translations/admin.json')
        self.load_from_file('data/translations/combat.json')
        self.load_from_file('data/translations/command.json')
        self.load_from_file('data/translations/item.json')
        self.load_from_file('data/translations/moving.json')
        self.load_from_file('data/translations/status.json')
        self.load_from_file('data/translations/system.json')

        logger.info(f"기본 메시지 {len(self.messages)}개 로드 완료")

    def get_message(self, key: str, locale: str = None, **kwargs) -> str:
        """
        메시지 조회

        Args:
            key: 메시지 키 (예: "auth.login_success")
            locale: 언어 코드 (None이면 기본 언어)
            **kwargs: 메시지 포맷팅용 변수들

        Returns:
            str: 로케일에 맞는 메시지
        """
        if locale is None:
            locale = self.default_locale

        if locale not in self.supported_locales:
            locale = self.default_locale

        # 메시지 조회
        message_dict = self.messages.get(key)
        if not message_dict:
            logger.warning(f"메시지 키를 찾을 수 없음: {key}")
            return f"[Missing message: {key}]"

        # 로케일별 메시지 조회
        message = message_dict.get(locale)
        if not message:
            # 기본 언어로 폴백
            message = message_dict.get(self.default_locale)
            if not message:
                logger.warning(f"메시지를 찾을 수 없음: {key} (locale: {locale})")
                return f"[Missing message: {key}]"

        # 변수 치환
        try:
            return message.format(**kwargs)
        except KeyError as e:
            logger.warning(f"메시지 포맷팅 실패: {key}, 누락된 변수: {e}")
            return message
        except Exception as e:
            logger.error(f"메시지 포맷팅 오류: {key}, 오류: {e}")
            return message

    def add_message(self, key: str, messages: Dict[str, str]) -> None:
        """
        메시지 추가

        Args:
            key: 메시지 키
            messages: 언어별 메시지 딕셔너리 (예: {"en": "Hello", "ko": "안녕하세요"})
        """
        self.messages[key] = messages
        logger.debug(f"메시지 추가: {key}")

    def load_from_file(self, file_path: str) -> bool:
        """
        파일에서 메시지 로드

        Args:
            file_path: JSON 파일 경로

        Returns:
            bool: 성공 여부
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"메시지 파일이 존재하지 않음: {file_path}")
                return False

            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 기존 메시지에 추가
            for key, messages in data.items():
                if isinstance(messages, dict):
                    self.messages[key] = messages
                else:
                    logger.warning(f"잘못된 메시지 형식: {key}")

            logger.info(f"메시지 파일 로드 완료: {file_path}")
            return True

        except Exception as e:
            logger.error(f"메시지 파일 로드 실패: {file_path}, 오류: {e}")
            return False


# 전역 인스턴스
_localization_manager: Optional[LocalizationManager] = None


def get_localization_manager() -> LocalizationManager:
    """전역 다국어 관리자 인스턴스 반환"""
    global _localization_manager
    if _localization_manager is None:
        _localization_manager = LocalizationManager()
    return _localization_manager


def get_message(key: str, locale: str = None, **kwargs) -> str:
    """
    편의 함수: 메시지 조회

    Args:
        key: 메시지 키
        locale: 언어 코드
        **kwargs: 포맷팅 변수들

    Returns:
        str: 로케일에 맞는 메시지
    """
    return get_localization_manager().get_message(key, locale, **kwargs)
