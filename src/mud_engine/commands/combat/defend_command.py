# -*- coding: utf-8 -*-
"""방어 명령어"""

import logging
from typing import List

from ..base import BaseCommand, CommandResult, CommandResultType
from ...core.types import SessionType
from ...core.localization import get_localization_manager
from ...game.combat import CombatAction, CombatInstance, Combatant
from ...game.combat_handler import CombatHandler

logger = logging.getLogger(__name__)


class DefendCommand(BaseCommand):
    """방어 명령어"""

    def __init__(self, combat_handler: CombatHandler):
        super().__init__(
            name="defend",
            aliases=["def", "guard", "block"],
            description="방어 자세를 취합니다",
            usage="defend",
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
        # TODO: 이거 세션 유효랑 체크들을 한번에 할 수 없나

        # 현재 턴 확인
        current_combatant = combat.get_current_combatant()
        if not current_combatant or current_combatant.id != session.player.id:
            return self.create_error_result("당신의 턴이 아닙니다.")

        # 방어 실행
        result = await self.combat_handler.process_player_action(combat_id, session.player.id, CombatAction.DEFEND, None)

        if not result.get("success"):
            return self.create_error_result(result.get("message", "방어 실패"))

        # 방어 결과 즉시 broadcast
        if result.get("message"):
            combat = self.combat_handler.combat_manager.get_combat(combat_id)
            if combat:
                await self.combat_handler.send_broadcast_combat_message(combat, result["message"])

        # 전투 종료 확인
        if result.get("combat_over"):
            return await self._end_combat(session, combat, result)

        # 몬스터 턴 자동 처리
        while combat.is_active and not combat.is_combat_over():
            current = combat.get_current_combatant()
            if not current:
                break

            from ...game.combat import CombatantType
            if current.combatant_type == CombatantType.PLAYER:
                break

            # 몬스터 턴 처리 (_execute_attack 내부에서 즉시 broadcast됨)
            monster_result = await self.combat_handler.process_monster_turn(combat.id)

            if monster_result.get("combat_over"):
                return await self._end_combat(session, combat, monster_result)

        # 전투 종료 재확인
        if combat.is_combat_over():
            return await self._end_combat(session, combat, {})

        return self.create_success_result(
            message="",
            data={"action": "combat_action_result", "combat_status": combat.to_dict()},
        )

    async def _process_monster_turns(self, combat):
        """몬스터 턴 처리"""
        from .attack_command import AttackCommand
        attack_cmd = AttackCommand(self.combat_handler)
        await attack_cmd._process_monster_turns(combat)

    async def _end_combat(self, session, combat, result):
        """전투 종료"""
        from .attack_command import AttackCommand
        attack_cmd = AttackCommand(self.combat_handler)
        return await attack_cmd._end_combat(session, combat, result)
