# -*- coding: utf-8 -*-
"""둘러보기 명령어"""

import logging
from typing import List

from ..base import BaseCommand, CommandResult, CommandResultType
from ...core.types import SessionType
from ...core.localization import get_localization_manager
from ...server.telnet_session import TelnetSession

logger = logging.getLogger(__name__)


class LookCommand(BaseCommand):

    def __init__(self):
        super().__init__(
            name="look",
            aliases=["l"],
            description="주변을 둘러보거나 특정 대상을 자세히 살펴봅니다",
            usage="look [대상]"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not args:
            # 방 전체 둘러보기
            return await self._look_around(session)
        else:
            # 특정 대상 살펴보기
            target = " ".join(args)
            return await self._look_at(session, target)  # target 은 idx 여야 함
            # TODO: 아이템도 볼 수 있어야 함

    async def _look_around(self, session: SessionType) -> CommandResult:
        """방 전체 둘러보기 - 방 정보를 다시 전송"""
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        logger.info("===== invoked ")
#         # 전투 중인 경우 전투 상태 표시
#         if getattr(session, 'in_combat', False):
#             combat_id = getattr(session, 'combat_id', None)
#             if combat_id:
#                 game_engine = getattr(session, 'game_engine', None)
#                 if game_engine:
#                     combat = game_engine.combat_manager.get_combat(combat_id)
#                     if combat and combat.is_active:
#                         # 전투 상태 포맷팅
#                         from ..core.managers.player_movement_manager import PlayerMovementManager
#                         movement_mgr = game_engine.movement_manager
#                         combat_status = movement_mgr._format_combat_status(combat)

#                         current = combat.get_current_combatant()
#                         from ..core.localization import get_localization_manager
#                         localization = get_localization_manager()
#                         locale = session.player.preferred_locale if session.player else "en"

#                         if current and current.id == session.player.id:
#                             turn_info = f"""

# {localization.get_message("combat.your_turn", locale)}

# 1️⃣ {localization.get_message("combat.action_attack", locale)}
# 2️⃣ {localization.get_message("combat.action_defend", locale)}
# 3️⃣ {localization.get_message("combat.action_flee", locale)}

# {localization.get_message("combat.enter_command", locale)}"""
#                         else:
#                             turn_info = f"\n\n⏳ {current.name}의 턴입니다..."

#                         return self.create_success_result(
#                             message=f"{combat_status}{turn_info}",
#                             data={"action": "look_combat", "combat_id": combat_id}
#                         )
        # ===== TODO: 위의 내용은 위치 이동 - 재활용

        # 현재 방 ID 가져오기 (전투 중이면 원래 방 사용)
        current_room_id = getattr(session, 'current_room_id', None)
        if getattr(session, 'in_combat', False):
            current_room_id = getattr(session, 'original_room_id', current_room_id)
        if not current_room_id:
            return self.create_error_result("현재 위치를 확인할 수 없습니다.")

        try:
            # 게임 엔진을 통해 방 정보를 다시 전송
            game_engine = getattr(session, 'game_engine', None)
            if not game_engine:
                return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

            # 방 정보를 플레이어에게 전송
            await game_engine.movement_manager.send_room_info_to_player(session, current_room_id)

            # 다국어 메시지 사용
            localization = get_localization_manager()
            locale = session.player.preferred_locale if session.player else "en"

            return self.create_success_result(
                message=localization.get_message("look.refresh", locale),
                data={
                    "action": "look_refresh",
                    "room_id": current_room_id
                }
            )

        except Exception as e:
            logger.error(f"방 둘러보기 중 오류: {e}")
            localization = get_localization_manager()
            locale = session.player.preferred_locale if session.player else "en"
            return self.create_error_result(localization.get_message("look.error", locale))

    async def _look_at(self, session: SessionType, target: str) -> CommandResult:
        """엔티티 번호로 대상 살펴보기"""
        if not target.isdigit():
            return self.create_info_result(
                f"'{target}'을(를) 찾을 수 없습니다."
            )

        entity_number = int(target)
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        # 세션에서 entity_map 가져오기
        entity_map = getattr(session, 'room_entity_map', {})
        if not entity_map:
            return self.create_error_result("방 정보를 찾을 수 없습니다.")

        # 해당 번호의 엔티티 찾기
        if entity_number not in entity_map:
            return self.create_error_result(f"'{entity_number}'번 대상을 찾을 수 없습니다.")

        entity_info = entity_map[entity_number]
        entity_type = entity_info.get('type')
        entity_id = entity_info.get('id')
        entity_name = entity_info.get('name', '알 수 없음')

        try:
            game_engine = getattr(session, 'game_engine', None)
            if not game_engine:
                return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

            locale = session.player.preferred_locale if session.player else "en"

            # 몬스터 정보 조회
            monster = await game_engine.world_manager.get_monster(entity_id)

            if not monster:
                return self.create_error_result(f"몬스터 정보를 찾을 수 없습니다.")

            # 몬스터 설명 가져오기
            description = monster.get_localized_description(locale)
            if not description:
                description = "특별한 설명이 없습니다."

            # 몬스터 상태 정보
            hp_info = f"HP: {monster.current_hp}/{monster.max_hp}"
            level_info = f"레벨: {monster.level}"

            # 몬스터 태도 정보
            attitude_info = ""
            if monster.is_aggressive():
                attitude_info = "\n⚔️ 공격형입니다."
            elif monster.is_passive():
                attitude_info = "\n🕊️ 수동형입니다."
            elif monster.is_neutral():
                attitude_info = "\n😐 중립적입니다."

            response = "\n".join([
                entity_name,
                "=" * 40,
                description,
                f"{hp_info} | {level_info}{attitude_info}",
                "📊 능력치:",
                f"  • 힘 (STR): {monster.stats.strength}",
                f"  • 민첩 (DEX): {monster.stats.dexterity}",
                f"  • 체력 (CON): {monster.stats.constitution}",
                f"  • 지능 (INT): {monster.stats.intelligence}",
                f"  • 지혜 (WIS): {monster.stats.wisdom}",
                f"  • 매력 (CHA): {monster.stats.charisma}",
                monster.faction_id,
            ])

        # 종족 정보
        # if monster.faction_id:
        #     lines.append("")
        #     lines.append(f"🏴 종족: {monster.faction_id}")

        # 행동 패턴
        # if hasattr(monster, 'monster_type'):
        #     lines.append("")
        #     monster_type_str = monster.monster_type.value if hasattr(monster.monster_type, 'value') else str(monster.monster_type)
        #     lines.append(f"⚔️ 성향: {monster_type_str}")

            return self.create_success_result(
                message=response,
                data={
                    "action": "look_at",
                    "target": entity_name,
                    "target_type": "monster",
                    "entity_id": entity_id
                }
            )

        except Exception as e:
            logger.error(f"엔티티 조회 중 오류: {e}")
            return self.create_error_result("대상을 조회하는 중 오류가 발생했습니다.")
