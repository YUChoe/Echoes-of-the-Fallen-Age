# -*- coding: utf-8 -*-
"""기본 게임 명령어들"""

import logging
from typing import List

from .base import BaseCommand, CommandResult, CommandResultType
from ..core.types import SessionType

logger = logging.getLogger(__name__)


class MoveCommand(BaseCommand):
    """이동 명령어 (방향별)"""

    def __init__(self, direction: str, aliases: List[str] = None):   # pyright: ignore[reportArgumentType]
        self.direction = direction
        super().__init__(
            name=direction,
            aliases=aliases or [],
            description=f"{direction} 방향으로 이동합니다",
            usage=direction
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        # 전투 중에는 이동 불가
        if getattr(session, 'in_combat', False):
            from ..core.localization import get_localization_manager
            localization = get_localization_manager()
            locale = session.player.preferred_locale if session.player else "en"
            return self.create_error_result(localization.get_message("movement.combat_blocked", locale))

        # 현재 방 ID 가져오기 (세션에서 또는 캐릭터에서)
        current_room_id = getattr(session, 'current_room_id', None)
        if not current_room_id:
            from ..core.localization import get_localization_manager
            localization = get_localization_manager()
            locale = session.player.preferred_locale if session.player else "en"
            return self.create_error_result(localization.get_message("movement.no_location", locale))

        # GameEngine을 통해 이동 처리
        from ..core.game_engine import GameEngine
        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

        try:
            # 좌표 기반 이동 시스템 사용
            success = await game_engine.movement_manager.move_player_by_direction(session, self.direction)

            if success:
                # 이동 성공 - 이동 메시지는 move_player_by_direction에서 이미 전송됨
                return self.create_success_result("")
            else:
                # 이동 실패 - 에러 메시지는 move_player_by_direction에서 이미 전송됨
                return self.create_error_result("")

        except Exception as e:
            logger.error(f"이동 명령어 실행 중 오류: {e}")
            from ..core.localization import get_localization_manager
            localization = get_localization_manager()
            locale = session.player.preferred_locale if session.player else "en"
            return self.create_error_result(localization.get_message("error.generic", locale))


class StatsCommand(BaseCommand):
    """능력치 확인 명령어"""

    def __init__(self):
        super().__init__(
            name="stats",
            aliases=["status", "st", "attributes"],
            description="플레이어의 능력치와 상태를 확인합니다",
            usage="stats [상세]"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        try:
            player = session.player
            stats = player.stats

            # 상세 모드 확인
            detailed = len(args) > 0 and args[0].lower() in ['상세', 'detail', 'detailed', 'full']

            if detailed:
                # 상세 능력치 표시
                response = await self._format_detailed_stats(player, stats, session)
            else:
                # 기본 능력치 표시
                response = await self._format_basic_stats(player, stats, session)

            return self.create_success_result(
                message=response,
                data={
                    "action": "stats",
                    "detailed": detailed,
                    "stats": stats.get_all_stats(),
                    "player_name": player.username
                }
            )

        except Exception as e:
            logger.error(f"능력치 확인 명령어 실행 중 오류: {e}")
            return self.create_error_result("능력치 정보를 확인하는 중 오류가 발생했습니다.")

    async def _format_basic_stats(self, player, stats, session) -> str:
        """기본 능력치 표시 형식 (장비 정보 포함)"""
        from ..game.stats import StatType
        from ..core.localization import get_localization_manager

        # 로케일 설정
        locale = getattr(session.player, 'preferred_locale', 'ko') if session.player else 'ko'
        localization = get_localization_manager()

        # 장비 정보 가져오기
        equipment_display = await self._get_equipment_display(session)

        # 다국어 텍스트
        if locale == 'ko':
            title = f"📊 {player.username}의 능력치"
            basic_info = "🎯 기본 정보:"
            primary_stats = "💪 1차 능력치:"
            main_stats = "❤️ 주요 스탯:"
            combat_stats = "⚔️ 전투 능력:"
            misc_info = "💼 기타:"
            detail_tip = "💡 상세한 정보를 보려면 'stats 상세'를 입력하세요."
            level_text = "레벨"
            max_weight_text = "최대 소지무게"
        else:
            title = f"📊 {player.username}'s Stats"
            basic_info = "🎯 Basic Info:"
            primary_stats = "💪 Primary Stats:"
            main_stats = "❤️ Main Stats:"
            combat_stats = "⚔️ Combat Stats:"
            misc_info = "💼 Misc:"
            detail_tip = "💡 Type 'stats detail' for more information."
            level_text = "Level"
            max_weight_text = "Max Carry Weight"

        # 80칼럼 활용한 2열 배치
        str_val = stats.get_primary_stat(StatType.STR)
        dex_val = stats.get_primary_stat(StatType.DEX)
        int_val = stats.get_primary_stat(StatType.INT)
        wis_val = stats.get_primary_stat(StatType.WIS)
        con_val = stats.get_primary_stat(StatType.CON)
        cha_val = stats.get_primary_stat(StatType.CHA)

        hp_val = stats.get_secondary_stat(StatType.HP)
        mp_val = stats.get_secondary_stat(StatType.MP)
        sta_val = stats.get_secondary_stat(StatType.STA)
        atk_val = stats.get_secondary_stat(StatType.ATK)
        def_val = stats.get_secondary_stat(StatType.DEF)
        spd_val = stats.get_secondary_stat(StatType.SPD)

        response = f"""{title}

{basic_info}
• {level_text}: {stats.level}

{primary_stats}
• STR: {str_val:2d}    • DEX: {dex_val:2d}    • INT: {int_val:2d}
• WIS: {wis_val:2d}    • CON: {con_val:2d}    • CHA: {cha_val:2d}

{main_stats}
• HP: {hp_val:3d}      • MP: {mp_val:3d}      • STA: {sta_val:3d}

{combat_stats}
• ATK: {atk_val:2d}     • DEF: {def_val:2d}     • SPD: {spd_val:2d}

{misc_info}
• {max_weight_text}: {stats.get_max_carry_weight()}kg

{equipment_display}

{detail_tip}"""

        return response

    async def _format_detailed_stats(self, player, stats, session) -> str:
        """상세 능력치 표시 형식"""
        from ..game.stats import StatType

        # 로케일 설정
        locale = getattr(session.player, 'preferred_locale', 'ko') if session.player else 'ko'

        # 장비 보너스 정보
        equipment_info = ""
        if stats.equipment_bonuses:
            if locale == 'ko':
                equipment_info = "\n🎒 장비 보너스:\n"
            else:
                equipment_info = "\n🎒 Equipment Bonuses:\n"
            for stat_name, bonus in stats.equipment_bonuses.items():
                if bonus > 0:
                    equipment_info += f"• {stat_name}: +{bonus}\n"

        # 다국어 텍스트
        if locale == 'ko':
            title = f"📊 {player.username}의 상세 능력치"
            basic_info = "🎯 기본 정보:"
            primary_stats = "💪 1차 능력치 (기본 스탯):"
            secondary_stats = "❤️ 2차 능력치 (파생 스탯):"
            misc_info = "💼 기타 정보:"
            formulas = "📈 능력치 계산 공식:"
            level_text = "레벨"
            base_text = "기본"
            max_weight_text = "최대 소지무게"
        else:
            title = f"📊 {player.username}'s Detailed Stats"
            basic_info = "🎯 Basic Info:"
            primary_stats = "💪 Primary Stats (Base):"
            secondary_stats = "❤️ Secondary Stats (Derived):"
            misc_info = "💼 Misc Info:"
            formulas = "📈 Stat Calculation Formulas:"
            level_text = "Level"
            base_text = "base"
            max_weight_text = "Max Carry Weight"

        # 능력치 값들
        str_total = stats.get_primary_stat(StatType.STR)
        dex_total = stats.get_primary_stat(StatType.DEX)
        int_total = stats.get_primary_stat(StatType.INT)
        wis_total = stats.get_primary_stat(StatType.WIS)
        con_total = stats.get_primary_stat(StatType.CON)
        cha_total = stats.get_primary_stat(StatType.CHA)

        hp_val = stats.get_secondary_stat(StatType.HP)
        mp_val = stats.get_secondary_stat(StatType.MP)
        sta_val = stats.get_secondary_stat(StatType.STA)
        atk_val = stats.get_secondary_stat(StatType.ATK)
        def_val = stats.get_secondary_stat(StatType.DEF)
        spd_val = stats.get_secondary_stat(StatType.SPD)
        res_val = stats.get_secondary_stat(StatType.RES)
        lck_val = stats.get_secondary_stat(StatType.LCK)
        inf_val = stats.get_secondary_stat(StatType.INF)

        # 공식 텍스트
        if locale == 'ko':
            formula_text = """• HP = 100 + (체력 × 5) + (레벨 × 10)
• MP = 50 + (지능 × 3) + (지혜 × 2) + (레벨 × 5)
• ATK = 10 + (힘 × 2) + 레벨
• DEF = 5 + (체력 × 1.5) + (레벨 × 0.5)
• SPD = 10 + (민첩 × 1.5)"""
        else:
            formula_text = """• HP = 100 + (CON × 5) + (Level × 10)
• MP = 50 + (INT × 3) + (WIS × 2) + (Level × 5)
• ATK = 10 + (STR × 2) + Level
• DEF = 5 + (CON × 1.5) + (Level × 0.5)
• SPD = 10 + (DEX × 1.5)"""

        response = f"""{title}

{basic_info}
• {level_text}: {stats.level}

{primary_stats}
• STR: {str_total:2d} ({base_text}: {stats.strength:2d})    • DEX: {dex_total:2d} ({base_text}: {stats.dexterity:2d})
• INT: {int_total:2d} ({base_text}: {stats.intelligence:2d})    • WIS: {wis_total:2d} ({base_text}: {stats.wisdom:2d})
• CON: {con_total:2d} ({base_text}: {stats.constitution:2d})    • CHA: {cha_total:2d} ({base_text}: {stats.charisma:2d})

{secondary_stats}
• HP: {hp_val:3d}    • MP: {mp_val:3d}    • STA: {sta_val:3d}
• ATK: {atk_val:2d}     • DEF: {def_val:2d}     • SPD: {spd_val:2d}
• RES: {res_val:2d}     • LCK: {lck_val:2d}     • INF: {inf_val:2d}

{misc_info}
• {max_weight_text}: {stats.get_max_carry_weight()}kg{equipment_info}

{formulas}
{formula_text}"""

        return response
    async def _get_equipment_display(self, session) -> str:
        """장비 상태 표시 - 모든 슬롯을 2열 레이아웃으로 표시"""
        try:
            # GameEngine 접근
            game_engine = getattr(session, 'game_engine', None)
            if not game_engine or not session.player:
                return ""

            # 착용 중인 장비들 조회
            equipped_items = await game_engine.world_manager.get_equipped_objects(session.player.id)

            # 로케일 설정
            locale = getattr(session.player, 'preferred_locale', 'ko') if session.player else 'ko'

            # 부위별 장착 상태 매핑
            equipment_slots = self._get_equipment_slots_display(locale)
            equipped_by_slot = {}

            for item in equipped_items:
                if item.equipment_slot:
                    equipped_by_slot[item.equipment_slot] = item

            # 다국어 텍스트
            if locale == 'ko':
                title = "⚔️ 장비 상태:"
                equipped_suffix = " ← 착용됨"
            else:
                title = "⚔️ Equipment Status:"
                equipped_suffix = " ← Equipped"

            # 슬롯 순서 정의 (2열 배치용)
            slot_order = [
                'head', 'right_arm',
                'shoulder', 'left_arm',
                'chest', 'right_hand',
                'left_hand', 'waist',
                'legs', 'feet',
                'back', None  # None으로 홀수 개수 처리
            ]

            response = f"{title}\n"

            # 2열로 배치
            for i in range(0, len(slot_order), 2):
                left_slot = slot_order[i]
                right_slot = slot_order[i + 1] if i + 1 < len(slot_order) else None

                # 왼쪽 슬롯
                if left_slot and left_slot in equipment_slots:
                    slot_info = equipment_slots[left_slot]
                    slot_icon = slot_info['icon']
                    slot_name = slot_info['name']

                    if left_slot in equipped_by_slot:
                        item = equipped_by_slot[left_slot]
                        item_name = item.get_localized_name(locale)
                        left_text = f"{slot_icon} {slot_name} ← {item_name}"
                    else:
                        left_text = f"{slot_icon} {slot_name}"
                else:
                    left_text = ""

                # 오른쪽 슬롯
                if right_slot and right_slot in equipment_slots:
                    slot_info = equipment_slots[right_slot]
                    slot_icon = slot_info['icon']
                    slot_name = slot_info['name']

                    if right_slot in equipped_by_slot:
                        item = equipped_by_slot[right_slot]
                        item_name = item.get_localized_name(locale)
                        right_text = f"{slot_icon} {slot_name} ← {item_name}"
                    else:
                        right_text = f"{slot_icon} {slot_name}"
                else:
                    right_text = ""

                # 2열 배치 (40칼럼씩)
                if right_text:
                    response += f"{left_text:<40} {right_text}\n"
                else:
                    response += f"{left_text}\n"

            return response.strip()

        except Exception as e:
            logger.error(f"장비 정보 표시 중 오류: {e}")
            locale = getattr(session.player, 'preferred_locale', 'ko') if session.player else 'ko'
            if locale == 'ko':
                return "⚔️ 장비: 정보를 불러올 수 없습니다."
            else:
                return "⚔️ Equipment: Unable to load information."

    def _get_equipment_slots_display(self, locale: str = 'ko') -> dict:
        """부위별 장비 슬롯 표시 정보"""
        if locale == 'ko':
            return {
                'head': {'name': '머리', 'icon': '🪖'},
                'shoulder': {'name': '어깨', 'icon': '🛡️'},
                'chest': {'name': '가슴', 'icon': '👕'},
                'right_arm': {'name': '오른팔', 'icon': '🦾'},
                'left_arm': {'name': '왼팔', 'icon': '🦾'},
                'right_hand': {'name': '오른손', 'icon': '⚔️'},
                'left_hand': {'name': '왼손', 'icon': '🛡️'},
                'waist': {'name': '허리', 'icon': '🔗'},
                'legs': {'name': '다리', 'icon': '👖'},
                'feet': {'name': '발', 'icon': '👢'},
                'back': {'name': '등', 'icon': '🎒'}
            }
        else:  # English
            return {
                'head': {'name': 'Head', 'icon': '🪖'},
                'shoulder': {'name': 'Shoulder', 'icon': '🛡️'},
                'chest': {'name': 'Chest', 'icon': '👕'},
                'right_arm': {'name': 'Right Arm', 'icon': '🦾'},
                'left_arm': {'name': 'Left Arm', 'icon': '🦾'},
                'right_hand': {'name': 'Right Hand', 'icon': '⚔️'},
                'left_hand': {'name': 'Left Hand', 'icon': '🛡️'},
                'waist': {'name': 'Waist', 'icon': '🔗'},
                'legs': {'name': 'Legs', 'icon': '👖'},
                'feet': {'name': 'Feet', 'icon': '👢'},
                'back': {'name': 'Back', 'icon': '🎒'}
            }