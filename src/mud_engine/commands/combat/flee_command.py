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
            # 원래 방 정보 가져오기
            original_room_id = getattr(session, "original_room_id", None)
            if not original_room_id:
                return self.create_error_result("원래 위치를 찾을 수 없습니다.")

            try:
                game_engine = getattr(session, "game_engine", None)
                if not game_engine:
                    return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

                # 원래 방의 출구 정보 가져오기
                original_room = await game_engine.world_manager.get_room(original_room_id)
                if not original_room:
                    return self.create_error_result("원래 방을 찾을 수 없습니다.")

                # 출구가 있는지 확인
                logger.info(f"현재 방 출구 확인 시작 {original_room.id} {original_room.x}/{original_room.y}")
                exit_directions = await coordinate_utils.get_exits(game_engine, original_room_id, original_room.x, original_room.y)
                logger.info(exit_directions)

                if not exit_directions or len(exit_directions) == 0:
                    # 출구가 없으면 원래 방으로 복귀
                    session.current_room_id = original_room_id
                    flee_message = f"{self.I18N.get_message('combat.flee_success', locale)}\n\n{self.I18N.get_message('combat.return_location', locale)}"
                else:
                    # 랜덤 출구 선택
                    import random

                    random_direction = random.choice(exit_directions)
                    target_room = await game_engine.world_manager.get_room(random_direction.id)
                    session.current_room_id = target_room.id
                    flee_message = f"{self.I18N.get_message('combat.flee_success', locale)}\n\n{random_direction.direction} 방향으로 도망쳐 {target_room.get_localized_description(locale)}에 도착했습니다."

                # 전투 상태 초기화
                session.in_combat = False
                session.original_room_id = None
                session.combat_id = None

                # 전투 인스턴스 종료
                self.combat_handler.combat_manager.end_combat(combat_id)
                logger.info(f"플레이어 {session.player.username} 도망 성공 - 전투 {combat_id} 종료, 이동: {session.current_room_id}")

                return self.create_success_result(
                    message=flee_message,
                    data={
                        "action": "flee_success",
                        "new_room_id": session.current_room_id,
                    },
                )

            except Exception as e:
                logger.error(f"도망 처리 중 오류: {e}", exc_info=True)
                # 오류 발생 시 원래 방으로 복귀
                session.current_room_id = original_room_id
                session.in_combat = False
                session.original_room_id = None
                session.combat_id = None
                self.combat_handler.combat_manager.end_combat(combat_id)

                return self.create_success_result(
                    message=f"{self.I18N.get_message('combat.flee_success', locale)}\n\n{self.I18N.get_message('combat.return_location', locale)}",
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
