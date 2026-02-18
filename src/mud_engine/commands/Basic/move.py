# -*- coding: utf-8 -*-
"""이동 명령어 (방향별)"""

import logging
from typing import List

from ..base import BaseCommand, CommandResult, CommandResultType
from ...core.types import SessionType
from ...core.localization import get_localization_manager
# from ...core.game_engine import GameEngine

logger = logging.getLogger(__name__)


class MoveCommand(BaseCommand):

    def __init__(self, direction: str, aliases: List[str] = None):   # pyright: ignore[reportArgumentType]
        self.direction = direction
        super().__init__(
            name=direction,
            aliases=aliases or [],
            description=f"{direction} 방향으로 이동합니다",
            usage=direction
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        # 전투 중에는 이동 불가
        if getattr(session, 'in_combat', False):
            localization = get_localization_manager()
            locale = session.player.preferred_locale if session.player else "en"
            return self.create_error_result(localization.get_message("movement.combat_blocked", locale))

        # 현재 방 ID 가져오기 (세션에서 또는 캐릭터에서)
        current_room_id = getattr(session, 'current_room_id', None)
        if not current_room_id:
            localization = get_localization_manager()
            locale = session.player.preferred_locale if session.player else "en"
            return self.create_error_result(localization.get_message("movement.no_location", locale))

        # GameEngine을 통해 이동 처리
        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

        try:
            # 좌표 기반 이동 시스템 사용
            success = await game_engine.movement_manager.move_player_by_direction(session, self.direction)

            if success:
                # 이동 성공 - 이동 메시지는 move_player_by_direction에서 이미 전송됨
                return self.create_success_result("")
            else:
                # 이동 실패 - 에러 메시지는 move_player_by_direction에서 이미 전송됨
                return self.create_error_result("")

        except Exception as e:
            logger.error(f"이동 명령어 실행 중 오류: {e}")
            localization = get_localization_manager()
            locale = session.player.preferred_locale if session.player else "en"
            return self.create_error_result(localization.get_message("error.generic", locale))
