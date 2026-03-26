# -*- coding: utf-8 -*-
"""템플릿에서 아이템 생성 명령어"""

import logging
from typing import List

from .base import AdminCommand
from ..base import CommandResult, CommandResultType
from ..utils import get_user_locale
from ...core.types import SessionType
from ...core.localization import get_localization_manager

logger = logging.getLogger(__name__)
I18N = get_localization_manager()


class SpawnItemCommand(AdminCommand):
    """템플릿에서 아이템 생성 명령어"""

    def __init__(self):
        super().__init__(
            name="spawnitem",
            description="템플릿에서 아이템을 생성합니다",
            aliases=["createitem", "item"],
            usage="spawnitem <template_id> [room_id]"
        )

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
        """템플릿에서 아이템 생성"""
        locale = get_user_locale(session)
        if not args:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.spawnitem.usage", locale)
            )

        template_id = args[0]
        room_id = args[1] if len(args) > 1 else session.current_room_id

        if not room_id:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.spawnitem.no_room", locale)
            )

        try:
            game_engine = session.game_engine
            if not game_engine:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.no_game_engine", locale)
                )

            room = await game_engine.world_manager.get_room(room_id)
            if not room:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.spawnitem.room_not_found", locale, room_id=room_id)
                )

            from uuid import uuid4
            item_id = str(uuid4())

            template_loader = game_engine.world_manager._monster_manager._template_loader
            item = template_loader.create_item_from_template(
                template_id=template_id,
                item_id=item_id,
                location_type="room",
                location_id=room_id
            )

            if not item:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.spawnitem.template_failed", locale, template_id=template_id)
                )

            success = await game_engine.create_object_realtime(item.to_dict(), session)
            if not success:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.spawnitem.save_failed", locale)
                )

            coord_info = f"({room.x}, {room.y})" if hasattr(room, 'x') and hasattr(room, 'y') else room_id
            item_name = item.get_localized_name(locale)

            return CommandResult(
                result_type=CommandResultType.SUCCESS,
                message=I18N.get_message("admin.spawnitem.success", locale, name=item_name, coord=coord_info)
            )

        except Exception as e:
            logger.error(f"아이템 생성 실패: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.spawnitem.error", locale, error=str(e))
            )

    def get_help(self) -> str:
        return """
📦 **아이템 생성 도움말**

템플릿을 사용하여 아이템을 생성합니다.

**사용법:** `spawnitem <template_id> [room_id]`

**매개변수:**
- `template_id`: 아이템 템플릿 ID (예: gold_coin)
- `room_id`: 생성할 방 ID (생략 시 현재 방)

**예시:**
- `spawnitem gold_coin` - 현재 방에 골드 생성
- `spawnitem essence_of_life room_123` - 특정 방에 생명의 정수 생성

**별칭:** `createitem`, `item`
**권한:** 관리자 전용

**사용 가능한 템플릿:**
- gold_coin (골드)
- essence_of_life (생명의 정수)
- 기타 configs/items/ 디렉토리의 템플릿들
        """
