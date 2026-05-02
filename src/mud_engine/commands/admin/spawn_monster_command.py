# -*- coding: utf-8 -*-
"""템플릿에서 몬스터 생성 명령어"""

import logging
from typing import List

from .base import AdminCommand
from ..base import CommandResult, CommandResultType
from ..utils import get_user_locale
from ...core.types import SessionType
from ...core.localization import get_localization_manager

logger = logging.getLogger(__name__)
I18N = get_localization_manager()


class SpawnMonsterCommand(AdminCommand):
    """템플릿에서 몬스터 생성 명령어"""

    def __init__(self):
        super().__init__(
            name="spawnmonster",
            description="템플릿에서 몬스터를 생성합니다",
            aliases=["spawn", "createmonster"],
            usage="spawnmonster <template_id> [room_id]"
        )

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
        """템플릿에서 몬스터 생성"""
        locale = get_user_locale(session)
        if not args:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.spawn.usage", locale)
            )

        template_id = args[0]
        room_id = args[1] if len(args) > 1 else session.current_room_id

        if not room_id:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.spawn.no_room", locale)
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
                    message=I18N.get_message("admin.spawn.room_not_found", locale, room_id=room_id)
                )

            monster = await game_engine.world_manager._monster_manager._spawn_monster_from_template(
                room_id=room_id,
                template_id=template_id
            )

            if not monster:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.spawn.template_failed", locale, template_id=template_id)
                )

            coord_info = f"({room.x}, {room.y})" if hasattr(room, 'x') and hasattr(room, 'y') else room_id

            return CommandResult(
                result_type=CommandResultType.SUCCESS,
                message=I18N.get_message("admin.spawn.success", locale, name=monster.get_localized_name(locale), coord=coord_info)
            )

        except Exception as e:
            logger.error(f"몬스터 생성 실패: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.spawn.error", locale, error=str(e))
            )

    def get_help(self, locale: str = "en") -> str:
        return """
🐉 **몬스터 생성 도움말**

템플릿을 사용하여 몬스터를 생성합니다.

**사용법:** `spawnmonster <template_id> [room_id]`

**매개변수:**
- `template_id`: 몬스터 템플릿 ID (예: template_forest_goblin)
- `room_id`: 생성할 방 ID (생략 시 현재 방)

**예시:**
- `spawnmonster template_forest_goblin` - 현재 방에 숲 고블린 생성
- `spawnmonster template_small_rat room_123` - 특정 방에 작은 쥐 생성

**별칭:** `spawn`, `createmonster`
**권한:** 관리자 전용

**사용 가능한 템플릿:**
- template_small_rat (작은 쥐)
- template_forest_goblin (숲 고블린)
- template_town_guard (마을 경비병)
- template_harbor_guide (항구 안내인)
- template_square_guard (광장 경비병)
- template_light_armored_guard (경장 경비병)
        """
