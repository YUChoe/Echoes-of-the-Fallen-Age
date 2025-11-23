# -*- coding: utf-8 -*-
"""전투 관련 명령어들"""

import logging
from datetime import datetime
from typing import List

from .base import BaseCommand, CommandResult, CommandResultType
from ..core.types import SessionType
from ..game.combat import CombatAction
from ..game.combat_handler import CombatHandler

logger = logging.getLogger(__name__)


class AttackCommand(BaseCommand):
    """공격 명령어"""

    def __init__(self, combat_handler: CombatHandler):
        super().__init__(
            name="attack",
            aliases=["att", "kill", "fight"],
            description="몬스터를 공격합니다",
            usage="attack <몬스터명>"
        )
        self.combat_handler = combat_handler
        self.combat_system = combat_handler  # 호환성을 위한 별칭

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        if not self.validate_args(args, min_args=1):
            return self.create_error_result(
                "공격할 대상을 지정해주세요.\n사용법: attack <몬스터명>"
            )

        target_name = " ".join(args).lower()
        current_room_id = getattr(session, 'current_room_id', None)

        if not current_room_id:
            return self.create_error_result("현재 위치를 확인할 수 없습니다.")

        try:
            # 이미 전투 중인지 확인
            existing_combat = self.combat_system.get_player_combat(session.player.id)
            if existing_combat:
                # 현재 전투 중인 몬스터들 중에 타겟이 있는지 확인
                target_in_current_combat = False
                for combatant in existing_combat.monsters:
                    # Combatant의 name 속성 사용
                    combatant_name = combatant.name.lower()
                    if target_name in combatant_name:
                        target_in_current_combat = True
                        break

                if target_in_current_combat:
                    # 현재 전투 중인 몬스터를 공격하려는 경우 액션 설정
                    success = existing_combat.set_player_action(CombatAction.ATTACK)
                    if success:
                        return self.create_success_result(
                            message="⚔️ 공격 액션을 선택했습니다!",
                            data={
                                "action": "combat_action_set",
                                "selected_action": "attack",
                                "combat_status": existing_combat.get_combat_status()
                            }
                        )
                    else:
                        return self.create_error_result("현재 액션을 선택할 수 없습니다.")
                else:
                    # 새로운 몬스터를 공격하려는 경우 - 기존 전투에 추가
                    pass  # 아래에서 처리

            # GameEngine을 통해 몬스터 찾기
            game_engine = getattr(session, 'game_engine', None)
            if not game_engine:
                return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

            # 방에서 몬스터 찾기
            monsters = await game_engine.world_manager.get_monsters_in_room(current_room_id)
            target_monster = None

            for monster in monsters:
                if not monster.is_alive:
                    continue

                # 이미 다른 플레이어와 전투 중인 몬스터는 제외 (현재 플레이어 제외)
                if self._is_monster_in_combat_with_other_player(monster.id, session.player.id):
                    continue

                monster_name_ko = monster.get_localized_name('ko').lower()
                monster_name_en = monster.get_localized_name('en').lower()

                if target_name in monster_name_ko or target_name in monster_name_en:
                    target_monster = monster
                    break

            if not target_monster:
                return self.create_error_result(
                    f"'{' '.join(args)}'라는 몬스터를 찾을 수 없습니다."
                )

            # 브로드캐스트 콜백 함수 정의 (개선된 버전)
            async def broadcast_callback(room_id: str, message: str, message_type: str = "combat_message", combat_status: dict = None):
                broadcast_data = {
                    "type": message_type,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                }

                if combat_status:
                    broadcast_data["combat_status"] = combat_status

                # 전투 메시지는 모든 플레이어에게 전송 (전투 시작한 플레이어 포함)
                await game_engine.broadcast_to_room(
                    room_id,
                    broadcast_data
                )

            # 기존 전투가 있으면 몬스터 추가, 없으면 새 전투 시작
            monster_name_ko = target_monster.get_localized_name('ko')
            
            if existing_combat:
                # 기존 전투에 몬스터 추가
                success = await self.combat_system.add_monsters_to_combat(
                    session.player.id,
                    [target_monster]
                )

                if success:
                    return self.create_success_result(
                        message=f"⚔️ {monster_name_ko}이(가) 전투에 참여했습니다!",
                        data={
                            "action": "monster_added_to_combat",
                            "monster": {
                                "id": target_monster.id,
                                "name": monster_name_ko
                            },
                            "combat_status": existing_combat.get_combat_status()
                        }
                    )
                else:
                    return self.create_error_result("몬스터를 전투에 추가할 수 없습니다.")
            else:
                # 새로운 전투 시작
                combat = await self.combat_system.start_combat(
                    session.player,
                    target_monster,
                    current_room_id,
                    broadcast_callback
                )

                # 전투 시작 메시지
                start_message = f"⚔️ {session.player.username}이(가) {monster_name_ko}와(과) 전투를 시작했습니다!"

                return self.create_success_result(
                    message=f"⚔️ {monster_name_ko}와(과) 전투를 시작합니다!",
                    data={
                        "action": "combat_start",
                        "monster": {
                            "id": target_monster.id,
                            "name": monster_name_ko
                        },
                        "combat_status": combat.get_combat_status()
                    },
                    broadcast=True,
                    broadcast_message=start_message,
                    room_only=True
                )

        except Exception as e:
            logger.error(f"공격 명령어 실행 중 오류: {e}")
            return self.create_error_result("공격 중 오류가 발생했습니다.")

    def _is_monster_in_combat_with_other_player(self, monster_id: str, current_player_id: str) -> bool:
        """몬스터가 다른 플레이어와 전투 중인지 확인합니다."""
        try:
            for combat_id, combat in self.combat_system.active_combats.items():
                # 현재 플레이어가 참여 중인 전투는 제외
                player_in_this_combat = any(
                    c.id == current_player_id
                    for c in combat.combatants
                )
                if player_in_this_combat:
                    continue

                # 해당 전투에서 몬스터 ID 확인
                for monster in combat.monsters:
                    if monster.id == monster_id:
                        return True
            return False
        except Exception as e:
            logger.error(f"몬스터 전투 상태 확인 실패: {e}")
            return False


class DefendCommand(BaseCommand):
    """방어 명령어"""

    def __init__(self, combat_handler: CombatHandler):
        super().__init__(
            name="defend",
            aliases=["def", "guard", "block"],
            description="방어 자세를 취합니다 (다음 턴 데미지 50% 감소)",
            usage="defend"
        )
        self.combat_handler = combat_handler
        self.combat_system = combat_handler  # 호환성을 위한 별칭

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        try:
            # 전투 중인지 확인
            combat = self.combat_system.get_player_combat(session.player.id)
            if not combat:
                return self.create_error_result("전투 중이 아닙니다.")

            # 방어 액션 설정
            success = combat.set_player_action(CombatAction.DEFEND)
            if success:
                return self.create_success_result(
                    message="🛡️ 방어 액션을 선택했습니다!",
                    data={
                        "action": "combat_action_set",
                        "selected_action": "defend",
                        "combat_status": combat.get_combat_status()
                    }
                )
            else:
                return self.create_error_result("현재 액션을 선택할 수 없습니다.")

        except Exception as e:
            logger.error(f"방어 명령어 실행 중 오류: {e}")
            return self.create_error_result("방어 중 오류가 발생했습니다.")


class FleeCommand(BaseCommand):
    """도망 명령어"""

    def __init__(self, combat_handler: CombatHandler):
        super().__init__(
            name="flee",
            aliases=["run", "escape", "retreat"],
            description="전투에서 도망칩니다",
            usage="flee"
        )
        self.combat_handler = combat_handler
        self.combat_system = combat_handler  # 호환성을 위한 별칭

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        try:
            # 전투 중인지 확인
            combat = self.combat_system.get_player_combat(session.player.id)
            if not combat:
                return self.create_error_result("전투 중이 아닙니다.")

            # 도망 액션 설정
            success = combat.set_player_action(CombatAction.FLEE)
            if success:
                return self.create_success_result(
                    message="💨 도망 액션을 선택했습니다!",
                    data={
                        "action": "combat_action_set",
                        "selected_action": "flee",
                        "combat_status": combat.get_combat_status()
                    }
                )
            else:
                return self.create_error_result("현재 액션을 선택할 수 없습니다.")

        except Exception as e:
            logger.error(f"도망 명령어 실행 중 오류: {e}")
            return self.create_error_result("도망 중 오류가 발생했습니다.")


class CombatStatusCommand(BaseCommand):
    """전투 상태 확인 명령어"""

    def __init__(self, combat_handler: CombatHandler):
        super().__init__(
            name="combat",
            aliases=["battle", "fight_status", "cs"],
            description="현재 전투 상태를 확인합니다",
            usage="combat"
        )
        self.combat_handler = combat_handler
        self.combat_system = combat_handler  # 호환성을 위한 별칭

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        try:
            # 전투 중인지 확인
            combat = self.combat_system.get_player_combat(session.player.id)
            if not combat:
                return self.create_info_result("현재 전투 중이 아닙니다.")

            combat_status = combat.get_combat_status()

            # 전투 상태 메시지 생성 (다중 전투 지원)
            player_info = combat_status['player']
            monsters_info = combat_status.get('monsters', [combat_status.get('monster')])

            current_turn = combat_status.get('current_turn', '알 수 없음')
            state = combat_status.get('state', 'unknown')
            current_target_index = combat_status.get('current_target_index', 0)

            # 몬스터 정보 문자열 생성
            monsters_text = ""
            for i, monster_info in enumerate(monsters_info):
                if not monster_info:
                    continue

                status_icon = "💀" if monster_info.get('is_alive', True) == False else "👹"
                target_marker = " 🎯" if i == current_target_index else ""

                monsters_text += f"{status_icon} {monster_info['name']} (Initiative: {monster_info.get('initiative', 0)}){target_marker}:\n"
                monsters_text += f"   HP: {monster_info['hp']}/{monster_info['max_hp']} ({monster_info['hp_percentage']:.1f}%)\n\n"

            message = f"""
⚔️ 다중 전투 상태 (턴 {combat_status['turn_number']})
🎯 현재 턴: {current_turn}
⏱️ 상태: {state}

👤 {player_info['name']} (Initiative: {player_info.get('initiative', 0)}):
   HP: {player_info['hp']}/{player_info['max_hp']} ({player_info['hp_percentage']:.1f}%)

{monsters_text}📝 마지막 행동: {combat_status['last_turn']}

💡 다중 전투 진행 중 - 턴이 돌아오면 액션을 선택하세요!
   🎯 표시된 몬스터가 현재 공격 대상입니다.
   사용 가능한 명령어: attack [몬스터명], defend, flee
            """.strip()

            return self.create_success_result(
                message=message,
                data={
                    "action": "combat_status",
                    "combat_status": combat_status
                }
            )

        except Exception as e:
            logger.error(f"전투 상태 확인 명령어 실행 중 오류: {e}")
            return self.create_error_result("전투 상태 확인 중 오류가 발생했습니다.")