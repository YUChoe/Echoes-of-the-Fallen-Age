# -*- coding: utf-8 -*-
"""전투 상태 확인 명령어"""

import logging
from typing import List

from ..base import BaseCommand, CommandResult, CommandResultType
from ..utils import get_user_locale
from ...core.types import SessionType
from ...game.combat_handler import CombatHandler

logger = logging.getLogger(__name__)


class CombatStatusCommand(BaseCommand):
    """전투 상태 확인 명령어"""

    def __init__(self, combat_handler: CombatHandler):
        super().__init__(
            name="combat",
            aliases=["battle", "fight_status", "cs"],
            description="현재 전투 상태를 확인합니다",
            usage="combat",
        )
        self.combat_handler = combat_handler

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        if not getattr(session, "in_combat", False):
            return self.create_info_result("현재 전투 중이 아닙니다.")

        combat_id = getattr(session, "combat_id", None)
        if not combat_id:
            return self.create_error_result("전투 정보를 찾을 수 없습니다.")

        combat = self.combat_handler.combat_manager.get_combat(combat_id)
        if not combat:
            return self.create_error_result("전투를 찾을 수 없습니다.")

        locale = get_user_locale(session)
        message = combat.get_combat_status_message(locale)
        message += combat.get_whos_turn(locale)
        return self.create_success_result(
            message=message,
            data={"action": "combat_status", "combat_status": combat.to_dict()},
        )
