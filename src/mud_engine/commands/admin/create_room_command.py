# -*- coding: utf-8 -*-
"""방 생성 명령어"""

import logging
from typing import List
import uuid

from .base import AdminCommand
from ..base import CommandResult, CommandResultType
from ..utils import get_user_locale
from ...core.types import SessionType
from ...core.localization import get_localization_manager
from ...utils.coordinate_utils import get_direction_from_string, calculate_new_coordinates  # TODO: lazy loading 이 도움이 되나? 난 싫어 하는 패턴인데


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
        # 현재 룸에 대해서 nsew 에 방을 생성
        room_direction = args[0]
        if room_direction not in ["north", "south", "east", "west"]:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.createroom.usage", locale)
            )
        logger.info(f"mkroom {args}")

        # 현재 위치 > new위치 확인
        current_room_id = getattr(session, 'current_room_id', None)
        current_room = await session.game_engine.world_manager.get_room(current_room_id)
        logger.info(f"current_room_id[{current_room_id[-12:]}] ({current_room.x},{current_room.y})")

        direction_enum = get_direction_from_string(room_direction)
        new_x, new_y = calculate_new_coordinates(current_room.x, current_room.y, direction_enum)
        logger.info(f"new_x[{new_x}] new_y[{new_y}]")

        try:
            room_data = {
                "id": str(uuid.uuid4()),
                "description": {
                    "ko": I18N.get_message("admin.createroom.default_desc", "ko"),
                    "en": I18N.get_message("admin.createroom.default_desc", "en")},
                "x": new_x,
                "y": new_y
            }

            success = await session.game_engine.create_room_realtime(room_data, session)

            if success:
                return CommandResult(
                    result_type=CommandResultType.SUCCESS,
                    message=I18N.get_message("admin.createroom.success", locale, room_id=current_room_id),
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

    def get_help(self, locale: str = "en") -> str:
        return """
🏗️ **방 생성 명령어**

**사용법:** `createroom <direction>`

**예시:**
- `createroom south` - 남쪽에 방을 생성

**별칭:** `cr`, `mkroom`
**권한:** 관리자 전용
"""
