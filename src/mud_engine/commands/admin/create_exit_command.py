# -*- coding: utf-8 -*-
"""출구 생성 명령어"""

import logging
from typing import List

from .base import AdminCommand
from ..base import CommandResult, CommandResultType
from ..utils import get_user_locale
from ...core.types import SessionType
from ...core.localization import get_localization_manager

logger = logging.getLogger(__name__)
I18N = get_localization_manager()


class CreateExitCommand(AdminCommand):
    """출구 생성 명령어"""

    def __init__(self):
        super().__init__(
            name="createexit",
            description="방 사이에 출구를 생성합니다",
            aliases=["ce", "mkexit"]
        )

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
        """출구 생성 실행"""
        locale = get_user_locale(session)
        if len(args) < 3:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.createexit.usage", locale)
            )

        from_room = args[0]
        direction = args[1].lower()
        to_room = args[2]

        valid_directions = ['north', 'south', 'east', 'west', 'up', 'down',
                          'northeast', 'northwest', 'southeast', 'southwest']

        if direction not in valid_directions:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.createexit.invalid_direction", locale, directions=', '.join(valid_directions))
            )

        try:
            updates = {
                "exits": {direction: to_room}
            }

            success = await session.game_engine.update_room_realtime(from_room, updates, session)

            if success:
                return CommandResult(
                    result_type=CommandResultType.SUCCESS,
                    message=I18N.get_message("admin.createexit.success", locale, from_room=from_room, to_room=to_room, direction=direction),
                    broadcast=True,
                    broadcast_message=I18N.get_message("admin.createexit.broadcast", locale)
                )
            else:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.createexit.failed", locale)
                )

        except Exception as e:
            logger.error(f"출구 생성 중 오류: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.createexit.error", locale, error=str(e))
            )

    def get_help(self) -> str:
        return """
🚪 **출구 생성 명령어**

**사용법:** `createexit <출발방ID> <방향> <도착방ID>`

**사용 가능한 방향:**
- `north`, `south`, `east`, `west`
- `up`, `down`
- `northeast`, `northwest`, `southeast`, `southwest`

**예시:**
- `createexit garden north library` - 정원에서 북쪽으로 도서관 연결
- `createexit room_001 up room_002` - 1층에서 위쪽으로 2층 연결

**별칭:** `ce`, `mkexit`
**권한:** 관리자 전용
        """
