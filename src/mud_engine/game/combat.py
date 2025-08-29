"""
전투 시스템 구현
"""

import random
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from datetime import datetime

from .models import Player
from .monster import Monster, MonsterStats
from .stats import PlayerStats, StatType, StatCalculator


class CombatAction(Enum):
    """전투 액션 타입"""
    ATTACK = "attack"
    DEFEND = "defend"
    FLEE = "flee"
    USE_ITEM = "use_item"
    CAST_SPELL = "cast_spell"


class CombatResult(Enum):
    """전투 결과"""
    ONGOING = "ongoing"
    PLAYER_VICTORY = "player_victory"
    MONSTER_VICTORY = "monster_victory"
    PLAYER_FLED = "player_fled"
    DRAW = "draw"


@dataclass
class CombatTurn:
    """전투 턴 정보"""
    turn_number: int
    attacker_id: str
    attacker_type: str  # "player" or "monster"
    action: CombatAction
    target_id: str
    damage_dealt: int = 0
    is_critical: bool = False
    is_hit: bool = True
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CombatParticipant:
    """전투 참여자 정보"""
    id: str
    name: str
    participant_type: str  # "player" or "monster"
    max_hp: int
    current_hp: int
    attack_power: int
    defense: int
    speed: int
    accuracy: int = 80
    critical_chance: int = 5
    is_defending: bool = False

    def is_alive(self) -> bool:
        """생존 여부 확인"""
        return self.current_hp > 0

    def take_damage(self, damage: int) -> int:
        """데미지를 받고 실제 받은 데미지 반환"""
        if self.is_defending:
            damage = int(damage * 0.5)  # 방어 시 데미지 50% 감소
            self.is_defending = False

        actual_damage = max(1, damage - self.defense)
        self.current_hp = max(0, self.current_hp - actual_damage)
        return actual_damage

    def heal(self, amount: int) -> None:
        """체력 회복"""
        self.current_hp = min(self.max_hp, self.current_hp + amount)

    def get_hp_percentage(self) -> float:
        """HP 퍼센트 반환"""
        if self.max_hp <= 0:
            return 0.0
        return (self.current_hp / self.max_hp) * 100


class CombatSystem:
    """전투 시스템 메인 클래스"""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.active_combats: Dict[str, 'Combat'] = {}  # room_id -> Combat

    def start_combat(self, player: Player, monster: Monster, room_id: str) -> 'Combat':
        """전투 시작"""
        self.logger.info(f"전투 시작: {player.username} vs {monster.get_localized_name('ko')} in room {room_id}")

        # 기존 전투가 있다면 종료
        if room_id in self.active_combats:
            self.end_combat(room_id)

        # 새 전투 생성
        combat = Combat(player, monster, room_id)
        self.active_combats[room_id] = combat

        return combat

    def get_combat(self, room_id: str) -> Optional['Combat']:
        """방의 활성 전투 조회"""
        return self.active_combats.get(room_id)

    def end_combat(self, room_id: str) -> None:
        """전투 종료"""
        if room_id in self.active_combats:
            combat = self.active_combats[room_id]
            self.logger.info(f"전투 종료: room {room_id}, 결과: {combat.result}")
            del self.active_combats[room_id]

    def is_in_combat(self, player_id: str) -> bool:
        """플레이어가 전투 중인지 확인"""
        for combat in self.active_combats.values():
            if combat.player_participant.id == player_id:
                return True
        return False

    def get_player_combat(self, player_id: str) -> Optional['Combat']:
        """플레이어의 현재 전투 조회"""
        for combat in self.active_combats.values():
            if combat.player_participant.id == player_id:
                return combat
        return None

    def process_player_action(self, player_id: str, action: CombatAction,
                            target_id: Optional[str] = None) -> Optional[CombatTurn]:
        """플레이어 액션 처리"""
        combat = self.get_player_combat(player_id)
        if not combat:
            return None

        return combat.process_player_action(action, target_id)

    def calculate_damage(self, attacker: CombatParticipant,
                        defender: CombatParticipant) -> Tuple[int, bool, bool]:
        """
        데미지 계산

        Returns:
            Tuple[int, bool, bool]: (데미지, 명중여부, 크리티컬여부)
        """
        # 명중률 계산
        hit_chance = attacker.accuracy / 100.0
        is_hit = random.random() <= hit_chance

        if not is_hit:
            return 0, False, False

        # 크리티컬 확률 계산
        critical_chance = attacker.critical_chance / 100.0
        is_critical = random.random() <= critical_chance

        # 기본 데미지 계산
        base_damage = attacker.attack_power

        # 크리티컬 시 데미지 2배
        if is_critical:
            base_damage *= 2

        # 방어력 적용
        final_damage = max(1, base_damage - defender.defense)

        # 랜덤 변동 (±20%)
        variation = random.uniform(0.8, 1.2)
        final_damage = int(final_damage * variation)

        return final_damage, is_hit, is_critical


class Combat:
    """개별 전투 인스턴스"""

    def __init__(self, player: Player, monster: Monster, room_id: str):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.room_id = room_id
        self.result = CombatResult.ONGOING
        self.turn_number = 0
        self.combat_log: List[CombatTurn] = []
        self.started_at = datetime.now()

        # 전투 참여자 생성
        self.player_participant = self._create_player_participant(player)
        self.monster_participant = self._create_monster_participant(monster)

        # 원본 객체 참조 유지 (경험치, 레벨업 등을 위해)
        self.player = player
        self.monster = monster

        self.logger.info(f"전투 생성: {player.username} vs {monster.get_localized_name('ko')}")

    def _create_player_participant(self, player: Player) -> CombatParticipant:
        """플레이어 전투 참여자 생성"""
        stats = player.stats if player.stats else PlayerStats()

        return CombatParticipant(
            id=player.id,
            name=player.username,
            participant_type="player",
            max_hp=stats.get_secondary_stat(StatType.HP),
            current_hp=stats.get_secondary_stat(StatType.HP),  # 전투 시작 시 풀 HP
            attack_power=stats.get_secondary_stat(StatType.ATK),
            defense=stats.get_secondary_stat(StatType.DEF),
            speed=stats.get_secondary_stat(StatType.SPD),
            accuracy=80 + stats.get_primary_stat(StatType.DEX),  # 기본 80% + 민첩성
            critical_chance=5 + int(stats.get_primary_stat(StatType.DEX) * 0.2)  # 기본 5% + 민첩성 보너스
        )

    def _create_monster_participant(self, monster: Monster) -> CombatParticipant:
        """몬스터 전투 참여자 생성"""
        return CombatParticipant(
            id=monster.id,
            name=monster.get_localized_name('ko'),
            participant_type="monster",
            max_hp=monster.stats.max_hp,
            current_hp=monster.stats.current_hp,
            attack_power=monster.stats.attack_power,
            defense=monster.stats.defense,
            speed=monster.stats.speed,
            accuracy=monster.stats.accuracy,
            critical_chance=monster.stats.critical_chance
        )

    def process_player_action(self, action: CombatAction,
                            target_id: Optional[str] = None) -> CombatTurn:
        """플레이어 액션 처리"""
        if self.result != CombatResult.ONGOING:
            raise ValueError("전투가 이미 종료되었습니다")

        self.turn_number += 1

        # 플레이어 턴 처리
        player_turn = self._process_turn(
            self.player_participant,
            self.monster_participant,
            action
        )
        self.combat_log.append(player_turn)

        # 몬스터가 죽었는지 확인
        if not self.monster_participant.is_alive():
            self.result = CombatResult.PLAYER_VICTORY
            self._handle_victory()
            return player_turn

        # 플레이어가 도망쳤는지 확인
        if action == CombatAction.FLEE:
            flee_success = self._calculate_flee_success()
            if flee_success:
                self.result = CombatResult.PLAYER_FLED
                return player_turn

        # 몬스터 턴 처리 (AI)
        monster_action = self._get_monster_action()
        monster_turn = self._process_turn(
            self.monster_participant,
            self.player_participant,
            monster_action
        )
        self.combat_log.append(monster_turn)

        # 플레이어가 죽었는지 확인
        if not self.player_participant.is_alive():
            self.result = CombatResult.MONSTER_VICTORY
            self._handle_defeat()

        return player_turn

    def _process_turn(self, attacker: CombatParticipant,
                     defender: CombatParticipant,
                     action: CombatAction) -> CombatTurn:
        """턴 처리"""
        turn = CombatTurn(
            turn_number=self.turn_number,
            attacker_id=attacker.id,
            attacker_type=attacker.participant_type,
            action=action,
            target_id=defender.id
        )

        if action == CombatAction.ATTACK:
            damage, is_hit, is_critical = self._calculate_damage(attacker, defender)

            if is_hit:
                actual_damage = defender.take_damage(damage)
                turn.damage_dealt = actual_damage
                turn.is_hit = True
                turn.is_critical = is_critical

                if is_critical:
                    turn.message = f"{attacker.name}이(가) {defender.name}에게 치명타로 {actual_damage} 데미지를 입혔습니다!"
                else:
                    turn.message = f"{attacker.name}이(가) {defender.name}에게 {actual_damage} 데미지를 입혔습니다."
            else:
                turn.is_hit = False
                turn.message = f"{attacker.name}의 공격이 빗나갔습니다!"

        elif action == CombatAction.DEFEND:
            attacker.is_defending = True
            turn.message = f"{attacker.name}이(가) 방어 자세를 취했습니다."

        elif action == CombatAction.FLEE:
            turn.message = f"{attacker.name}이(가) 도망치려 합니다!"

        return turn

    def _calculate_damage(self, attacker: CombatParticipant,
                        defender: CombatParticipant) -> Tuple[int, bool, bool]:
        """데미지 계산"""
        # 명중률 계산
        hit_chance = attacker.accuracy / 100.0
        is_hit = random.random() <= hit_chance

        if not is_hit:
            return 0, False, False

        # 크리티컬 확률 계산
        critical_chance = attacker.critical_chance / 100.0
        is_critical = random.random() <= critical_chance

        # 기본 데미지 계산
        base_damage = attacker.attack_power

        # 크리티컬 시 데미지 2배
        if is_critical:
            base_damage *= 2

        # 방어력 적용
        final_damage = max(1, base_damage - defender.defense)

        # 랜덤 변동 (±20%)
        variation = random.uniform(0.8, 1.2)
        final_damage = int(final_damage * variation)

        return final_damage, is_hit, is_critical

    def _get_monster_action(self) -> CombatAction:
        """몬스터 AI 액션 결정"""
        # 간단한 AI: 90% 확률로 공격, 10% 확률로 방어
        if random.random() < 0.9:
            return CombatAction.ATTACK
        else:
            return CombatAction.DEFEND

    def _calculate_flee_success(self) -> bool:
        """도망 성공률 계산"""
        # 플레이어 속도와 몬스터 속도 비교
        player_speed = self.player_participant.speed
        monster_speed = self.monster_participant.speed

        # 기본 50% + 속도 차이에 따른 보너스/페널티
        base_chance = 0.5
        speed_modifier = (player_speed - monster_speed) * 0.02  # 속도 차이 1당 2%

        flee_chance = base_chance + speed_modifier
        flee_chance = max(0.1, min(0.9, flee_chance))  # 10%~90% 제한

        return random.random() <= flee_chance

    def _handle_victory(self) -> None:
        """승리 처리"""
        # 경험치 획득
        exp_gained = self.monster.experience_reward
        if self.player.stats:
            leveled_up = self.player.stats.add_experience(exp_gained)
            if leveled_up:
                self.logger.info(f"플레이어 {self.player.username} 레벨업! 현재 레벨: {self.player.stats.level}")

        # 몬스터 사망 처리
        self.monster.die()

        self.logger.info(f"전투 승리: {self.player.username}이(가) {self.monster.get_localized_name('ko')}을(를) 처치했습니다")

    def _handle_defeat(self) -> None:
        """패배 처리"""
        # 플레이어 사망 처리 (추후 구현)
        self.logger.info(f"전투 패배: {self.player.username}이(가) {self.monster.get_localized_name('ko')}에게 패배했습니다")

    def get_combat_status(self) -> Dict[str, Any]:
        """전투 상태 정보 반환"""
        return {
            'room_id': self.room_id,
            'result': self.result.value,
            'turn_number': self.turn_number,
            'player': {
                'name': self.player_participant.name,
                'hp': self.player_participant.current_hp,
                'max_hp': self.player_participant.max_hp,
                'hp_percentage': self.player_participant.get_hp_percentage()
            },
            'monster': {
                'name': self.monster_participant.name,
                'hp': self.monster_participant.current_hp,
                'max_hp': self.monster_participant.max_hp,
                'hp_percentage': self.monster_participant.get_hp_percentage()
            },
            'last_turn': self.combat_log[-1].message if self.combat_log else "",
            'is_ongoing': self.result == CombatResult.ONGOING
        }

    def get_combat_log(self) -> List[Dict[str, Any]]:
        """전투 로그 반환"""
        return [
            {
                'turn_number': turn.turn_number,
                'attacker': turn.attacker_id,
                'attacker_type': turn.attacker_type,
                'action': turn.action.value,
                'damage_dealt': turn.damage_dealt,
                'is_critical': turn.is_critical,
                'is_hit': turn.is_hit,
                'message': turn.message,
                'timestamp': turn.timestamp.isoformat()
            }
            for turn in self.combat_log
        ]