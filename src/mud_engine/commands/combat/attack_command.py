# -*- coding: utf-8 -*-
"""공격 명령어 - 턴제 전투 시스템"""

import logging
from typing import List

from ..base import BaseCommand, CommandResult, CommandResultType
from ..utils import get_user_locale
from ...core.types import SessionType
from ...core.localization import get_localization_manager
from ...game.monster import Monster
from ...game.combat import CombatAction, CombatInstance, Combatant
from ...game.combat_handler import CombatHandler
from ...server.ansi_colors import ANSIColors
from ..Basic import LookCommand

logger = logging.getLogger(__name__)


class AttackCommand(BaseCommand):
    """
    공격 명령어 - 턴제 전투
    전투 시작 의 의미도 됨.
    몹이 선제 공격을 한 경우 이 명령이 실행 된 것으로 취급 할 수도 있음.
    """

    def __init__(self, combat_handler: CombatHandler):
        super().__init__(
            name="attack",
            aliases=["att", "kill", "fight"],
            description="공격합니다",
            usage="attack <몹id>",
        )
        self.combat_handler = combat_handler
        self.I18N = get_localization_manager()

    # 이거 무조건 비동기로 만들어야 하나?
    def get_monster_entity_by_input_digit(self, session: SessionType, target_input) -> Monster:
        if not target_input.isdigit():
            logger.error(f"target_input[{target_input}] is not digit")
            return None

        entity_num = int(target_input)
        logger.info(f"target_input[{target_input}] entity_num[{entity_num}]")
        if session.in_combat:
            combat_instances: CombatInstance = self.combat_handler.combat_manager.get_combat(session.combat_id)
            entity_map = combat_instances.get_entity_map()
        else:
            entity_map = getattr(session, "room_entity_map", {})

        # debug
        logger.info("entity_map starting")
        for entnum in entity_map:
            entity_info = entity_map[entnum]
            logger.info(f"entity_map[{entnum}]: {entity_info['type']}")
        logger.info("entity_map finished")

        if entity_num in entity_map:
            entity_info = entity_map[entity_num]
            logger.info(f"{target_input}번은 타입이 {entity_info['type']} 입니다.")
        else:
            logger.info("못찾음")
            return None

        target_monster = entity_info["entity"]
        return target_monster

    def get_target_combatant_by_monster_id(self, monster_id: str, combat: CombatInstance) -> Combatant:
        # monster_id 라고 써 놓긴 했는데, 플레이어 일 수도 있고 동료 일 수도 있고
        for combatant in combat.combatants:
            logger.debug(f"combatant.id[{combatant.id}] ? [{monster_id}]")
            if combatant.id == monster_id:
                logger.debug("found")
                return combatant
        logger.info("combatant not found")
        return None

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        # 전투 시작
        locale = get_user_locale(session)
        if not self.validate_args(args, min_args=0):
            return self.create_error_result(self.I18N.get_message("combat.no_target", locale))

        target_input = " ".join(args)

        # 번호로 대상 찾기
        target_monster = self.get_monster_entity_by_input_digit(session, target_input)
        if not target_input or not target_monster:
            logger.info(f"공격 대상을 찾을 수 없습니다.args[{args}] target_input[{target_input}]")
            return self.create_error_result(self.I18N.get_message("combat.target_not_found_usage", locale, usage=self.usage))
        logger.info(f"target_monster.id[{target_monster.id}]")

        current_room_id = getattr(session, "current_room_id", None)
        if not current_room_id:
            return self.create_error_result(self.I18N.get_message("combat.no_target", locale))
        logger.info(f"target_input[{target_input}] current_room_id[{current_room_id}]")

        # 인스턴스 확인 및 생성
        combat = await self.combat_handler.start_combat(session.player, target_monster, current_room_id)
        logger.info(combat.to_simple())
        # 생성되면서 턴 순서도 로그에 찍혀야 함

        # 인스턴스에 엔티티 기록
        combat.set_entity_map(getattr(session, "room_entity_map", {}))

        if session.in_combat == True:
            # 전투 중에 attack 명령 인 경우 - 공격 액션 실행
            target_combatant = self.get_target_combatant_by_monster_id(target_monster.id, combat)
            result = await self._execute_combat_attack(session, target_combatant, combat)
            # _execute_attack 내부에서 이미 broadcast됨 → 중복 전송 제거
            combat.advance_turn()

            if combat.is_combat_over():
                await self._end_combat(session, combat, {})
                _lcmd = LookCommand()
                await _lcmd._look_around(session)
                return result

            # 상태 출력
            msg = combat.get_combat_status_message(session.locale)
            await self.combat_handler.send_broadcast_combat_message(combat, msg)
            msg = combat.get_whos_turn(session.locale)
            await self.combat_handler.send_broadcast_combat_message(combat, msg)
            await self.combat_handler.send_battle_command_menu(combat)
            return result

        """else: 새로운 전투 시작"""
        # 세션 상태 업데이트
        session.in_combat = True
        session.original_room_id = current_room_id
        session.combat_id = combat.id
        session.current_room_id = f"combat_{combat.id}"  # 전투 인스턴스로 이동
        logger.debug(session)

        # 출력
        locale = get_user_locale(session)
        monster_name = target_monster.get_localized_name(locale)
        msg = "\n".join([
            "",
            f"{ANSIColors.RED}{self.I18N.get_message('combat.start', locale, monster=monster_name)}{ANSIColors.RESET}",
            "",
        ])
        await self.combat_handler.send_broadcast_combat_message(combat, msg)
        await self.combat_handler.send_broadcast_combat_message(combat, combat.get_combat_status_message(locale))
        await self.combat_handler.send_broadcast_combat_message(combat, combat.get_whos_turn(locale))
        await self.combat_handler.send_battle_command_menu(combat)

        return self.create_success_result(
            message="",
            data={
                "action": "combat_start",
                "combat_id": combat.id,
                "combat_status": combat.to_dict(),
            },
        )

    async def _execute_combat_attack(self, session: SessionType, target: Combatant, combat: CombatInstance) -> CommandResult:
        """전투 중 공격 액션 실행 - _execute_attack 내부에서 즉시 broadcast됨"""
        combat_id = combat.id

        result = await self.combat_handler.process_player_action(combat_id, session.player.id, CombatAction.ATTACK, target.id)
        logger.info(f"result[{result}]")
        return self.create_success_result(
            message="",
            data={"action": "combat_action_result", "combat_status": combat.to_dict()},
        )

    async def _end_combat(self, session: SessionType, combat: CombatInstance, result: dict) -> CommandResult:
        # 전투 종료 공지
        await self.combat_handler.send_broadcast_combat_message_localized(
            combat, lambda loc: self.I18N.get_message("combat.ended", loc)
        )

        # 원래 방으로 복귀
        original_room_id = getattr(session, "original_room_id", None)
        if original_room_id:
            logger.info(f"원래 방으로 복귀 {original_room_id}")
            session.current_room_id = original_room_id

        # 전투 상태 초기화
        session.in_combat = False
        session.original_room_id = None
        session.combat_id = None

        # 현재 플레이어를 전투에서 제거
        self.combat_handler.combat_manager.remove_player_from_combat(session.player.id)

        # 다른 플레이어가 남아있는지 확인
        remaining_players = combat.get_alive_players()
        if len(remaining_players) == 0:
            # 모든 플레이어가 나갔으면 전투 종료
            self.combat_handler.combat_manager.end_combat(combat.id)
            logger.info(f"전투 {combat.id} 종료 - 모든 플레이어 이탈")
        else:
            logger.info(f"전투 {combat.id} 유지 - 남은 플레이어 {len(remaining_players)}명")

        return self.create_success_result(
            message=f"전투 {combat.id} 가 종료 되었습니다.",
            data={"action": "combat_end"},
        )
