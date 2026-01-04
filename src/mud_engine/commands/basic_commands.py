# -*- coding: utf-8 -*-
"""기본 게임 명령어들"""

import logging
from typing import List

from .base import BaseCommand, CommandResult, CommandResultType
from ..core.types import SessionType

logger = logging.getLogger(__name__)


class LookCommand(BaseCommand):
    """둘러보기 명령어"""

    def __init__(self):
        super().__init__(
            name="look",
            aliases=["l", "examine"],
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
            return await self._look_at(session, target)

    async def _look_around(self, session: SessionType) -> CommandResult:
        """방 전체 둘러보기 - 방 정보를 다시 전송"""
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        # 전투 중인 경우 전투 상태 표시
        if getattr(session, 'in_combat', False):
            combat_id = getattr(session, 'combat_id', None)
            if combat_id:
                game_engine = getattr(session, 'game_engine', None)
                if game_engine:
                    combat = game_engine.combat_manager.get_combat(combat_id)
                    if combat and combat.is_active:
                        # 전투 상태 포맷팅
                        from ..core.managers.player_movement_manager import PlayerMovementManager
                        movement_mgr = game_engine.movement_manager
                        combat_status = movement_mgr._format_combat_status(combat)

                        current = combat.get_current_combatant()
                        from ..core.localization import get_localization_manager
                        localization = get_localization_manager()
                        locale = session.player.preferred_locale if session.player else "en"

                        if current and current.id == session.player.id:
                            turn_info = f"""

{localization.get_message("combat.your_turn", locale)}

1️⃣ {localization.get_message("combat.action_attack", locale)}
2️⃣ {localization.get_message("combat.action_defend", locale)}
3️⃣ {localization.get_message("combat.action_flee", locale)}

{localization.get_message("combat.enter_command", locale)}"""
                        else:
                            turn_info = f"\n\n⏳ {current.name}의 턴입니다..."

                        return self.create_success_result(
                            message=f"{combat_status}{turn_info}",
                            data={"action": "look_combat", "combat_id": combat_id}
                        )

        # 현재 방 ID 가져오기
        current_room_id = getattr(session, 'current_room_id', None)
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
            from ..core.localization import get_localization_manager
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
            from ..core.localization import get_localization_manager
            localization = get_localization_manager()
            locale = session.player.preferred_locale if session.player else "en"
            return self.create_error_result(localization.get_message("look.error", locale))

    async def _look_at(self, session: SessionType, target: str) -> CommandResult:
        """특정 대상 살펴보기"""
        target_lower = target.lower()

        # 자기 자신 살펴보기
        if target_lower in ["me", "myself", session.player.username.lower()]:
            response = f"""
👤 {session.player.username}
당신은 이 신비로운 세계에 발을 들인 모험가입니다.
아직 여행을 시작한 지 얼마 되지 않아 평범한 옷을 입고 있습니다.
            """.strip()

            return self.create_success_result(
                message=response,
                data={
                    "action": "look_at",
                    "target": "self",
                    "target_type": "player"
                }
            )

        # 숫자 인자 처리 (엔티티 번호)
        if target.isdigit():
            entity_number = int(target)
            return await self._look_at_entity_by_number(session, entity_number)

        # 기타 대상들
        return self.create_info_result(
            f"'{target}'을(를) 찾을 수 없습니다."
        )

    async def _look_at_entity_by_number(self, session: SessionType, entity_number: int) -> CommandResult:
        """엔티티 번호로 대상 살펴보기"""
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

            if entity_type == 'npc':
                # NPC 정보 조회
                npc = await game_engine.world_manager.get_npc_by_id(entity_id)

                if not npc:
                    return self.create_error_result(f"NPC 정보를 찾을 수 없습니다.")

                # NPC 설명 가져오기
                description = npc.get_localized_description(locale)
                if not description:
                    description = "특별한 설명이 없습니다."

                # NPC 타입에 따른 추가 정보
                npc_type_info = ""
                if npc.is_merchant():
                    npc_type_info = "\n💰 이 NPC는 상인입니다. 'shop' 명령어로 거래할 수 있습니다."

                response = f"""
👤 {entity_name}
{description}{npc_type_info}
                """.strip()

                return self.create_success_result(
                    message=response,
                    data={
                        "action": "look_at",
                        "target": entity_name,
                        "target_type": "npc",
                        "entity_id": entity_id
                    }
                )

            elif entity_type == 'monster':
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
                    attitude_info = "\n⚔️ 이 몬스터는 공격적입니다."
                elif monster.is_passive():
                    attitude_info = "\n🕊️ 이 몬스터는 평화롭습니다."
                elif monster.is_neutral():
                    attitude_info = "\n😐 이 몬스터는 중립적입니다."

                response = f"""
🐾 {entity_name}
{description}

{hp_info} | {level_info}{attitude_info}
                """.strip()

                return self.create_success_result(
                    message=response,
                    data={
                        "action": "look_at",
                        "target": entity_name,
                        "target_type": "monster",
                        "entity_id": entity_id
                    }
                )

            else:
                return self.create_error_result(f"'{entity_number}'번은 살펴볼 수 없는 대상입니다.")

        except Exception as e:
            logger.error(f"엔티티 조회 중 오류: {e}")
            return self.create_error_result("대상을 조회하는 중 오류가 발생했습니다.")


class HelpCommand(BaseCommand):
    """도움말 명령어"""

    def __init__(self, command_processor=None):
        super().__init__(
            name="help",
            aliases=["?", "commands"],
            description="명령어 도움말을 표시합니다",
            usage="help [명령어]"
        )
        self.command_processor = command_processor

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not self.command_processor:
            return self.create_error_result("명령어 처리기가 설정되지 않았습니다.")

        # 전투 중인 경우 전투 명령어만 표시
        if getattr(session, 'in_combat', False):
            from ..core.localization import get_localization_manager
            localization = get_localization_manager()
            locale = session.player.preferred_locale if session.player else "en"

            combat_help = f"""
{localization.get_message("combat.help_title", locale)}

{localization.get_message("combat.help_attack", locale)}
{localization.get_message("combat.help_defend", locale)}
{localization.get_message("combat.help_flee", locale)}

{localization.get_message("combat.help_other", locale)}
• look - {localization.get_message("help.look_combat", locale, default="전투 상태 확인" if locale == "ko" else "Check combat status")}
• status - {localization.get_message("help.status", locale, default="능력치 확인" if locale == "ko" else "Check attributes")}
• combat - {localization.get_message("help.combat_detail", locale, default="전투 상태 상세 정보" if locale == "ko" else "Detailed combat information")}

💡 {localization.get_message("help.tip_numbers", locale, default="팁: 숫자만 입력해도 행동을 선택할 수 있습니다!" if locale == "ko" else "Tip: You can just enter numbers to select actions!")}
"""

            return self.create_success_result(
                message=combat_help.strip(),
                data={"action": "help_combat"}
            )

        # 플레이어의 관리자 권한 확인
        is_admin = False
        if session.player:
            is_admin = getattr(session.player, 'is_admin', False)

        if args:
            # 특정 명령어 도움말
            command_name = args[0]
            help_text = self.command_processor.get_help_text(command_name, is_admin)
        else:
            # 전체 명령어 목록
            help_text = self.command_processor.get_help_text(None, is_admin)

        return self.create_success_result(
            message=help_text,
            data={
                "action": "help",
                "command": args[0] if args else None,
                "is_admin": is_admin
            }
        )


class MoveCommand(BaseCommand):
    """이동 명령어 (방향별)"""

    def __init__(self, direction: str, aliases: List[str] = None):
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


class GoCommand(BaseCommand):
    """go 명령어 (방향 지정)"""

    def __init__(self):
        super().__init__(
            name="go",
            aliases=["move", "walk"],
            description="지정한 방향으로 이동합니다",
            usage="go <방향>"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        from ..core.localization import get_localization_manager
        localization = get_localization_manager()
        locale = session.player.preferred_locale if session.player else "en"

        if not self.validate_args(args, min_args=1):
            return self.create_error_result(localization.get_message("go.usage_error", locale))

        direction = args[0].lower()
        valid_directions = {
            'north', 'south', 'east', 'west',
            'n', 's', 'e', 'w'
        }

        # 축약형을 전체 이름으로 변환
        direction_map = {
            'n': 'north', 's': 'south', 'e': 'east', 'w': 'west'
        }

        if direction in direction_map:
            direction = direction_map[direction]

        if direction not in valid_directions:
            return self.create_error_result(localization.get_message("go.invalid_direction", locale, direction=args[0]))

        # MoveCommand를 임시로 생성하여 실행
        move_command = MoveCommand(direction)
        return await move_command.execute(session, [])


class ExitsCommand(BaseCommand):
    """출구 확인 명령어"""

    def __init__(self):
        super().__init__(
            name="exits",
            aliases=["ex", "directions"],
            description="현재 방의 출구를 확인합니다",
            usage="exits"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        from ..core.localization import get_localization_manager
        localization = get_localization_manager()
        locale = session.player.preferred_locale if session.player else "en"

        if not session.is_authenticated or not session.player:
            return self.create_error_result(localization.get_message("auth.not_authenticated", locale))

        # 현재 방 ID 가져오기
        current_room_id = getattr(session, 'current_room_id', None)
        if not current_room_id:
            return self.create_error_result(localization.get_message("movement.no_location", locale))

        # GameEngine을 통해 방 정보 조회
        from ..core.game_engine import GameEngine
        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

        try:
            current_room = await game_engine.world_manager.get_room(current_room_id)
            if not current_room:
                return self.create_error_result("현재 방을 찾을 수 없습니다.")

            logger.info("좌표 기반으로 사용 가능한 출구 계산")
            # 좌표 기반으로 사용 가능한 출구 계산
            exits = []
            if current_room.x is not None and current_room.y is not None:
                from ...utils.coordinate_utils import Direction, calculate_new_coordinates

                # 각 방향에 대해 방이 존재하는지 확인
                for direction in Direction:
                    new_x, new_y = calculate_new_coordinates(current_room.x, current_room.y, direction)
                    adjacent_room = await game_engine.world_manager.get_room_at_coordinates(new_x, new_y)
                    if adjacent_room:
                        exits.append(direction.value)

            if not exits:
                return self.create_info_result(localization.get_message("exits.no_exits", locale))

            # 출구 목록 생성
            exit_list = ", ".join(exits)
            message = localization.get_message("exits.available", locale, exits=exit_list)

            return self.create_success_result(
                message=message,
                data={
                    "action": "exits",
                    "exits": exits,
                    "room_id": current_room_id
                }
            )

        except Exception as e:
            logger.error(f"출구 확인 명령어 실행 중 오류: {e}")
            return self.create_error_result(localization.get_message("exits.error", locale))


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