# -*- coding: utf-8 -*-
"""명령어 처리기"""

import logging
import shlex
from typing import Dict, List, Optional, Any
from datetime import datetime

from .base import BaseCommand, CommandResult, CommandResultType
from ..core.types import SessionType
from ..core.event_bus import EventBus, Event, EventType

logger = logging.getLogger(__name__)


class CommandProcessor:
    """명령어 처리기 클래스"""

    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        CommandProcessor 초기화

        Args:
            event_bus: 이벤트 버스 (선택사항)
        """
        self.commands: Dict[str, BaseCommand] = {}
        self.event_bus = event_bus

        logger.info("CommandProcessor 초기화 완료")

    def register_command(self, command: BaseCommand) -> None:
        """
        명령어 등록

        Args:
            command: 등록할 명령어 객체
        """
        # 방향 명령어 전용 예약 별칭
        RESERVED_DIRECTION_ALIASES = {'n', 's', 'e', 'w'}
        
        # 방향 명령어가 아닌데 예약된 별칭을 사용하는지 확인
        if command.name not in ['north', 'south', 'east', 'west']:
            for alias in command.aliases:
                if alias in RESERVED_DIRECTION_ALIASES:
                    logger.error(
                        f"명령어 '{command.name}'이(가) 방향 전용 예약 별칭 '{alias}'를 사용하려고 시도했습니다. "
                        f"n, s, e, w는 방향 명령어 전용입니다."
                    )
                    # 예약된 별칭 제거
                    command.aliases = [a for a in command.aliases if a not in RESERVED_DIRECTION_ALIASES]
        
        # 메인 명령어 이름으로 등록
        self.commands[command.name] = command

        # 별칭들도 등록
        for alias in command.aliases:
            self.commands[alias] = command

        logger.info(f"명령어 등록: {command.name} (별칭: {command.aliases})")

    def unregister_command(self, command_name: str) -> bool:
        """
        명령어 등록 해제

        Args:
            command_name: 해제할 명령어 이름

        Returns:
            bool: 해제 성공 여부
        """
        command_name = command_name.lower()

        if command_name not in self.commands:
            return False

        command = self.commands[command_name]

        # 메인 명령어와 모든 별칭 제거
        keys_to_remove = [command.name] + command.aliases
        for key in keys_to_remove:
            if key in self.commands:
                del self.commands[key]

        logger.info(f"명령어 등록 해제: {command.name}")
        return True

    def get_command(self, command_name: str) -> Optional[BaseCommand]:
        """
        명령어 객체 조회

        Args:
            command_name: 명령어 이름

        Returns:
            Optional[BaseCommand]: 명령어 객체 (없으면 None)
        """
        return self.commands.get(command_name.lower())

    def get_all_commands(self) -> List[BaseCommand]:
        """
        등록된 모든 명령어 목록 반환 (중복 제거)

        Returns:
            List[BaseCommand]: 명령어 목록
        """
        seen = set()
        unique_commands = []

        for command in self.commands.values():
            if command.name not in seen:
                seen.add(command.name)
                unique_commands.append(command)

        return sorted(unique_commands, key=lambda c: c.name)

    def _convert_combat_number_to_command(self, command_line: str) -> str:
        """
        전투 중 숫자 입력을 명령어로 변환
        
        Args:
            command_line: 입력된 명령어 라인
        
        Returns:
            str: 변환된 명령어 라인
        """
        command_line = command_line.strip()
        
        # 숫자만 입력된 경우 변환
        if command_line in ['1', '2', '3']:
            combat_actions = {
                '1': 'attack',
                '2': 'defend',
                '3': 'flee'
            }
            converted = combat_actions.get(command_line, command_line)
            logger.debug(f"전투 숫자 입력 변환: '{command_line}' -> '{converted}'")
            return converted
        
        return command_line

    async def _execute_combat_command(self, session: SessionType, command_name: str, args: List[str]) -> CommandResult:
        """
        전투 전용 명령어 동적 실행
        
        Args:
            session: 세션 객체
            command_name: 명령어 이름
            args: 인수 목록
        
        Returns:
            CommandResult: 실행 결과
        """
        from ..commands.combat_commands import DefendCommand, FleeCommand
        
        # 명령어 별칭 매핑
        defend_aliases = ['defend', 'def', 'guard', 'block']
        flee_aliases = ['flee', 'run', 'escape', 'retreat']
        
        # combat_handler 가져오기
        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="게임 엔진에 접근할 수 없습니다."
            )
        
        combat_handler = game_engine.combat_handler
        
        # 명령어 실행
        if command_name in defend_aliases:
            command = DefendCommand(combat_handler)
            return await command.execute(session, args)
        elif command_name in flee_aliases:
            command = FleeCommand(combat_handler)
            return await command.execute(session, args)
        else:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=f"알 수 없는 전투 명령어: '{command_name}'"
            )

    def parse_command(self, command_line: str) -> tuple[str, List[str]]:
        """
        명령어 라인 파싱

        Args:
            command_line: 명령어 라인

        Returns:
            tuple[str, List[str]]: (명령어, 인수 목록)
        """
        command_line = command_line.strip()

        if not command_line:
            return "", []

        try:
            # shlex를 사용해서 따옴표 처리 등을 올바르게 파싱
            parts = shlex.split(command_line)
        except ValueError:
            # 파싱 오류 시 단순 공백 분할 사용
            parts = command_line.split()

        if not parts:
            return "", []

        command_name = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        return command_name, args

    async def process_command(self, session: SessionType, command_line: str) -> CommandResult:
        """
        명령어 처리

        Args:
            session: 세션 객체
            command_line: 명령어 라인

        Returns:
            CommandResult: 처리 결과
        """
        if not session.is_authenticated or not session.player:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="인증되지 않은 사용자입니다."
            )

        # "." 입력 시 이전 명령어 반복
        if command_line.strip() == ".":
            last_command = getattr(session, 'last_command', None)
            if last_command:
                logger.debug(f"이전 명령어 반복: {last_command}")
                command_line = last_command
            else:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message="반복할 이전 명령어가 없습니다."
                )

        # 전투 중일 때 숫자 입력을 명령어로 변환
        if getattr(session, 'in_combat', False):
            command_line = self._convert_combat_number_to_command(command_line)

        # 명령어 파싱
        command_name, args = self.parse_command(command_line)

        if not command_name:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="명령어가 비어있습니다."
            )

        # 전투 전용 명령어 처리 (defend, flee)
        in_combat = getattr(session, 'in_combat', False)
        combat_only_commands = ['defend', 'flee', 'def', 'guard', 'block', 'run', 'escape', 'retreat']
        
        if command_name in combat_only_commands:
            if not in_combat:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message="전투 중에만 사용할 수 있는 명령어입니다."
                )
            # 전투 중이면 동적으로 명령어 생성하여 실행
            return await self._execute_combat_command(session, command_name, args)

        # 명령어 조회
        command = self.get_command(command_name)

        if not command:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=f"알 수 없는 명령어: '{command_name}'. 'help'를 입력해서 사용 가능한 명령어를 확인하세요."
            )

        try:
            # 명령어 실행 전 이벤트 발행
            if self.event_bus:
                await self.event_bus.publish(Event(
                    event_type=EventType.PLAYER_COMMAND,
                    source=session.session_id,
                    data={
                        "player_id": session.player.id,
                        "username": session.player.username,
                        "command": command_name,
                        "args": args,
                        "full_command": command_line,
                        "session_id": session.session_id
                    }
                ))

            # 관리자 전용 명령어 권한 확인
            if hasattr(command, 'admin_only') and command.admin_only:
                is_admin = getattr(session.player, 'is_admin', False)
                if not is_admin:
                    logger.warning(f"권한 없음: {session.player.username} -> {command_name} (관리자 전용)")
                    return CommandResult(
                        result_type=CommandResultType.ERROR,
                        message=f"'{command_name}' 명령어는 관리자 전용입니다."
                    )

            # 명령어 실행
            result = await command.execute(session, args)

            # 실행 결과 로깅
            logger.info(f"명령어 실행: {session.player.username} -> {command_name} -> {result.result_type.value}")

            # 명령어 실행 성공 시 마지막 명령어로 저장 (반복 명령 제외)
            if result.result_type == CommandResultType.SUCCESS and command_line.strip() != ".":
                session.last_command = command_line

            return result

        except Exception as e:
            logger.error(f"명령어 실행 중 오류 ({command_name}): {e}", exc_info=True)
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=f"명령어 실행 중 오류가 발생했습니다: {str(e)}"
            )

    def get_help_text(self, command_name: Optional[str] = None, is_admin: bool = False) -> str:
        """
        도움말 텍스트 생성

        Args:
            command_name: 특정 명령어 도움말 (None이면 전체 목록)
            is_admin: 관리자 권한 여부

        Returns:
            str: 도움말 텍스트
        """
        if command_name:
            command = self.get_command(command_name)
            if command:
                # 관리자 전용 명령어인데 관리자가 아니면 접근 거부
                if hasattr(command, 'admin_only') and command.admin_only and not is_admin:
                    return f"'{command_name}' 명령어는 관리자 전용입니다."
                return command.get_help()
            else:
                return f"알 수 없는 명령어: '{command_name}'"

        # 전체 명령어 목록 (권한에 따라 필터링)
        all_commands = self.get_all_commands()
        commands = [cmd for cmd in all_commands if not (hasattr(cmd, 'admin_only') and cmd.admin_only) or is_admin]

        if not commands:
            return "사용 가능한 명령어가 없습니다."

        help_text = "🎮 사용 가능한 명령어:\n\n"

        # 일반 명령어와 관리자 명령어 분리
        normal_commands = [cmd for cmd in commands if not (hasattr(cmd, 'admin_only') and cmd.admin_only)]
        admin_commands = [cmd for cmd in commands if hasattr(cmd, 'admin_only') and cmd.admin_only]

        # 일반 명령어 표시
        if normal_commands:
            for command in normal_commands:
                help_text += f"• {command.name}"
                if command.aliases:
                    help_text += f" ({', '.join(command.aliases)})"
                if command.description:
                    help_text += f" - {command.description}"
                help_text += "\n"

        # 관리자 명령어 표시 (관리자인 경우에만)
        if admin_commands and is_admin:
            help_text += "\n🔧 관리자 명령어:\n"
            for command in admin_commands:
                help_text += f"• {command.name}"
                if command.aliases:
                    help_text += f" ({', '.join(command.aliases)})"
                if command.description:
                    help_text += f" - {command.description}"
                help_text += "\n"

        help_text += "\n특정 명령어의 자세한 도움말을 보려면 'help <명령어>'를 입력하세요."

        return help_text

    def get_stats(self) -> Dict[str, Any]:
        """
        명령어 처리기 통계 정보 반환

        Returns:
            Dict: 통계 정보
        """
        unique_commands = self.get_all_commands()

        return {
            "total_commands": len(unique_commands),
            "total_aliases": len(self.commands) - len(unique_commands),
            "command_names": [cmd.name for cmd in unique_commands],
            "has_event_bus": self.event_bus is not None
        }