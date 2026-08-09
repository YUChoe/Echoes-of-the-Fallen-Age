# -*- coding: utf-8 -*-
"""명령어 시스템 기본 클래스"""

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from ..core.types import SessionType

if TYPE_CHECKING:
    from .context import ActionContext, ActionResult

logger = logging.getLogger(__name__)


class CommandResultType(Enum):
    """명령어 실행 결과 타입"""
    SUCCESS = "success"
    ERROR = "error"
    INFO = "info"
    WARNING = "warning"


@dataclass
class CommandResult:
    """명령어 실행 결과"""
    result_type: CommandResultType
    message: str
    data: Dict[str, Any] = None
    broadcast: bool = False  # 다른 플레이어에게 브로드캐스트할지 여부
    broadcast_message: Optional[str] = None  # 브로드캐스트할 메시지
    room_only: bool = False  # 같은 방에만 브로드캐스트할지 여부

    def __post_init__(self):
        if self.data is None:
            self.data = {}


class BaseCommand(ABC):
    """명령어 기본 클래스"""

    def __init__(self, name: str, aliases: Optional[List[str]] = None,
                 description: str = "", usage: str = "", admin_only: bool = False):
        """
        명령어 초기화

        Args:
            name: 명령어 이름
            aliases: 명령어 별칭 목록
            description: 명령어 설명
            usage: 사용법
            admin_only: 관리자 전용 명령어 여부
        """
        self.name = name.lower()
        self.aliases = [alias.lower() for alias in (aliases or [])]
        self.description = description
        self.usage = usage
        self.admin_only = admin_only

    @abstractmethod
    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        """
        명령어 실행

        Args:
            session: 세션 객체
            args: 명령어 인수 목록

        Returns:
            CommandResult: 실행 결과
        """
        pass

    def matches(self, command_name: str) -> bool:
        """
        명령어 이름이 일치하는지 확인

        Args:
            command_name: 확인할 명령어 이름

        Returns:
            bool: 일치 여부
        """
        command_name = command_name.lower()
        return command_name == self.name or command_name in self.aliases

    def get_help(self, locale: str = "en") -> str:
        """
        명령어 도움말 반환 (다국어 지원)

        Args:
            locale: 언어 설정 ("en" 또는 "ko")

        Returns:
            str: 도움말 텍스트
        """
        from ..core.localization import get_localization_manager
        localization = get_localization_manager()

        help_text = f"{self.name}"

        if self.aliases:
            alias_label = "Aliases" if locale == "en" else "별칭"
            help_text += f" ({alias_label}: {', '.join(self.aliases)})"

        # 번역 키로 description 조회, 없으면 self.description 폴백
        desc_key = f"cmd.{self.name}.desc"
        description = localization.get_message(desc_key, locale)
        if description and not description.startswith("[Missing message:"):
            help_text += f"\n{description}"
        elif self.description:
            help_text += f"\n{self.description}"

        # 번역 키로 usage 조회, 없으면 self.usage 폴백
        usage_str = self.get_localized_usage(locale)
        if usage_str:
            usage_label = "Usage" if locale == "en" else "사용법"
            help_text += f"\n{usage_label}: {usage_str}"

        return help_text

    def get_localized_usage(self, locale: str = "en") -> str:
        """
        locale에 맞는 usage 문자열 반환

        Args:
            locale: 언어 설정 ("en" 또는 "ko")

        Returns:
            str: 사용법 문자열 (번역 키 우선, 없으면 self.usage 폴백)
        """
        from ..core.localization import get_localization_manager
        localization = get_localization_manager()

        usage_key = f"cmd.{self.name}.usage"
        usage = localization.get_message(usage_key, locale)
        if usage and not usage.startswith("[Missing message:"):
            return usage
        return self.usage

    def validate_args(self, args: List[str], min_args: int = 0,
                     max_args: Optional[int] = None) -> bool:
        """
        명령어 인수 유효성 검사

        Args:
            args: 인수 목록
            min_args: 최소 인수 개수
            max_args: 최대 인수 개수 (None이면 제한 없음)

        Returns:
            bool: 유효성 검사 결과
        """
        if len(args) < min_args:
            return False

        if max_args is not None and len(args) > max_args:
            return False

        return True

    def create_error_result(self, message: str, data: Dict[str, Any] = None) -> CommandResult:
        """오류 결과 생성"""
        # 여기에 로그를 안 넣는 이유는 발생 위치도 확인 하기 위해
        return CommandResult(
            result_type=CommandResultType.ERROR,
            message=message,
            data=data or {}
        )

    def create_success_result(self, message: str, data: Dict[str, Any] = None,
                            broadcast: bool = False, broadcast_message: str = None,
                            room_only: bool = False) -> CommandResult:
        """성공 결과 생성"""
        return CommandResult(
            result_type=CommandResultType.SUCCESS,
            message=message,
            data=data or {},
            broadcast=broadcast,
            broadcast_message=broadcast_message,
            room_only=room_only
        )

    def create_info_result(self, message: str, data: Dict[str, Any] = None) -> CommandResult:
        """정보 결과 생성"""
        return CommandResult(
            result_type=CommandResultType.INFO,
            message=message,
            data=data or {}
        )


class ActionHandler(ABC):
    """액션 핸들러 기본 클래스

    구조화 액션 하나를 처리한다. 문자열 파싱과 별칭이 없으므로 이름, 별칭,
    사용법, 도움말을 갖지 않는다. 클라이언트가 엔티티 속성으로 버튼을 추론하고
    서버는 적용 불가한 요청을 거절한다.
    """

    # 이 핸들러가 처리하는 verb
    verb: str = ""

    # 대상 uuid 가 필요한 verb 인지. 디스패처가 검사한다
    requires_target: bool = False

    # 전투 중에만 허용되는 verb 인지
    combat_only: bool = False

    # 전투 중에 금지되는 verb 인지
    forbidden_in_combat: bool = False

    # 관리자 전용 verb 인지
    admin_only: bool = False

    @abstractmethod
    async def handle(self, ctx: "ActionContext") -> "ActionResult":
        """액션을 처리한다.

        Args:
            ctx: 액션 컨텍스트. 대상 해석은 디스패처가 이미 수행했다

        Returns:
            처리 결과
        """
        raise NotImplementedError
