# -*- coding: utf-8 -*-
"""방 생성 명령어"""

import logging
from typing import List

from .base import AdminCommand
from ..base import CommandResult, CommandResultType
from ..utils import get_user_locale
from ...core.types import SessionType
from ...core.localization import get_localization_manager

logger = logging.getLogger(__name__)
I18N = get_localization_manager()


class CreateRoomCommand(AdminCommand):
    """실시간 방 생성 명령어"""

    def __init__(self):
        super().__init__(
            name="createroom",
            description="새로운 방을 생성합니다",
            aliases=["cr", "mkroom"]
        )

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
        """방 생성 실행"""
        locale = get_user_locale(session)
        if len(args) < 1:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.createroom.usage", locale)
            )

        room_id = args[0]
        default_desc = I18N.get_message("admin.createroom.default_desc", locale)
        room_description = " ".join(args[1:]) if len(args) > 1 else default_desc

        try:
            room_data = {
                "id": room_id,
                "description": {"ko": room_description, "en": room_description},
                "exits": {}
            }

            success = await session.game_engine.create_room_realtime(room_data, session)

            if success:
                return CommandResult(
                    result_type=CommandResultType.SUCCESS,
                    message=I18N.get_message("admin.createroom.success", locale, room_id=room_id),
                    broadcast=True,
                    broadcast_message=I18N.get_message("admin.createroom.broadcast", locale)
                )
            else:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.createroom.failed", locale)
                )

        except Exception as e:
            logger.error(f"방 생성 중 오류: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.createroom.error", locale, error=str(e))
            )

    def get_help(self) -> str:
        return """
🏗️ **방 생성 명령어**

**사용법:** `createroom <방ID> [설명]`

**예시:**
- `createroom garden` - 기본 설명으로 방 생성
- `createroom library 조용한 도서관입니다` - 상세 설명과 함께 생성

**별칭:** `cr`, `mkroom`
**권한:** 관리자 전용
**참고:** 방 이름은 좌표로 자동 표시됩니다.
        """
