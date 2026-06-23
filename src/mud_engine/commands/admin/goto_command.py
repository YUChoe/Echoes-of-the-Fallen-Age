# -*- coding: utf-8 -*-
"""좌표로 바로 이동하는 명령어"""

import logging
from typing import List

from .base import AdminCommand
from ..base import CommandResult, CommandResultType
from ..utils import get_user_locale
from ...core.types import SessionType
from ...core.localization import get_localization_manager

logger = logging.getLogger(__name__)
I18N = get_localization_manager()


class GotoCommand(AdminCommand):
    """좌표로 바로 이동하는 명령어"""

    def __init__(self):
        super().__init__(
            name="goto",
            description="지정한 좌표로 바로 이동합니다",
            aliases=["tp", "teleport", "warp"]
        )

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
        """좌표로 이동 실행"""
        locale = get_user_locale(session)
        if len(args) < 2:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.goto.usage", locale)
            )

        if getattr(session, 'in_combat', False):
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.in_combat", locale)
            )

        try:
            x = int(args[0])
            y = int(args[1])
        except ValueError:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.goto.invalid_coords", locale)
            )

        try:
            cursor = await session.game_engine.db_manager.execute(
                "SELECT id FROM rooms WHERE x = ? AND y = ?",
                (x, y)
            )
            room_row = await cursor.fetchone()

            if not room_row:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.goto.room_not_found", locale, x=x, y=y)
                )

            target_room_id = room_row[0]
            target_room = await session.game_engine.world_manager.get_room(target_room_id)

            if not target_room:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.goto.room_not_found", locale, x=x, y=y)
                )

            if hasattr(session, 'current_room_id') and session.current_room_id:
                await session.game_engine.broadcast_to_room(
                    session.current_room_id,
                    {
                        "type": "room_message",
                        "message": I18N.get_message("admin.goto.leave_msg", locale, username=session.player.username)
                    },
                    exclude_session=session.session_id
                )

            success = await session.game_engine.movement_manager.move_player_to_room(session, target_room_id)

            if not success:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.goto.move_failed", locale, x=x, y=y)
                )

            await session.game_engine.broadcast_to_room(
                target_room_id,
                {
                    "type": "room_message",
                    "message": I18N.get_message("admin.goto.arrive_msg", locale, username=session.player.get_display_name())
                },
                exclude_session=session.session_id
            )

            return CommandResult(
                result_type=CommandResultType.SUCCESS,
                message=I18N.get_message("admin.goto.success", locale, x=x, y=y)
            )

        except Exception as e:
            logger.error(f"방 이동 중 오류: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.goto.error", locale, error=str(e))
            )

    def get_help(self, locale: str = "en") -> str:
        return """
✨ **순간이동 명령어**

**사용법:** `goto <x좌표> <y좌표>`

**설명:**
관리자 권한으로 지정한 좌표로 즉시 이동합니다.
이동 시 현재 방의 다른 플레이어들에게 알림이 전송됩니다.

**예시:**
- `goto 0 0` - (0, 0) 좌표로 이동
- `goto 5 7` - (5, 7) 좌표로 이동
- `goto 3 4` - (3, 4) 좌표로 이동

**별칭:** `tp`, `teleport`, `warp`
**권한:** 관리자 전용

**주의사항:**
- 좌표는 숫자로 입력해야 합니다
- 존재하지 않는 좌표를 입력하면 이동할 수 없습니다
- 이동 시 다른 플레이어들에게 순간이동 메시지가 표시됩니다
        """
