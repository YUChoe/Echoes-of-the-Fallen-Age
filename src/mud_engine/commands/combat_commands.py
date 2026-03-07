# -*- coding: utf-8 -*-
"""전투 관련 명령어들 - 턴제 전투 시스템"""

import logging
from typing import List, Optional

from .base import BaseCommand, CommandResult, CommandResultType

from .utils import is_session_available, is_game_engine_available, get_user_locale
from ..core.types import SessionType
from ..core.localization import get_localization_manager
from ..game.monster import Monster, MonsterType
from ..game.combat import CombatAction, CombatInstance, Combatant
from ..game.combat_handler import CombatHandler
from ..server.ansi_colors import ANSIColors


from ..utils import coordinate_utils
from ..utils.coordinate_utils import RoomCoordination

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
        if not self.validate_args(args, min_args=0):
            return self.create_error_result("공격할 대상을 지정해주세요.\n사용법: attack <몹num>")  # TODO: en help

        target_input = " ".join(args)

        # 번호로 대상 찾기
        target_monster = self.get_monster_entity_by_input_digit(session, target_input)
        if not target_input:
            return self.create_error_result(f"해당하는 대상을 찾을 수 없습니다.")
        logger.info(f"target_monster.id[{target_monster.id}]")

        current_room_id = getattr(session, "current_room_id", None)
        if not current_room_id:
            return self.create_error_result("현재 위치를 확인할 수 없습니다.")
        logger.info(f"target_input[{target_input}] current_room_id[{current_room_id}]")

        # 인스턴스 확인 및 생성
        combat = await self.combat_handler.start_combat(session.player, target_monster, current_room_id)
        logger.info(combat)
        # 생성되면서 턴 순서도 로그에 찍혀야 함

        # 인스턴스에 엔티티 기록
        combat.set_entity_map(getattr(session, "room_entity_map", {}))

        if session.in_combat == True:
            # 전투 중에 attack 명령 인 경우 - 공격 액션 실행
            target_combatant = self.get_target_combatant_by_monster_id(target_monster.id, combat)
            result = await self._execute_combat_attack(session, target_combatant, combat)
            await self.combat_handler.send_broadcast_combat_message(combat, result.message)
            result.message = ""  # 위에서 출력 하고 clear
            combat.advance_turn()  # << 턴넘김

            if combat.is_combat_over():
                return result

            # 피 얼마나 남았는지 등 상태 출력
            msg = combat.get_combat_status_message(session.locale)
            await self.combat_handler.send_broadcast_combat_message(combat, msg)
            # 전투 참가자들에게 다음 턴 브로드캐스트
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
        """전투 중 공격 액션 실행"""
        combat_id = combat.id

        # combat_handler 가서 공격 실행
        # 근데 플레이어의 공격이랑 몹의 공격이랑 다를게 있나? 왜 분리가 되어 있는거지
        result = await self.combat_handler.process_player_action(combat_id, session.player.id, CombatAction.ATTACK, target.id)
        logger.info(f"result[{result}]")
        return self.create_success_result(
            message=result.get("message", ""),
            data={"action": "combat_action_result", "combat_status": combat.to_dict()},
        )
        # if not result.get("success"):
        #     return self.create_error_result(result.get("message", "공격 실패"))

        # # 공격 메시지 먼저 저장
        # attack_message = result.get("message", "")

        # # 전투 종료 확인 - combat.is_combat_over()를 직접 확인
        # if combat.is_combat_over():
        #     # 공격 메시지와 함께 전투 종료 처리
        #     end_result = await self._end_combat(session, combat, result)
        #     # 공격 메시지를 승리 메시지 앞에 추가
        #     if attack_message:
        #         combined_message = f"{attack_message}\n\n{end_result.message}"
        #         end_result.message = combined_message
        #     return end_result

        # # 몬스터 턴 자동 처리
        # monster_messages = []
        # while combat.is_active and not combat.is_combat_over():
        #     current = combat.get_current_combatant()
        #     if not current:
        #         break

        #     # 플레이어 턴이면 중단
        #     from ..game.combat import CombatantType

        #     if current.combatant_type == CombatantType.PLAYER:
        #         break

        #     # 몬스터 턴 처리
        #     monster_result = await self.combat_handler.process_monster_turn(combat.id)
        #     if monster_result.get("success") and monster_result.get("message"):
        #         monster_messages.append(monster_result["message"])

        #     # 전투 종료 확인 - combat.is_combat_over()를 직접 확인
        #     if combat.is_combat_over():
        #         # 공격 메시지와 몬스터 메시지를 포함한 전투 종료 처리
        #         end_result = await self._end_combat(session, combat, monster_result)
        #         # 모든 메시지를 승리 메시지 앞에 추가
        #         all_messages = [attack_message] + monster_messages
        #         combined_message = (
        #             "\n".join(filter(None, all_messages)) + f"\n\n{end_result.message}"
        #         )
        #         end_result.message = combined_message
        #         return end_result

        # # 전투 종료 재확인 - combat.is_combat_over() 직접 확인
        # if combat.is_combat_over():
        #     # 공격 메시지와 몬스터 메시지를 포함한 전투 종료 처리
        #     end_result = await self._end_combat(session, combat, {})
        #     # 모든 메시지를 승리 메시지 앞에 추가
        #     all_messages = [attack_message] + monster_messages
        #     combined_message = (
        #         "\n".join(filter(None, all_messages)) + f"\n\n{end_result.message}"
        #     )
        #     end_result.message = combined_message
        #     return end_result

        # # 다음 턴 메시지
        # locale = session.player.preferred_locale if session.player else "ko"
        # message = f"{attack_message}\n"

        # # 몬스터 턴 메시지 추가
        # if monster_messages:
        #     message += "\n" + "\n".join(monster_messages) + "\n"

        # message += "\n" + self._get_combat_status_message(combat, locale)
        # message += "\n\n"
        # message += self._get_turn_message(combat, session.player.id, locale)

        # return self.create_success_result(
        #     message=attack_message,
        #     data={"action": "combat_action_result", "combat_status": combat.to_dict()},
        # )

    # def _get_hp_bar(self, current: int, maximum: int, length: int = 10) -> str:
    #     """HP 바 생성"""
    #     if maximum <= 0:
    #         return "[" + "░" * length + "]"

    #     filled = int((current / maximum) * length)
    #     empty = length - filled

    #     return "[" + "█" * filled + "░" * empty + "]"


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

        # 전투 종료 확인
        if result.get("combat_over"):
            return await self._end_combat(session, combat, result)

        # 몬스터 턴 자동 처리
        monster_messages = []
        while combat.is_active and not combat.is_combat_over():
            current = combat.get_current_combatant()
            if not current:
                break

            # 플레이어 턴이면 중단
            from ..game.combat import CombatantType

            if current.combatant_type == CombatantType.PLAYER:
                break

            # 몬스터 턴 처리
            monster_result = await self.combat_handler.process_monster_turn(combat.id)
            if monster_result.get("success") and monster_result.get("message"):
                monster_messages.append(monster_result["message"])

            # 전투 종료 확인
            if monster_result.get("combat_over"):
                return await self._end_combat(session, combat, monster_result)

        # 전투 종료 재확인
        if combat.is_combat_over():
            return await self._end_combat(session, combat, {})

        # 다음 턴 메시지
        AttackCommand(self.combat_handler)
        # locale = get_user_locale(session)
        message = f"{result.get('message', '')}\n"

        # TODO:
        # # 몬스터 턴 메시지 추가
        # if monster_messages:
        #     message += "\n" + "\n".join(monster_messages) + "\n"

        # message += "\n" + attack_cmd._get_combat_status_message(session, combat, locale)
        # message += "\n\n"
        # message += attack_cmd._get_turn_message(combat, session.player.id, locale)

        return self.create_success_result(
            message=message,
            data={"action": "combat_action_result", "combat_status": combat.to_dict()},
        )

    async def _process_monster_turns(self, combat):
        """몬스터 턴 처리"""
        attack_cmd = AttackCommand(self.combat_handler)
        await attack_cmd._process_monster_turns(combat)

    async def _end_combat(self, session, combat, result):
        """전투 종료"""
        attack_cmd = AttackCommand(self.combat_handler)
        return await attack_cmd._end_combat(session, combat, result)


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

        # 전투에서 제거 됨
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

        # 도망 실패 - 몬스터 턴 처리
        monster_messages = []
        while combat.is_active and not combat.is_combat_over():
            current = combat.get_current_combatant()
            if not current:
                break

            # 플레이어 턴이면 중단
            from ..game.combat import CombatantType

            if current.combatant_type == CombatantType.PLAYER:
                break

            # 몬스터 턴 처리
            monster_result = await self.combat_handler.process_monster_turn(combat.id)
            if monster_result.get("success") and monster_result.get("message"):
                monster_messages.append(monster_result["message"])

            # 전투 종료 확인
            if monster_result.get("combat_over"):
                return await self._end_combat(session, combat, monster_result)

        # 전투 종료 확인
        if combat.is_combat_over():
            return await self._end_combat(session, combat, {})

        # 다음 턴 메시지
        AttackCommand(self.combat_handler)
        message = f"{result.get('message', '')}\n"

        # 몬스터 턴 메시지 추가
        if monster_messages:
            message += "\n" + "\n".join(monster_messages) + "\n"
        # TODO:
        # message += "\n" + attack_cmd._get_combat_status_message(session, combat, locale)
        # message += "\n\n"
        # message += attack_cmd._get_turn_message(combat, session.player.id, locale)

        return self.create_success_result(
            message=message,
            data={"action": "combat_action_result", "combat_status": combat.to_dict()},
        )

    async def _process_monster_turns(self, combat):
        """몬스터 턴 처리"""
        attack_cmd = AttackCommand(self.combat_handler)
        await attack_cmd._process_monster_turns(combat)

    async def _end_combat(self, session, combat, result):
        """전투 종료"""
        attack_cmd = AttackCommand(self.combat_handler)
        return await attack_cmd._end_combat(session, combat, result)


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

        message = "!!!!!!!!"
        logger.info(message)
        return self.create_success_result(
            message=message,
            data={"action": "combat_action_result", "combat_status": combat.to_dict()},
        )


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

        # attack_cmd = AttackCommand(self.combat_handler)
        # locale = get_user_locale(session)
        # message = attack_cmd._get_combat_status_message(session, combat, locale)
        # message += "\n\n"
        # message += attack_cmd._get_turn_message(combat, session.player.id, locale)
        message = ""  # TODO:
        return self.create_success_result(
            message=message,
            data={"action": "combat_status", "combat_status": combat.to_dict()},
        )
