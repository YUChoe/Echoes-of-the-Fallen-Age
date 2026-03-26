# -*- coding: utf-8 -*-
"""아이템 사용 명령어 (전투 중)"""

import logging
from typing import List

from ..base import BaseCommand, CommandResult, CommandResultType
from ...core.types import SessionType
from ...game.combat_handler import CombatHandler

logger = logging.getLogger(__name__)


class ItemCommand(BaseCommand):
    def __init__(self, combat_handler: CombatHandler):
        super().__init__(
            name="item",
            aliases=[],
            description="",
            usage="item 12 1  # use/throw item [12] to [1]",
        )
        self.combat_handler = combat_handler

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        combat_id = getattr(session, "combat_id", None)
        if not combat_id:
            return self.create_error_result("전투 정보를 찾을 수 없습니다.")

        combat = self.combat_handler.combat_manager.get_combat(combat_id)
        if not combat or not combat.is_active:
            return self.create_error_result("전투를 찾을 수 없거나 이미 종료되었습니다.")

        message = "ItemCommand!!!!!!!!"
        logger.info(message)
        return self.create_success_result(
            message=message,
            data={"action": "combat_action_result", "combat_status": combat.to_dict()},
        )
