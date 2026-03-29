# -*- coding: utf-8 -*-
"""도망 명령어"""

import logging
from typing import List

from ..base import BaseCommand, CommandResult, CommandResultType
from ..utils import get_user_locale
from ...core.types import SessionType
from ...core.localization import get_localization_manager
from ...game.combat import CombatAction, CombatInstance, Combatant
from ...game.combat_handler import CombatHandler
from ...utils import coordinate_utils

logger = logging.getLogger(__name__)


class FleeCommand(BaseCommand):
    """도망 명령어"""

    def __init__(self, combat_handler: CombatHandler):
        super().__init__(
            name="flee",
            aliases=["run", "escape", "retreat"],
            description="전투에서 도망칩니다",
            usage="flee",
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

        # 현재 턴 확인
        current_combatant = combat.get_current_combatant()
        if not current_combatant or current_combatant.id != session.player.id:
            return self.create_error_result("당신의 턴이 아닙니다.")

        # 스태미나 체크 (3 필요)
        stamina = getattr(session, 'stamina', 5.0)
        is_superadmin = getattr(session.player, 'is_admin', False) and session.player.get_display_name() == "SUPERADMIN"
        if stamina < 3.0 and not is_superadmin:
            locale = get_user_locale(session)
            return self.create_error_result(self.I18N.get_message("system.stamina_exhausted", locale))

        # 도망 실행
        result = await self.combat_handler.process_player_action(combat_id, session.player.id, CombatAction.FLEE, None)

        if not result.get("success"):
            return self.create_error_result(result.get("message", "도망 실패"))

        # 도망 결과 즉시 broadcast
        if result.get("message"):
            await self.combat_handler.send_broadcast_combat_message(combat, result["message"])

        locale = get_user_locale(session)

        # 도망 성공 여부 확인
        if result.get("fled"):
            logger.info("도망 성공")
            original_room_id = getattr(session, "original_room_id", None)
            if not original_room_id:
                return self.create_error_result("원래 위치를 찾을 수 없습니다.")

            try:
                game_engine = getattr(session, "game_engine", None)
                if not game_engine:
                    return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

                # 스태미나 소모
                session.stamina = max(0.0, getattr(session, 'stamina', 5.0) - 3.0)

                # 전투 상태 초기화 (이동 전에 해야 move_player_to_room이 정상 동작)
                session.in_combat = False
                session.combat_id = None
                session.original_room_id = None
                self.combat_handler.combat_manager.end_combat(combat_id)

                # 원래 방의 출구에서 랜덤 방향 선택
                original_room = await game_engine.world_manager.get_room(original_room_id)
                if not original_room:
                    session.current_room_id = original_room_id
                    return self.create_success_result(
                        message=f"{self.I18N.get_message('combat.flee_success', locale)}",
                        data={"action": "flee_success"},
                    )

                exit_directions = await coordinate_utils.get_exits(game_engine, original_room_id, original_room.x, original_room.y)

                if exit_directions:
                    import random
                    random_direction = random.choice(exit_directions)
                    target_room = await game_engine.world_manager.get_room(random_direction.id)

                    # move_player_to_room으로 정상 이동 (좌표 업데이트, 이벤트, 알림 포함)
                    session.current_room_id = original_room_id  # 먼저 원래 방으로 복귀
                    await game_engine.movement_manager.move_player_to_room(session, target_room.id)

                    flee_message = f"{self.I18N.get_message('combat.flee_success', locale)}\n{random_direction.direction} 방향으로 도망쳤습니다."
                else:
                    # 출구 없으면 원래 방으로 복귀
                    session.current_room_id = original_room_id
                    await game_engine.movement_manager.send_room_info_to_player(session, original_room_id)
                    flee_message = f"{self.I18N.get_message('combat.flee_success', locale)}"

                logger.info(f"플레이어 {session.player.username} 도망 성공 - 전투 {combat_id} 종료, 이동: {session.current_room_id}")

                return self.create_success_result(
                    message=flee_message,
                    data={"action": "flee_success", "new_room_id": session.current_room_id},
                )

            except Exception as e:
                logger.error(f"도망 처리 중 오류: {e}", exc_info=True)
                session.current_room_id = original_room_id
                session.in_combat = False
                session.original_room_id = None
                session.combat_id = None
                self.combat_handler.combat_manager.end_combat(combat_id)

                return self.create_success_result(
                    message=f"{self.I18N.get_message('combat.flee_success', locale)}",
                    data={"action": "flee_success"},
                )

        # 도망 실패 - 몬스터 턴 처리 (_execute_attack 내부에서 즉시 broadcast됨)
        while combat.is_active and not combat.is_combat_over():
            current = combat.get_current_combatant()
            if not current:
                break

            from ...game.combat import CombatantType
            if current.combatant_type == CombatantType.PLAYER:
                break

            monster_result = await self.combat_handler.process_monster_turn(combat.id)

            if monster_result.get("combat_over"):
                return await self._end_combat(session, combat, monster_result)

        # 전투 종료 확인
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
