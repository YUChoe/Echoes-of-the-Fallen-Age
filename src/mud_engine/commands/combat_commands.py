# -*- coding: utf-8 -*-
"""전투 관련 명령어들 - 턴제 전투 시스템"""

import logging
from datetime import datetime
from typing import List, Optional

from .base import BaseCommand, CommandResult, CommandResultType
from ..core.types import SessionType
from ..game.combat import CombatAction, CombatInstance
from ..game.combat_handler import CombatHandler
from ..server.ansi_colors import ANSIColors

from ..utils import coordinate_utils
from ..utils.coordinate_utils import RoomCoordination

logger = logging.getLogger(__name__)


class AttackCommand(BaseCommand):
    """공격 명령어 - 턴제 전투"""

    def __init__(self, combat_handler: CombatHandler):
        super().__init__(
            name="attack",
            aliases=["att", "kill", "fight"],
            description="몬스터를 공격합니다",
            usage="attack <몬스터명>",
        )
        self.combat_handler = combat_handler

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        # 전투 중인 경우 - 공격 액션 실행
        if getattr(session, "in_combat", False):
            return await self._execute_combat_attack(session)

        # 전투 시작
        if not self.validate_args(args, min_args=1):
            return self.create_error_result(
                "공격할 대상을 지정해주세요.\n사용법: attack <몬스터명>"
            )

        return await self._start_combat(session, args)

    async def _start_combat(
        self, session: SessionType, args: List[str]
    ) -> CommandResult:
        """새로운 전투 시작"""
        target_input = " ".join(args)
        current_room_id = getattr(session, "current_room_id", None)

        if not current_room_id:
            return self.create_error_result("현재 위치를 확인할 수 없습니다.")

        try:
            game_engine = getattr(session, "game_engine", None)
            if not game_engine:
                return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

            # 번호로 입력된 경우 만 처리
            target_monster = None  # 복수 일 수도?
            if not target_input.isdigit():
                return self.create_error_result(
                    f"대상 [{target_input}]을 찾을 수 없습니다."
                )
            entity_num = int(target_input)
            entity_map = getattr(session, "room_entity_map", {})

            if entity_num in entity_map:
                entity_info = entity_map[entity_num]
                logger.info(f"{target_input}번은 타입이 {entity_info['type']} 입니다.")
            else:
                return self.create_error_result(
                    f"번호 [{entity_num}]에 해당하는 대상을 찾을 수 없습니다."
                )

            target_monster = entity_info["entity"]

            # 전투 인스턴스 생성 / 만약 몹이 전투중이면 그 인스턴스가 반환 됨
            combat = await self.combat_handler.start_combat(
                session.player, target_monster, current_room_id
            )
            logger.info(combat)

            # 세션 상태 업데이트
            session.in_combat = True
            session.original_room_id = current_room_id
            session.combat_id = combat.id
            session.current_room_id = f"combat_{combat.id}"  # 전투 인스턴스로 이동
            logger.info(session)

            # 플레이어의 언어 설정에 따라 몬스터 이름 표시
            locale = session.player.preferred_locale if session.player else "en"
            monster_name = target_monster.get_localized_name(locale)

            # 몬스터가 선공이면 자동으로 턴 처리
            # 몹에게 "알림" 형태로?
            current = combat.get_current_combatant()
            from ..game.combat import CombatantType

            if current and current.combatant_type == CombatantType.MONSTER:
                logger.info(f"몬스터 선공 - 자동 턴 처리 시작")
                await self._process_monster_turns(combat)

                # 전투 종료 확인
                if combat.is_combat_over():
                    return await self._end_combat(session, combat, {})

            # 전투 시작 메시지 (몬스터 턴 처리 후)
            from ..core.localization import get_localization_manager

            localization = get_localization_manager()
            locale = session.player.preferred_locale if session.player else "en"

            start_message = "\n".join(
                [
                    "",
                    f'{ANSIColors.RED}{localization.get_message("combat.start", locale, monster=monster_name)}{ANSIColors.RESET}',
                    "",
                    f"{self._get_combat_status_message(combat, locale)}",
                    f"{self._get_turn_message(combat, session.player.id, locale)}",
                ]
            )

            return self.create_success_result(
                message=start_message.strip(),
                data={
                    "action": "combat_start",
                    "combat_id": combat.id,
                    "combat_status": combat.to_dict(),
                },
            )

        except Exception as e:
            logger.error(f"전투 시작 중 오류: {e}", exc_info=True)
            return self.create_error_result("전투 시작 중 오류가 발생했습니다.")

    async def _execute_combat_attack(self, session: SessionType) -> CommandResult:
        """전투 중 공격 액션 실행"""
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

        # 공격 대상 선택 (첫 번째 생존 몬스터)
        alive_monsters = combat.get_alive_monsters()
        if not alive_monsters:
            return self.create_error_result("공격할 몬스터가 없습니다.")

        target = alive_monsters[0]

        # 공격 실행
        result = await self.combat_handler.process_player_action(
            combat_id, session.player.id, CombatAction.ATTACK, target.id
        )

        if not result.get("success"):
            return self.create_error_result(result.get("message", "공격 실패"))

        # 공격 메시지 먼저 저장
        attack_message = result.get("message", "")

        # 전투 종료 확인 - combat.is_combat_over()를 직접 확인
        if combat.is_combat_over():
            # 공격 메시지와 함께 전투 종료 처리
            end_result = await self._end_combat(session, combat, result)
            # 공격 메시지를 승리 메시지 앞에 추가
            if attack_message:
                combined_message = f"{attack_message}\n\n{end_result.message}"
                end_result.message = combined_message
            return end_result

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

            # 전투 종료 확인 - combat.is_combat_over()를 직접 확인
            if combat.is_combat_over():
                # 공격 메시지와 몬스터 메시지를 포함한 전투 종료 처리
                end_result = await self._end_combat(session, combat, monster_result)
                # 모든 메시지를 승리 메시지 앞에 추가
                all_messages = [attack_message] + monster_messages
                combined_message = (
                    "\n".join(filter(None, all_messages)) + f"\n\n{end_result.message}"
                )
                end_result.message = combined_message
                return end_result

        # 전투 종료 재확인 - combat.is_combat_over() 직접 확인
        if combat.is_combat_over():
            # 공격 메시지와 몬스터 메시지를 포함한 전투 종료 처리
            end_result = await self._end_combat(session, combat, {})
            # 모든 메시지를 승리 메시지 앞에 추가
            all_messages = [attack_message] + monster_messages
            combined_message = (
                "\n".join(filter(None, all_messages)) + f"\n\n{end_result.message}"
            )
            end_result.message = combined_message
            return end_result

        # 다음 턴 메시지
        locale = session.player.preferred_locale if session.player else "ko"
        message = f"{attack_message}\n"

        # 몬스터 턴 메시지 추가
        if monster_messages:
            message += "\n" + "\n".join(monster_messages) + "\n"

        message += "\n" + self._get_combat_status_message(combat, locale)
        message += "\n\n"
        message += self._get_turn_message(combat, session.player.id, locale)

        return self.create_success_result(
            message=message,
            data={"action": "combat_action_result", "combat_status": combat.to_dict()},
        )

    async def _process_monster_turns(self, combat: CombatInstance) -> None:
        """몬스터 턴들을 자동으로 처리"""
        while combat.is_active and not combat.is_combat_over():
            current = combat.get_current_combatant()
            if not current:
                break

            # 플레이어 턴이면 중단
            from ..game.combat import CombatantType

            if current.combatant_type == CombatantType.PLAYER:
                break

            # 몬스터 턴 처리
            await self.combat_handler.process_monster_turn(combat.id)

    async def _end_combat(
        self, session: SessionType, combat: CombatInstance, result: dict
    ) -> CommandResult:
        """전투 종료 처리"""
        winners = combat.get_winners()
        # rewards = result.get('rewards', {'experience': 0, 'gold': 0, 'items': [], 'dropped_items': []})

        # 승리/패배 메시지
        from ..game.combat import CombatantType
        from ..core.localization import get_localization_manager

        localization = get_localization_manager()
        locale = session.player.preferred_locale if session.player else "en"

        player_won = any(w.combatant_type == CombatantType.PLAYER for w in winners)

        if player_won:
            # 보상 지급
            game_engine = getattr(session, "game_engine", None)

            # 죽은 몬스터들을 DB에 저장하고 아이템 드롭 처리
            if game_engine and game_engine.world_manager:
                for combatant in combat.combatants:
                    if (
                        combatant.combatant_type != CombatantType.PLAYER
                        and not combatant.is_alive()
                    ):
                        # 몬스터가 죽었으면 DB에 저장
                        try:
                            monster = await game_engine.world_manager.get_monster(
                                combatant.id
                            )
                            if monster and monster.is_alive:
                                monster.die()
                                await game_engine.world_manager.update_monster(monster)
                                logger.info(
                                    f"몬스터 {combatant.name} ({combatant.id}) 사망 처리 완료"
                                )
                        except Exception as e:
                            logger.error(f"몬스터 사망 처리 실패 ({combatant.id}): {e}")

            # TODO: 몹 > 아이템(컨테이너)이 되어 땅에 떨어짐
            # # 드롭된 아이템 처리
            # dropped_items_msg = []
            # if rewards.get('dropped_items'):
            #     from ..game.item_templates import ItemTemplateManager
            #     item_manager = ItemTemplateManager()

            #     for drop_info in rewards['dropped_items']:
            #         if drop_info.get('location') == 'inventory':
            #             # 플레이어 인벤토리에 직접 추가
            #             template_id = drop_info.get('template_id')
            #             if template_id and game_engine:
            #                 item_data = item_manager.create_item(
            #                     template_id=template_id,
            #                     location_type="inventory",
            #                     location_id=session.player.id,
            #                     quantity=drop_info.get('quantity', 1)
            #                 )
            #                 if item_data:
            #                     await game_engine.world_manager.create_game_object(item_data)
            #                     item_name = drop_info.get(f'name_{locale}', drop_info.get('name_ko', 'Unknown Item'))
            #                     dropped_items_msg.append(
            #                         localization.get_message("combat.item_inventory", locale,
            #                                                name=item_name,
            #                                                quantity=drop_info.get('quantity', 1))
            #                     )
            #                     logger.info(
            #                         f"플레이어 {session.player.username}이(가) "
            #                         f"{drop_info['name_ko']} {drop_info.get('quantity', 1)}개 획득"
            #                     )
            #                 else:
            #                     # 템플릿이 없어서 아이템 생성 실패
            #                     item_name = drop_info.get(f'name_{locale}', drop_info.get('name_ko', 'Unknown Item'))
            #                     await session.send_message({
            #                         "type": "room_message",
            #                         "message": localization.get_message("item.disappeared", locale, item=item_name)
            #                     })
            #                     logger.error(f"아이템 드롭 실패 - 템플릿 없음: {template_id}")
            #         elif drop_info.get('location') == 'ground':
            #             # 땅에 떨어진 아이템
            #             item_name = drop_info.get(f'name_{locale}', drop_info.get('name_ko', 'Unknown Item'))
            #             dropped_items_msg.append(
            #                 localization.get_message("combat.item_ground", locale,
            #                                         name=item_name,
            #                                         quantity=drop_info.get('quantity', 1))
            #             )

            # 승리 메시지 생성
            message = f"{ANSIColors.RED}{localization.get_message('combat.victory_message', locale)}{ANSIColors.RESET}"

            # if dropped_items_msg:
            #     message += f"\n\n" + "\n".join(dropped_items_msg)

            message += (
                f"\n\n{localization.get_message('combat.returning_location', locale)}"
            )
        else:
            message = f"{ANSIColors.RED}{localization.get_message('combat.defeat_message', locale)}{ANSIColors.RESET}\n\n{localization.get_message('combat.returning_location', locale)}"

        # 원래 방으로 복귀
        original_room_id = getattr(session, "original_room_id", None)
        if original_room_id:
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
            message=message.strip(),
            data={"action": "combat_end", "victory": player_won},
        )

    def _get_combat_status_message(
        self, combat: CombatInstance, locale: str = "ko"
    ) -> str:
        """전투 상태 메시지 생성"""
        from ..core.localization import get_localization_manager

        localization = get_localization_manager()

        lines = ["━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
        lines.append(f"{ANSIColors.RED}")
        lines.append(
            localization.get_message("combat.round", locale, round=combat.turn_number)
        )
        lines.append(f"{ANSIColors.RESET}")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # 플레이어 정보
        players = combat.get_alive_players()
        if players:
            player = players[0]
            lines.append(f"\n👤 {player.name} HP: {player.current_hp}/{player.max_hp}")

        # 몬스터 정보
        monsters = combat.get_alive_monsters()
        if monsters:
            for monster in monsters:
                # 몬스터 이름을 언어별로 동적 조회
                monster_name = monster.name  # 기본값
                if monster.data and "monster" in monster.data:
                    monster_obj = monster.data["monster"]
                    monster_name = monster_obj.get_localized_name(locale)

                lines.append(
                    f"👹 {monster_name}: HP: {monster.current_hp}/{monster.max_hp}"
                )

        lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)

    def _get_turn_message(
        self, combat: CombatInstance, player_id: str, locale: str = "en"
    ) -> str:
        """턴 메시지 생성"""
        from ..core.localization import get_localization_manager

        localization = get_localization_manager()

        current = combat.get_current_combatant()
        if not current:
            return ""

        if current.id == player_id:
            return f"""
{localization.get_message("combat.your_turn", locale)}

1️⃣ {localization.get_message("combat.action_attack", locale)}
2️⃣ {localization.get_message("combat.action_defend", locale)}
3️⃣ {localization.get_message("combat.action_flee", locale)}

{localization.get_message("combat.enter_command", locale)}"""
        else:
            if locale == "ko":
                return (
                    f"{ANSIColors.RED}⏳ {current.name}의 턴입니다...{ANSIColors.RESET}"
                )
            else:
                return f"{ANSIColors.RED}⏳ {current.name}'s turn...{ANSIColors.RESET}"

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

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        if not getattr(session, "in_combat", False):
            return self.create_error_result("전투 중이 아닙니다.")

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
        locale = session.player.preferred_locale if session.player else "ko"
        message = f"{result.get('message', '')}\n"

        # 몬스터 턴 메시지 추가
        if monster_messages:
            message += "\n" + "\n".join(monster_messages) + "\n"

        message += "\n" + attack_cmd._get_combat_status_message(combat, locale)
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

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        if not getattr(session, "in_combat", False):
            return self.create_error_result("전투 중이 아닙니다.")

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

                from ..core.localization import get_localization_manager

                localization = get_localization_manager()
                locale = session.player.preferred_locale if session.player else "en"

                if not exit_directions or len(exit_directions) == 0:
                    # 출구가 없으면 원래 방으로 복귀
                    session.current_room_id = original_room_id
                    flee_message = f"{localization.get_message('combat.flee_success', locale)}\n\n{localization.get_message('combat.return_location', locale)}"
                else:
                    # 랜덤 출구 선택
                    import random

                    random_direction = random.choice(exit_directions)
                    target_room = await game_engine.world_manager.get_room(
                        random_direction.id
                    )
                    session.current_room_id = target_room.id
                    flee_message = f"{localization.get_message('combat.flee_success', locale)}\n\n{random_direction.direction} 방향으로 도망쳐 {target_room.get_localized_description(locale)}에 도착했습니다."

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

                from ..core.localization import get_localization_manager

                localization = get_localization_manager()
                locale = session.player.preferred_locale if session.player else "en"

                return self.create_success_result(
                    message=f"{localization.get_message('combat.flee_success', locale)}\n\n{localization.get_message('combat.return_location', locale)}",
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
        locale = session.player.preferred_locale if session.player else "ko"
        message = f"{result.get('message', '')}\n"

        # 몬스터 턴 메시지 추가
        if monster_messages:
            message += "\n" + "\n".join(monster_messages) + "\n"

        message += "\n" + attack_cmd._get_combat_status_message(combat, locale)
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
        locale = session.player.preferred_locale if session.player else "ko"
        message = attack_cmd._get_combat_status_message(combat, locale)
        message += "\n\n"
        message += attack_cmd._get_turn_message(combat, session.player.id, locale)

        return self.create_success_result(
            message=message,
            data={"action": "combat_status", "combat_status": combat.to_dict()},
        )
