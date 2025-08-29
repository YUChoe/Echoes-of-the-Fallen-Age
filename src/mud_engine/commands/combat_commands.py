# -*- coding: utf-8 -*-
"""전투 관련 명령어들"""

import logging
from typing import List

from .base import BaseCommand, CommandResult, CommandResultType
from ..server.session import Session
from ..game.combat import CombatSystem, CombatAction, CombatResult

logger = logging.getLogger(__name__)


class AttackCommand(BaseCommand):
    """공격 명령어"""

    def __init__(self, combat_system: CombatSystem):
        super().__init__(
            name="attack",
            aliases=["att", "kill", "fight"],
            description="몬스터를 공격합니다",
            usage="attack <몬스터명>"
        )
        self.combat_system = combat_system

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
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
                # 이미 전투 중이면 공격 액션 처리
                turn = self.combat_system.process_player_action(
                    session.player.id,
                    CombatAction.ATTACK
                )

                if turn:
                    combat_status = existing_combat.get_combat_status()
                    return self.create_success_result(
                        message=turn.message,
                        data={
                            "action": "combat_turn",
                            "turn": turn.__dict__,
                            "combat_status": combat_status
                        },
                        broadcast=True,
                        broadcast_message=f"⚔️ {session.player.username}이(가) 전투 중입니다!",
                        room_only=True
                    )
                else:
                    return self.create_error_result("전투 액션 처리에 실패했습니다.")

            # 새로운 전투 시작 - GameEngine을 통해 몬스터 찾기
            game_engine = getattr(session, 'game_engine', None)
            if not game_engine:
                return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

            # 방에서 몬스터 찾기
            monsters = await game_engine.world_manager.get_monsters_in_room(current_room_id)
            target_monster = None

            for monster in monsters:
                if not monster.is_alive:
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

            # 전투 시작
            combat = self.combat_system.start_combat(
                session.player,
                target_monster,
                current_room_id
            )

            # 첫 번째 공격 턴 처리
            turn = combat.process_player_action(CombatAction.ATTACK)
            combat_status = combat.get_combat_status()

            # 전투 시작 메시지
            start_message = f"⚔️ {session.player.username}이(가) {target_monster.get_localized_name('ko')}와(과) 전투를 시작했습니다!"

            return self.create_success_result(
                message=f"⚔️ {target_monster.get_localized_name('ko')}와(과) 전투를 시작합니다!\n{turn.message}",
                data={
                    "action": "combat_start",
                    "monster": {
                        "id": target_monster.id,
                        "name": target_monster.get_localized_name('ko')
                    },
                    "turn": turn.__dict__,
                    "combat_status": combat_status
                },
                broadcast=True,
                broadcast_message=start_message,
                room_only=True
            )

        except Exception as e:
            logger.error(f"공격 명령어 실행 중 오류: {e}")
            return self.create_error_result("공격 중 오류가 발생했습니다.")


class DefendCommand(BaseCommand):
    """방어 명령어"""

    def __init__(self, combat_system: CombatSystem):
        super().__init__(
            name="defend",
            aliases=["def", "guard", "block"],
            description="방어 자세를 취합니다 (다음 턴 데미지 50% 감소)",
            usage="defend"
        )
        self.combat_system = combat_system

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        try:
            # 전투 중인지 확인
            combat = self.combat_system.get_player_combat(session.player.id)
            if not combat:
                return self.create_error_result("전투 중이 아닙니다.")

            # 방어 액션 처리
            turn = self.combat_system.process_player_action(
                session.player.id,
                CombatAction.DEFEND
            )

            if turn:
                combat_status = combat.get_combat_status()
                return self.create_success_result(
                    message=turn.message,
                    data={
                        "action": "combat_defend",
                        "turn": turn.__dict__,
                        "combat_status": combat_status
                    },
                    broadcast=True,
                    broadcast_message=f"🛡️ {session.player.username}이(가) 방어 자세를 취했습니다.",
                    room_only=True
                )
            else:
                return self.create_error_result("방어 액션 처리에 실패했습니다.")

        except Exception as e:
            logger.error(f"방어 명령어 실행 중 오류: {e}")
            return self.create_error_result("방어 중 오류가 발생했습니다.")


class FleeCommand(BaseCommand):
    """도망 명령어"""

    def __init__(self, combat_system: CombatSystem):
        super().__init__(
            name="flee",
            aliases=["run", "escape", "retreat"],
            description="전투에서 도망칩니다",
            usage="flee"
        )
        self.combat_system = combat_system

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        try:
            # 전투 중인지 확인
            combat = self.combat_system.get_player_combat(session.player.id)
            if not combat:
                return self.create_error_result("전투 중이 아닙니다.")

            # 도망 액션 처리
            turn = self.combat_system.process_player_action(
                session.player.id,
                CombatAction.FLEE
            )

            if turn:
                combat_status = combat.get_combat_status()

                # 도망 성공 여부 확인
                if combat.result == CombatResult.PLAYER_FLED:
                    # 전투 종료
                    self.combat_system.end_combat(combat.room_id)

                    return self.create_success_result(
                        message="💨 성공적으로 도망쳤습니다!",
                        data={
                            "action": "combat_fled",
                            "turn": turn.__dict__,
                            "combat_ended": True
                        },
                        broadcast=True,
                        broadcast_message=f"💨 {session.player.username}이(가) 전투에서 도망쳤습니다!",
                        room_only=True
                    )
                else:
                    return self.create_success_result(
                        message=f"{turn.message}\n도망에 실패했습니다!",
                        data={
                            "action": "combat_flee_failed",
                            "turn": turn.__dict__,
                            "combat_status": combat_status
                        },
                        broadcast=True,
                        broadcast_message=f"💨 {session.player.username}이(가) 도망치려 했지만 실패했습니다!",
                        room_only=True
                    )
            else:
                return self.create_error_result("도망 액션 처리에 실패했습니다.")

        except Exception as e:
            logger.error(f"도망 명령어 실행 중 오류: {e}")
            return self.create_error_result("도망 중 오류가 발생했습니다.")


class CombatStatusCommand(BaseCommand):
    """전투 상태 확인 명령어"""

    def __init__(self, combat_system: CombatSystem):
        super().__init__(
            name="combat",
            aliases=["battle", "fight_status", "cs"],
            description="현재 전투 상태를 확인합니다",
            usage="combat"
        )
        self.combat_system = combat_system

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        try:
            # 전투 중인지 확인
            combat = self.combat_system.get_player_combat(session.player.id)
            if not combat:
                return self.create_info_result("현재 전투 중이 아닙니다.")

            combat_status = combat.get_combat_status()

            # 전투 상태 메시지 생성
            player_info = combat_status['player']
            monster_info = combat_status['monster']

            message = f"""
⚔️ 전투 상태 (턴 {combat_status['turn_number']})

👤 {player_info['name']}:
   HP: {player_info['hp']}/{player_info['max_hp']} ({player_info['hp_percentage']:.1f}%)

👹 {monster_info['name']}:
   HP: {monster_info['hp']}/{monster_info['max_hp']} ({monster_info['hp_percentage']:.1f}%)

📝 마지막 행동: {combat_status['last_turn']}

💡 사용 가능한 명령어: attack, defend, flee
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