# -*- coding: utf-8 -*-
"""방 편집 명령어"""

import logging
from typing import List

from .base import AdminCommand
from ..base import CommandResult, CommandResultType
from ..utils import get_user_locale
from ...core.types import SessionType
from ...core.localization import get_localization_manager

logger = logging.getLogger(__name__)
I18N = get_localization_manager()


class EditRoomCommand(AdminCommand):
    """방 편집 명령어"""

    def __init__(self):
        super().__init__(
            name="editroom",
            description="기존 방을 편집합니다",
            aliases=["er", "modroom"]
        )

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
        """방 편집 실행"""
        locale = get_user_locale(session)
        if len(args) < 2:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.editroom.usage", locale)
            )

        room_id = args[0]
        new_description = " ".join(args[1:])

        try:
            updates = {
                "description": {"ko": new_description, "en": new_description}
            }

            success = await session.game_engine.update_room_realtime(room_id, updates, session)

            if success:
                return CommandResult(
                    result_type=CommandResultType.SUCCESS,
                    message=I18N.get_message("admin.editroom.success", locale, room_id=room_id),
                    broadcast=True,
                    broadcast_message=I18N.get_message("admin.editroom.broadcast", locale, room_id=room_id)
                )
            else:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.editroom.failed", locale)
                )

        except Exception as e:
            logger.error(f"방 편집 중 오류: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.editroom.error", locale, error=str(e))
            )

    def get_help(self) -> str:
        return """
🔧 **방 편집 명령어**

**사용법:** `editroom <방ID> <설명>`

**예시:**
- `editroom garden 아름다운 정원입니다` - 방 설명 변경
- `editroom library 고요한 분위기의 도서관` - 방 설명 변경

**별칭:** `er`, `modroom`
**권한:** 관리자 전용
**참고:** 방 이름은 좌표로 자동 표시되므로 설명만 편집 가능합니다.
        """
