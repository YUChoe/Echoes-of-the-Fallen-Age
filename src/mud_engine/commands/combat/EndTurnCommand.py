import logging
from typing import List, Optional

from ..base import BaseCommand, CommandResult, CommandResultType
from ...core.types import SessionType
from ...game.combat_handler import CombatHandler
from ...game.combat import CombatAction
from ...core.localization import get_localization_manager

logger = logging.getLogger(__name__)

class EndTurnCommand(BaseCommand):

    def __init__(self, combat_handler: CombatHandler):
        super().__init__(
            name="endturn",
            aliases=[],
            description="턴을넘깁입니다.",
            usage="endturn",
        )
        self.combat_handler = combat_handler
        self.I18N = get_localization_manager()

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        combat_id = getattr(session, "combat_id", None)
        if not combat_id:
            return self.create_error_result("전투 정보를 찾을 수 없습니다.")

        combat = self.combat_handler.combat_manager.get_combat(combat_id)
        if not combat or not combat.is_active:
            return self.create_error_result("전투를 찾을 수 없거나 이미 종료되었습니다.")

        logger.info(f"EndTurnCommand excute invoked")
        await self.combat_handler.process_player_action(combat_id, session.player.id,
            CombatAction.ENDTURN, target_id=None)

        return self.create_success_result(
            message="",
            data={
                "action": "combat_action_result",
                "combat_status": combat.to_dict()
                }
        )

