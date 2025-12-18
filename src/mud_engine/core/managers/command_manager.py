# -*- coding: utf-8 -*-
"""명령어 관리자"""

import logging
from typing import TYPE_CHECKING, Optional
from datetime import datetime

from ..types import SessionType

if TYPE_CHECKING:
    from ..game_engine import GameEngine
    from ...commands.processor import CommandProcessor

logger = logging.getLogger(__name__)


class CommandManager:
    """명령어 등록 및 처리를 담당하는 매니저"""

    def __init__(self, game_engine: 'GameEngine'):
        self.game_engine = game_engine
        self.command_processor: Optional['CommandProcessor'] = None
        self._setup_command_processor()

    def _setup_command_processor(self) -> None:
        """명령어 처리기 초기화"""
        try:
            from ...commands import CommandProcessor
            self.command_processor = CommandProcessor(self.game_engine.event_bus)
            logger.info("CommandProcessor 초기화 완료")

            self._setup_commands()
            logger.info("명령어 설정 완료")
        except Exception as e:
            logger.error(f"명령어 처리기 초기화 실패: {e}", exc_info=True)
            raise

    def _setup_commands(self) -> None:
        """기본 명령어들 설정"""
        if not self.command_processor:
            logger.error("CommandProcessor가 초기화되지 않았습니다.")
            return

        # 기본 명령어들 import 및 등록
        from ...commands.basic_commands import (
            SayCommand, TellCommand, WhoCommand, LookCommand, QuitCommand,
            GoCommand, ExitsCommand, MoveCommand, HelpCommand, StatsCommand
        )

        self.command_processor.register_command(SayCommand())
        self.command_processor.register_command(TellCommand())
        self.command_processor.register_command(WhoCommand(self.game_engine.session_manager))
        self.command_processor.register_command(LookCommand())
        self.command_processor.register_command(QuitCommand())
        self.command_processor.register_command(StatsCommand())

        # 이동 관련 명령어들 등록
        self.command_processor.register_command(GoCommand())
        self.command_processor.register_command(ExitsCommand())

        # 객체 상호작용 명령어들 등록
        from ...commands.object_commands import GetCommand, DropCommand, InventoryCommand, EquipCommand, UnequipCommand, UseCommand
        self.command_processor.register_command(GetCommand())
        self.command_processor.register_command(DropCommand())
        self.command_processor.register_command(InventoryCommand())
        self.command_processor.register_command(EquipCommand())
        self.command_processor.register_command(UnequipCommand())
        self.command_processor.register_command(UseCommand())

        # 장비 관련 명령어들 등록 (unequipall만 유지)
        from ...commands.equipment_commands import UnequipAllCommand
        self.command_processor.register_command(UnequipAllCommand())

        # 방향별 이동 명령어들 등록
        directions = [
            ('north', ['n']),
            ('south', ['s']),
            ('east', ['e']),
            ('west', ['w'])
        ]

        for direction, aliases in directions:
            self.command_processor.register_command(MoveCommand(direction, aliases))

        # HelpCommand는 command_processor 참조가 필요
        help_command = HelpCommand(self.command_processor)
        self.command_processor.register_command(help_command)

        # 관리자 명령어들 등록
        from ...commands.admin_commands import (
            CreateRoomCommand, EditRoomCommand, CreateExitCommand,
            CreateObjectCommand, AdminListCommand, GotoCommand,
            RoomInfoCommand, SpawnMonsterCommand, ListTemplatesCommand,
            SpawnItemCommand, ListItemTemplatesCommand, TerminateCommand
        )
        from ...commands.admin.scheduler_command import SchedulerCommand
        self.command_processor.register_command(CreateRoomCommand())
        self.command_processor.register_command(EditRoomCommand())
        self.command_processor.register_command(CreateExitCommand())
        self.command_processor.register_command(CreateObjectCommand())
        self.command_processor.register_command(AdminListCommand())
        self.command_processor.register_command(GotoCommand())
        self.command_processor.register_command(RoomInfoCommand())
        self.command_processor.register_command(SpawnMonsterCommand())
        self.command_processor.register_command(ListTemplatesCommand())
        self.command_processor.register_command(SpawnItemCommand())
        self.command_processor.register_command(ListItemTemplatesCommand())
        self.command_processor.register_command(TerminateCommand())
        self.command_processor.register_command(SchedulerCommand())

        # 플레이어 상호작용 명령어들 등록
        from ...commands.interaction_commands import (
            GiveCommand, FollowCommand, WhisperCommand, PlayersCommand
        )
        self.command_processor.register_command(GiveCommand())
        self.command_processor.register_command(FollowCommand())
        self.command_processor.register_command(WhisperCommand())
        self.command_processor.register_command(PlayersCommand())

        # 몬스터 상호작용 명령어들 등록
        from ...commands.npc_commands import (
            TalkCommand, TradeCommand, ShopCommand
        )
        self.command_processor.register_command(TalkCommand())
        self.command_processor.register_command(TradeCommand())
        self.command_processor.register_command(ShopCommand())

        # 전투 명령어들 등록
        from ...commands.combat_commands import (
            AttackCommand, CombatStatusCommand
        )
        self.command_processor.register_command(AttackCommand(self.game_engine.combat_handler))
        self.command_processor.register_command(CombatStatusCommand(self.game_engine.combat_handler))
        # defend, flee는 전투 중에만 사용 가능하므로 일반 명령어 목록에서 제외

        # 사용자 이름 명령어들 등록
        from ...commands.name_commands import (
            ChangeNameCommand, AdminChangeNameCommand
        )
        self.command_processor.register_command(ChangeNameCommand())
        self.command_processor.register_command(AdminChangeNameCommand())

        # 언어 설정 명령어들 등록
        from ...commands.language_commands import LanguageCommand
        self.command_processor.register_command(LanguageCommand())

        # 조사 명령어 등록
        from ...commands.inspect_commands import InspectCommand
        self.command_processor.register_command(InspectCommand())

        logger.info("기본 명령어 등록 완료 (이동, 객체 상호작용, 관리자, 플레이어 상호작용, NPC 상호작용, 전투, 사용자 이름, 조사 명령어 포함)")

    async def handle_player_command(self, session: SessionType, command: str):
        """
        플레이어 명령어 처리

        Args:
            session: 세션 객체
            command: 명령어

        Returns:
            명령어 실행 결과
        """
        if not session.is_authenticated or not session.player:
            await session.send_error("인증되지 않은 사용자입니다.")
            return None

        if not self.command_processor:
            logger.error("CommandProcessor가 초기화되지 않았습니다.")
            await session.send_error("명령어 처리기가 초기화되지 않았습니다.")
            return None

        # 명령어 처리기를 통해 명령어 실행
        result = await self.command_processor.process_command(session, command)

        # 결과를 세션에 전송
        await self._send_command_result(session, result)

        # 결과 반환 (관리자 명령어 응답 처리용)
        return result

    async def _send_command_result(self, session: SessionType, result) -> None:
        """
        명령어 실행 결과를 세션에 전송

        Args:
            session: 세션 객체
            result: 명령어 실행 결과
        """
        from ...commands.base import CommandResultType

        # 기본 메시지 전송
        if result.result_type == CommandResultType.SUCCESS:
            await session.send_success(result.message, result.data)
        elif result.result_type == CommandResultType.ERROR:
            await session.send_error(result.message)
        else:
            await session.send_message({
                "response": result.message,
                "type": result.result_type.value,
                **result.data
            })

        # UI 업데이트가 필요한 명령어인지 확인
        ui_update_commands = ['look', 'go', 'north', 'south', 'east', 'west', 'up', 'down',
                             'northeast', 'northwest', 'southeast', 'southwest', 'get', 'drop']

        # 명령어 처리 후 UI 업데이트 (방 정보가 변경될 수 있는 명령어들)
        if (hasattr(result, 'command_name') and result.command_name in ui_update_commands) or \
           result.data.get('ui_update_needed', False):
            if hasattr(session, 'current_room_id') and session.current_room_id:
                room_info = await self.game_engine.get_room_info(session.current_room_id, session.locale)
                if room_info:
                    await self.game_engine.ui_manager.send_ui_update(session, room_info)

        # 브로드캐스트 처리
        if result.broadcast and result.broadcast_message:
            if result.room_only:
                # 같은 방에만 브로드캐스트
                if hasattr(session, 'current_room_id') and session.current_room_id:
                    await self.game_engine.broadcast_to_room(session.current_room_id, {
                        "type": "room_message",
                        "message": result.broadcast_message,
                        "timestamp": datetime.now().isoformat()
                    }, exclude_session=session.session_id)
            else:
                # 전체 브로드캐스트
                await self.game_engine.broadcast_to_all({
                    "type": "broadcast_message",
                    "message": result.broadcast_message,
                    "timestamp": datetime.now().isoformat()
                })

        # 특별한 액션 처리
        if result.data.get("disconnect"):
            # quit 명령어 등으로 연결 종료 요청
            await self.game_engine.remove_player_session(session, "플레이어 요청으로 종료")