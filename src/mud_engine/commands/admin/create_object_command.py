# -*- coding: utf-8 -*-
"""객체 생성 명령어"""

import logging
from typing import List

from .base import AdminCommand
from ..base import CommandResult, CommandResultType
from ..utils import get_user_locale
from ...core.types import SessionType
from ...core.localization import get_localization_manager

logger = logging.getLogger(__name__)
I18N = get_localization_manager()


class CreateObjectCommand(AdminCommand):
    """객체 생성 명령어"""

    def __init__(self):
        super().__init__(
            name="createobject",
            description="새로운 게임 객체를 생성합니다",
            aliases=["co", "mkobj"]
        )

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
        """객체 생성 실행"""
        locale = get_user_locale(session)
        if len(args) < 3:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.createobject.usage", locale)
            )

        obj_id = args[0]
        obj_name = args[1]
        obj_type = args[2].lower()
        location_id = args[3] if len(args) > 3 else session.current_room_id

        valid_types = ['item', 'weapon', 'armor', 'food', 'book', 'key', 'treasure', 'furniture', 'container']

        if obj_type not in valid_types:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.createobject.invalid_type", locale, types=', '.join(valid_types))
            )

        try:
            object_data = {
                "id": obj_id,
                "name": {"ko": obj_name, "en": obj_name},
                "description": {"ko": f"{obj_name}입니다.", "en": f"This is {obj_name}."},
                "object_type": obj_type,
                "location_type": "room",
                "location_id": location_id,
                "properties": {}
            }

            success = await session.game_engine.create_object_realtime(object_data, session)

            if success:
                return CommandResult(
                    result_type=CommandResultType.SUCCESS,
                    message=I18N.get_message("admin.createobject.success", locale, obj_name=obj_name, obj_id=obj_id, location_id=location_id),
                    broadcast=True,
                    broadcast_message=I18N.get_message("admin.createobject.broadcast", locale, obj_name=obj_name)
                )
            else:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.createobject.failed", locale)
                )

        except Exception as e:
            logger.error(f"객체 생성 중 오류: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.createobject.error", locale, error=str(e))
            )

    def get_help(self) -> str:
        return """
✨ **객체 생성 명령어**

**사용법:** `createobject <객체ID> <객체이름> <타입> [위치ID]`

**사용 가능한 타입:**
- `item` - 일반 아이템
- `weapon` - 무기
- `armor` - 방어구
- `food` - 음식
- `book` - 책
- `key` - 열쇠
- `treasure` - 보물
- `furniture` - 가구
- `container` - 상자/컨테이너

**예시:**
- `createobject sword001 철검 weapon` - 현재 방에 철검 생성
- `createobject book001 마법서 book library` - 도서관에 마법서 생성

**별칭:** `co`, `mkobj`
**권한:** 관리자 전용
        """
