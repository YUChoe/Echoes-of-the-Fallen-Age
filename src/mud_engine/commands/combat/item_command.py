# -*- coding: utf-8 -*-
"""아이템 사용 명령어 (전투 중)"""

import logging
from typing import List

from ..base import BaseCommand, CommandResult, CommandResultType
from ..inventory_command import InventoryCommand
from ..use_command import UseCommand
from ...core.types import SessionType
from ...game.combat_handler import CombatHandler
from ...game.combat import CombatantType

logger = logging.getLogger(__name__)


class ItemCommand(BaseCommand):
    """전투 중 아이템 명령어 - 인벤토리 확인 및 아이템 사용"""

    def __init__(self, combat_handler: CombatHandler):
        super().__init__(
            name="item",
            aliases=[],
            description="전투 중 아이템을 확인하거나 사용합니다",
            usage="item [번호]",
        )
        self.combat_handler = combat_handler

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        combat_id = getattr(session, "combat_id", None)
        if not combat_id:
            return self.create_error_result("전투 정보를 찾을 수 없습니다.")

        combat = self.combat_handler.combat_manager.get_combat(combat_id)
        if not combat or not combat.is_active:
            return self.create_error_result("전투를 찾을 수 없거나 이미 종료되었습니다.")

        # TODO: item <아이템번호> <몬스터번호> — 몬스터에게 아이템 사용 (use item to monster)

        if not args:
            # 인자 없음: 인벤토리 표시 (턴 소모 없음)
            inv_cmd = InventoryCommand()
            return await inv_cmd.execute(session, [])

        # 인자 있음: 아이템 사용
        use_cmd = UseCommand()
        result = await use_cmd.execute(session, args)

        # 사용 실패 시 턴 소모 없음
        if result.result_type != CommandResultType.SUCCESS:
            return result

        # 사용 성공 시 턴 진행
        combat.advance_turn()

        # 전투 종료 확인
        if combat.is_combat_over():
            from .attack_command import AttackCommand
            attack_cmd = AttackCommand(self.combat_handler)
            return await attack_cmd._end_combat(session, combat, {})

        # 몬스터 턴 처리
        while combat.is_active and not combat.is_combat_over():
            current = combat.get_current_combatant()
            if not current:
                break
            if current.combatant_type == CombatantType.PLAYER:
                break
            await self.combat_handler.process_monster_turn(combat.id)
            if combat.is_combat_over():
                from .attack_command import AttackCommand
                attack_cmd = AttackCommand(self.combat_handler)
                return await attack_cmd._end_combat(session, combat, {})

        return result
