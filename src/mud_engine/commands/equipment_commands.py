# -*- coding: utf-8 -*-
"""장비 관련 명령어들"""

import logging
from typing import List, Dict, Optional

from .base import BaseCommand, CommandResult
from ..core.types import SessionType
from ..game.models import GameObject

logger = logging.getLogger(__name__)



class UnequipAllCommand(BaseCommand):
    """모든 장비 해제 명령어"""

    def __init__(self):
        super().__init__(
            name="unequipall",
            aliases=["removeall", "naked"],
            description="착용 중인 모든 장비를 해제합니다",
            usage="unequipall"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not session.player:
            return self.create_error_result("플레이어 정보를 찾을 수 없습니다.")

        # GameEngine 접근
        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

        try:
            # 착용 중인 장비들 조회
            equipped_items = await game_engine.world_manager.get_equipped_objects(session.player.id)

            if not equipped_items:
                return self.create_info_result("착용 중인 장비가 없습니다.")

            unequipped_items = []

            for item in equipped_items:
                item.unequip()
                await game_engine.world_manager.update_object(item)
                unequipped_items.append(item.get_localized_name(session.locale))

            # 결과 메시지 생성
            message = f"⚔️ {len(unequipped_items)}개의 장비를 해제했습니다.\n\n"
            message += "🔓 해제된 장비:\n"
            for item_name in unequipped_items:
                message += f"  • {item_name}\n"

            return self.create_success_result(
                message=message.strip(),
                data={
                    "action": "unequipall",
                    "unequipped_count": len(unequipped_items),
                    "unequipped_items": unequipped_items
                }
            )

        except Exception as e:
            logger.error(f"모든 장비 해제 중 오류: {e}")
            return self.create_error_result("모든 장비 해제 중 오류가 발생했습니다.")