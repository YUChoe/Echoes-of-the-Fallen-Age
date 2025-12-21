# -*- coding: utf-8 -*-
"""조사 관련 명령어들"""

import logging
from typing import List

from .base import BaseCommand, CommandResult
from ..core.types import SessionType

logger = logging.getLogger(__name__)


class InspectCommand(BaseCommand):
    """엔티티 조사 명령어"""

    def __init__(self):
        super().__init__(
            name="inspect",
            aliases=["조사", "examine", "ex"],
            description="몬스터나 NPC의 상세 정보를 확인합니다",
            usage="inspect <번호 또는 이름>"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        """조사 실행"""
        try:
            if not args:
                return self.create_error_result("무엇을 조사하시겠습니까? 사용법: inspect <번호 또는 이름>")

            target_input = " ".join(args)

            # GameEngine을 통해 정보 조회
            game_engine = getattr(session, 'game_engine', None)
            if not game_engine:
                return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

            # 번호로 입력된 경우 처리
            target_entity = None
            entity_type = None

            if target_input.isdigit():
                entity_num = int(target_input)
                entity_map = getattr(session, 'room_entity_map', {})

                if entity_num in entity_map:
                    entity_info = entity_map[entity_num]
                    target_entity = entity_info['entity']
                    entity_type = entity_info['type']
                else:
                    return self.create_error_result(
                        f"번호 [{entity_num}]에 해당하는 대상을 찾을 수 없습니다."
                    )
            else:
                # 이름으로 검색 - 몬스터 먼저
                target_name = target_input.lower()
                monsters = await game_engine.world_manager.get_monsters_in_room(session.current_room_id)

                for monster in monsters:
                    if (target_name in monster.get_localized_name(session.locale).lower() or
                        target_name in monster.get_localized_name('en').lower() or
                        target_name in monster.get_localized_name('ko').lower()):
                        target_entity = monster
                        entity_type = 'monster'
                        break

                # 몬스터를 못 찾았으면 NPC 검색
                if not target_entity:
                    npcs = await game_engine.model_manager.npcs.get_npcs_in_room(session.current_room_id)
                    for npc in npcs:
                        if (target_name in npc.get_localized_name(session.locale).lower() or
                            target_name in npc.get_localized_name('en').lower() or
                            target_name in npc.get_localized_name('ko').lower()):
                            target_entity = npc
                            entity_type = 'npc'
                            break

            if not target_entity:
                return self.create_error_result(f"'{target_input}'을(를) 찾을 수 없습니다.")

            # 엔티티 정보 포맷팅
            if entity_type == 'monster':
                message = self._format_monster_info(target_entity, session.locale)
            else:
                message = self._format_npc_info(target_entity, session.locale)

            return self.create_success_result(message)

        except Exception as e:
            logger.error(f"조사 명령어 실행 실패: {e}", exc_info=True)
            return self.create_error_result("조사 중 오류가 발생했습니다.")

    def _format_monster_info(self, monster, locale: str) -> str:
        """몬스터 정보 포맷팅"""
        name = monster.get_localized_name(locale)
        desc = monster.get_localized_description(locale)

        lines = [
            f"🔍 {name}",
            "=" * 40,
            f"{desc}",
            "",
            f"💚 HP: {monster.current_hp}/{monster.max_hp}",
            f"⭐ 레벨: {monster.level}",
            "",
            "📊 능력치:",
            f"  • 힘 (STR): {monster.stats.strength}",
            f"  • 민첩 (DEX): {monster.stats.dexterity}",
            f"  • 체력 (CON): {monster.stats.constitution}",
            f"  • 지능 (INT): {monster.stats.intelligence}",
            f"  • 지혜 (WIS): {monster.stats.wisdom}",
            f"  • 매력 (CHA): {monster.stats.charisma}",
        ]

        # 종족 정보
        if monster.faction_id:
            lines.append("")
            lines.append(f"🏴 종족: {monster.faction_id}")

        # 행동 패턴
        if hasattr(monster, 'monster_type'):
            lines.append("")
            monster_type_str = monster.monster_type.value if hasattr(monster.monster_type, 'value') else str(monster.monster_type)
            lines.append(f"⚔️ 성향: {monster_type_str}")

        return "\n".join(lines)

    def _format_npc_info(self, npc, locale: str) -> str:
        """NPC 정보 포맷팅"""
        name = npc.get_localized_name(locale)
        desc = npc.get_localized_description(locale)

        lines = [
            f"🔍 {name}",
            "=" * 40,
            f"{desc}",
            "",
        ]

        # NPC 타입
        if npc.npc_type:
            lines.append(f"👤 역할: {npc.npc_type}")

        # 상인 여부
        if npc.is_merchant():
            lines.append("💰 상인입니다")
            lines.append("  'shop' 명령어로 상품을 확인할 수 있습니다")

        return "\n".join(lines)
