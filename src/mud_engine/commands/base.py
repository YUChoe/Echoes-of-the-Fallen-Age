# -*- coding: utf-8 -*-
"""명령어 시스템 기본 클래스"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from ..server.session import Session

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
                 description: str = "", usage: str = ""):
        """
        명령어 초기화

        Args:
            name: 명령어 이름
            aliases: 명령어 별칭 목록
            description: 명령어 설명
            usage: 사용법
        """
        self.name = name.lower()
        self.aliases = [alias.lower() for alias in (aliases or [])]
        self.description = description
        self.usage = usage

    @abstractmethod
    async def execute(self, session: Session, args: List[str]) -> CommandResult:
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

    def get_help(self) -> str:
        """
        명령어 도움말 반환

        Returns:
            str: 도움말 텍스트
        """
        help_text = f"**{self.name}**"

        if self.aliases:
            help_text += f" (별칭: {', '.join(self.aliases)})"

        if self.description:
            help_text += f"\n{self.description}"

        if self.usage:
            help_text += f"\n사용법: {self.usage}"

        return help_text

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