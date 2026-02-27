# -*- coding: utf-8 -*-
"""전투 관련 명령어들 - 턴제 전투 시스템"""

import logging
from typing import List, Optional

from .base import BaseCommand, CommandResult, CommandResultType

from .utils import is_session_available, is_game_engine_available, get_user_locale
from ..core.types import SessionType
from ..core.localization import get_localization_manager
from ..game.monster import Monster, MonsterType
from ..game.combat import CombatAction, CombatInstance
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

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        # 전투 시작
        if not self.validate_args(args, min_args=0):
            return self.create_error_result(
                "공격할 대상을 지정해주세요.\n사용법: attack <몹num>"
            )  # TODO: en help

        """새로운 전투 시작"""
        target_input = " ".join(args)
        current_room_id = getattr(session, "current_room_id", None)
        if not current_room_id: return self.create_error_result("현재 위치를 확인할 수 없습니다.")
        logger.info(f'target_input[{target_input}] current_room_id[{current_room_id}]')

        # 번호로 대상 찾기
        target_monster = self.get_monster_entity_by_input_digit(session, target_input)
        if not target_input:
            return self.create_error_result(f"해당하는 대상을 찾을 수 없습니다.")

        # 인스턴스 생성
        combat = await self.combat_handler.start_combat(
                session.player, target_monster, current_room_id
        )
        logger.info(combat)
        # 생성되면서 턴 순서도 로그에 찍혀야 함

        # 세션 상태 업데이트
        session.in_combat = True
        session.original_room_id = current_room_id
        session.combat_id = combat.id
        session.current_room_id = f"combat_{combat.id}"  # 전투 인스턴스로 이동
        logger.info(session)

        # 출력
        locale = get_user_locale(session)
        monster_name = target_monster.get_localized_name(locale)
        start_message = "\n".join(
            [
                "",
                f'{ANSIColors.RED}{self.I18N.get_message("combat.start", locale, monster=monster_name)}{ANSIColors.RESET}',
                "",
                f"{self._get_combat_status_message(session, combat, locale)}",
            ]
        )

        logger.info(f"player turn {combat.get_current_combatant().id == session.player.id}")  # 이게 왜 false ?
        if combat.get_current_combatant().id == session.player.id:
            start_message += f"{self._get_turn_message(combat, session.player.id, locale)}"
        else:
            # 다른 플레이어 이거나 몹인 경우 이렇게 처리 해도 됨
            if locale == "ko":  # TODO:
                start_message += f"{ANSIColors.RED}⏳ {monster_name}의 턴입니다...{ANSIColors.RESET}"
            else:
                start_message += f"{ANSIColors.RED}⏳ {monster_name}'s turn...{ANSIColors.RESET}"

        # TODO: subscribe 3sectickscheduler

        return self.create_success_result(
            message=start_message.strip(),
            data={
                "action": "combat_start",
                "combat_id": combat.id,
                "combat_status": combat.to_dict(),
            },
        )


    def _get_combat_status_message(self, session: SessionType, combat: CombatInstance, locale: str = "en") -> str:
        """전투 상태 메시지 생성"""
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f'{ANSIColors.RED}{self.I18N.get_message("combat.round", locale, round=combat.turn_number)}{ANSIColors.RESET}',
            ""
        ]

        # 플레이어 정보
        players = combat.get_alive_players()
        if players:
            player = players[0]
            lines.append(f"[0] 👤 {player.name} HP: {player.current_hp}/{player.max_hp}")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # 몬스터 정보
        monsters = combat.get_alive_monsters()
        room_entity_map = getattr(session, "room_entity_map", {})
        for monster in monsters:
            monster_name = monster.name # monster.name 은 id
            if monster.data and "monster" in monster.data:
                monster_obj = monster.data["monster"]
                monster_name = monster_obj.get_localized_name(locale)
            for num in room_entity_map:
                if 'id' in room_entity_map[num] and room_entity_map[num]['id'] == monster.name:
                    logger.info(f"found id[{monster.name}] {room_entity_map[num]}")
                    break
            else:
                num = "?"
            lines.append(
                f"[{num}] 👹 {monster_name}: HP: {monster.current_hp}/{monster.max_hp}"
            )
        lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines) + "\n"

    def _get_turn_message(self, combat: CombatInstance, player_id: str, locale: str = "en") -> str:
        """플레이어 턴 메시지 생성"""

        return "\n".join([
                self.I18N.get_message("combat.your_turn", locale),
                "",
                f'{self.I18N.get_message("combat.action_attack", locale)}',
                f'{self.I18N.get_message("combat.action_defend", locale)}',
                f'{self.I18N.get_message("combat.action_flee", locale)}',
                f'[4] Item  ',
                self.I18N.get_message("combat.enter_command", locale)
        ])


    def _get_hp_bar(self, current: int, maximum: int, length: int = 10) -> str:
        """HP 바 생성"""
        if maximum <= 0:
            return "[" + "░" * length + "]"

        filled = int((current / maximum) * length)
        empty = length - filled

        return "[" + "█" * filled + "░" * empty + "]"


























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
            return self.create_error_result(
                "전투를 찾을 수 없거나 이미 종료되었습니다."
            )
        # TODO: 이거 세션 유효랑 체크들을 한번에 할 수 없나

        # 현재 턴 확인
        current_combatant = combat.get_current_combatant()
        if not current_combatant or current_combatant.id != session.player.id:
            return self.create_error_result("당신의 턴이 아닙니다.")

        # 방어 실행
        result = await self.combat_handler.process_player_action(
            combat_id, session.player.id, CombatAction.DEFEND, None
        )

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
        attack_cmd = AttackCommand(self.combat_handler)
        locale = get_user_locale(session)
        message = f"{result.get('message', '')}\n"

        # 몬스터 턴 메시지 추가
        if monster_messages:
            message += "\n" + "\n".join(monster_messages) + "\n"

        message += "\n" + attack_cmd._get_combat_status_message(session, combat, locale)
        message += "\n\n"
        message += attack_cmd._get_turn_message(combat, session.player.id, locale)

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
            return self.create_error_result(
                "전투를 찾을 수 없거나 이미 종료되었습니다."
            )

        # 현재 턴 확인
        current_combatant = combat.get_current_combatant()
        if not current_combatant or current_combatant.id != session.player.id:
            return self.create_error_result("당신의 턴이 아닙니다.")

        # 도망 실행
        result = await self.combat_handler.process_player_action(
            combat_id, session.player.id, CombatAction.FLEE, None
        )

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
                original_room = await game_engine.world_manager.get_room(
                    original_room_id
                )
                if not original_room:
                    return self.create_error_result("원래 방을 찾을 수 없습니다.")

                # 출구가 있는지 확인
                logger.info(
                    f"현재 방 출구 확인 시작 {original_room.id} {original_room.x}/{original_room.y}"
                )
                exit_directions = await coordinate_utils.get_exits(
                    game_engine, original_room_id, original_room.x, original_room.y
                )
                logger.info(exit_directions)

                if not exit_directions or len(exit_directions) == 0:
                    # 출구가 없으면 원래 방으로 복귀
                    session.current_room_id = original_room_id
                    flee_message = f"{self.I18N.get_message('combat.flee_success', locale)}\n\n{self.I18N.get_message('combat.return_location', locale)}"
                else:
                    # 랜덤 출구 선택
                    import random

                    random_direction = random.choice(exit_directions)
                    target_room = await game_engine.world_manager.get_room(
                        random_direction.id
                    )
                    session.current_room_id = target_room.id
                    flee_message = f"{self.I18N.get_message('combat.flee_success', locale)}\n\n{random_direction.direction} 방향으로 도망쳐 {target_room.get_localized_description(locale)}에 도착했습니다."

                # 전투 상태 초기화
                session.in_combat = False
                session.original_room_id = None
                session.combat_id = None

                # 전투 인스턴스 종료
                self.combat_handler.combat_manager.end_combat(combat_id)
                logger.info(
                    f"플레이어 {session.player.username} 도망 성공 - 전투 {combat_id} 종료, 이동: {session.current_room_id}"
                )

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
        attack_cmd = AttackCommand(self.combat_handler)
        message = f"{result.get('message', '')}\n"

        # 몬스터 턴 메시지 추가
        if monster_messages:
            message += "\n" + "\n".join(monster_messages) + "\n"

        message += "\n" + attack_cmd._get_combat_status_message(session, combat, locale)
        message += "\n\n"
        message += attack_cmd._get_turn_message(combat, session.player.id, locale)

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
            usage="item 12 1  # use/throw item [12] to [1]"
        )
        self.combat_handler = combat_handler

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        combat_id = getattr(session, "combat_id", None)
        if not combat_id:
            return self.create_error_result("전투 정보를 찾을 수 없습니다.")

        combat = self.combat_handler.combat_manager.get_combat(combat_id)
        if not combat or not combat.is_active:
            return self.create_error_result(
                "전투를 찾을 수 없거나 이미 종료되었습니다."
            )

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

        attack_cmd = AttackCommand(self.combat_handler)
        locale = get_user_locale(session)
        message = attack_cmd._get_combat_status_message(session, combat, locale)
        message += "\n\n"
        message += attack_cmd._get_turn_message(combat, session.player.id, locale)

        return self.create_success_result(
            message=message,
            data={"action": "combat_status", "combat_status": combat.to_dict()},
        )
