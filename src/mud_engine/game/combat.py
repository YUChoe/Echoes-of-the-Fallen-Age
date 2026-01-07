"""
전투 시스템 - 인스턴스 기반 턴제 전투
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from .monster import Monster
from .models import Player

logger = logging.getLogger(__name__)


class CombatAction(Enum):
    """전투 행동 타입"""

    ATTACK = "attack"
    DEFEND = "defend"
    SKILL = "skill"
    FLEE = "flee"
    WAIT = "wait"


class CombatantType(Enum):
    """전투 참가자 타입"""

    PLAYER = "player"
    MONSTER = "monster"


@dataclass
class Combatant:
    """전투 참가자"""

    id: str
    name: str
    combatant_type: CombatantType
    agility: int  # 민첩 (턴 순서 결정)
    max_hp: int
    current_hp: int
    attack_power: int
    defense: int
    is_defending: bool = False  # 방어 중인지 여부
    data: Optional[Dict[str, Any]] = None  # 추가 데이터 (AC, 공격보너스 등)

    def __post_init__(self):
        """초기화 후 검증"""
        if self.agility < 0:
            raise ValueError("민첩은 0 이상이어야 합니다")
        if self.max_hp <= 0:
            raise ValueError("최대 HP는 1 이상이어야 합니다")
        if self.current_hp < 0:
            self.current_hp = 0

    def is_alive(self) -> bool:
        """생존 여부 확인"""
        return self.current_hp > 0

    def take_damage(self, damage: int) -> int:
        """데미지를 받고 실제 받은 데미지 반환"""
        # 방어 중이면 데미지 50% 감소
        if self.is_defending:
            damage = damage // 2

        actual_damage = max(0, damage - self.defense)
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

    def get_display_name(self, locale: str = "en", world_manager=None) -> str:
        """표시용 이름 반환 (언어별)"""
        if self.combatant_type == CombatantType.PLAYER:
            return self.name  # 플레이어는 이름 그대로
        elif self.combatant_type == CombatantType.MONSTER:
            # 몬스터는 world_manager를 통해 동적으로 이름 조회
            if world_manager:
                try:
                    # 비동기 함수를 동기적으로 호출할 수 없으므로 data에서 조회
                    if self.data and "monster" in self.data:
                        monster = self.data["monster"]
                        return monster.get_localized_name(locale)
                except Exception:
                    pass
            # 폴백: ID 또는 기본 이름 사용
            return self.name
        else:
            return self.name

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "name": self.name,
            "combatant_type": self.combatant_type.value,
            "agility": self.agility,
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "attack_power": self.attack_power,
            "defense": self.defense,
            "is_defending": self.is_defending,
            "hp_percentage": self.get_hp_percentage(),
        }


@dataclass
class CombatTurn:
    """전투 턴 정보"""

    turn_number: int
    combatant_id: str
    action: Optional[CombatAction] = None
    target_id: Optional[str] = None
    damage_dealt: int = 0
    damage_received: int = 0
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "turn_number": self.turn_number,
            "combatant_id": self.combatant_id,
            "action": self.action.value if self.action else None,
            "target_id": self.target_id,
            "damage_dealt": self.damage_dealt,
            "damage_received": self.damage_received,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class CombatInstance:
    """전투 인스턴스"""

    id: str = field(default_factory=lambda: str(uuid4()))
    room_id: str = ""
    combatants: List[Combatant] = field(default_factory=list)
    turn_order: List[str] = field(default_factory=list)  # combatant_id 순서
    current_turn_index: int = 0
    turn_number: int = 1
    combat_log: List[CombatTurn] = field(default_factory=list)
    is_active: bool = True
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None

    def __post_init__(self):
        """초기화 후 턴 순서 결정"""
        if not self.turn_order and self.combatants:
            self._determine_turn_order()

    def _determine_turn_order(self) -> None:
        """민첩 기반 턴 순서 결정 (높은 순서대로)"""
        # 민첩이 높은 순서대로 정렬
        sorted_combatants = sorted(
            self.combatants, key=lambda c: c.agility, reverse=True
        )
        self.turn_order = [c.id for c in sorted_combatants]
        logger.info(f"전투 {self.id} 턴 순서 결정: {self.turn_order}")

    def add_combatant(self, combatant: Combatant) -> None:
        """전투 참가자 추가"""
        if any(c.id == combatant.id for c in self.combatants):
            logger.warning(f"이미 전투에 참가 중인 참가자: {combatant.id}")
            return

        self.combatants.append(combatant)
        # 턴 순서 재결정
        self._determine_turn_order()
        logger.info(f"전투 {self.id}에 {combatant.name} 추가")
        for c in self.combatants:
            logger.info(f"- {c.get_display_name()}")

    def remove_combatant(self, combatant_id: str) -> bool:
        """전투 참가자 제거"""
        original_count = len(self.combatants)
        self.combatants = [c for c in self.combatants if c.id != combatant_id]

        if len(self.combatants) < original_count:
            # 턴 순서에서도 제거
            if combatant_id in self.turn_order:
                self.turn_order.remove(combatant_id)
            logger.info(f"전투 {self.id}에서 {combatant_id} 제거")
            return True

        return False

    def get_combatant(self, combatant_id: str) -> Optional[Combatant]:
        """참가자 조회"""
        for combatant in self.combatants:
            if combatant.id == combatant_id:
                return combatant
        return None

    def get_current_combatant(self) -> Optional[Combatant]:
        """현재 턴의 참가자 반환"""
        if not self.turn_order or self.current_turn_index >= len(self.turn_order):
            return None

        current_id = self.turn_order[self.current_turn_index]
        return self.get_combatant(current_id)

    def get_alive_combatants(self) -> List[Combatant]:
        """생존한 참가자 목록 반환"""
        return [c for c in self.combatants if c.is_alive()]

    def get_alive_players(self) -> List[Combatant]:
        """생존한 플레이어 목록 반환"""
        return [
            c
            for c in self.combatants
            if c.is_alive() and c.combatant_type == CombatantType.PLAYER
        ]

    def get_alive_monsters(self) -> List[Combatant]:
        """생존한 몬스터 목록 반환"""
        return [
            c
            for c in self.combatants
            if c.is_alive() and c.combatant_type == CombatantType.MONSTER
        ]

    def advance_turn(self) -> None:
        """다음 턴으로 진행"""
        if not self.turn_order:
            return

        # 다음 참가자로 이동
        self.current_turn_index += 1

        # 한 라운드가 끝나면 다시 처음부터
        if self.current_turn_index >= len(self.turn_order):
            self.current_turn_index = 0
            self.turn_number += 1
            logger.info(f"전투 {self.id} 라운드 {self.turn_number} 시작")

        # 사망한 참가자는 건너뛰기
        current = self.get_current_combatant()
        if current and not current.is_alive():
            self.advance_turn()

    def add_combat_log(self, turn: CombatTurn) -> None:
        """전투 로그 추가"""
        self.combat_log.append(turn)

    def is_combat_over(self) -> bool:
        """전투 종료 여부 확인"""
        alive_players = self.get_alive_players()
        alive_monsters = self.get_alive_monsters()

        # 한쪽이 전멸하면 전투 종료
        return len(alive_players) == 0 or len(alive_monsters) == 0

    def end_combat(self) -> None:
        """전투 종료"""
        self.is_active = False
        self.ended_at = datetime.now()
        logger.info(f"전투 {self.id} 종료")

    def get_winners(self) -> List[Combatant]:
        """승리자 목록 반환"""
        if not self.is_combat_over():
            return []

        alive_players = self.get_alive_players()
        alive_monsters = self.get_alive_monsters()

        if alive_players:
            return alive_players
        elif alive_monsters:
            return alive_monsters
        else:
            return []

    @property
    def monsters(self) -> List[Combatant]:
        """몬스터 목록 반환 (호환성을 위한 속성)"""
        return self.get_alive_monsters()

    def set_player_action(self, action: CombatAction) -> bool:
        """
        플레이어 액션 설정 (간단한 버전)

        Args:
            action: 전투 행동

        Returns:
            bool: 성공 여부
        """
        current = self.get_current_combatant()
        if not current or current.combatant_type != CombatantType.PLAYER:
            return False

        # 액션은 실제로 처리되지 않고 단순히 성공 반환
        # 실제 처리는 CombatHandler에서 수행
        return True

    def get_combat_status(self) -> Dict[str, Any]:
        """전투 상태 조회 (호환성을 위한 메서드)"""
        current = self.get_current_combatant()
        alive_players = self.get_alive_players()
        alive_monsters = self.get_alive_monsters()

        # 플레이어 정보
        player_info = None
        if alive_players:
            player = alive_players[0]
            player_info = {
                "id": player.id,
                "name": player.name,
                "hp": player.current_hp,
                "max_hp": player.max_hp,
                "hp_percentage": player.get_hp_percentage(),
                "initiative": player.agility,
            }

        # 몬스터 정보
        monster_info = []
        for monster in alive_monsters:
            monster_info.append(
                {
                    "id": monster.id,
                    "name": monster.name,
                    "hp": monster.current_hp,
                    "max_hp": monster.max_hp,
                    "hp_percentage": monster.get_hp_percentage(),
                    "initiative": monster.agility,
                    "is_alive": monster.is_alive(),
                }
            )

        return {
            "combat_id": self.id,
            "turn_number": self.turn_number,
            "current_turn": current.name if current else "알 수 없음",
            "state": "active" if self.is_active else "ended",
            "player": player_info,
            "monsters": monster_info,
            "monster": monster_info[0] if monster_info else None,  # 호환성
            "last_turn": (
                self.combat_log[-1].message if self.combat_log else "전투 시작"
            ),
            "current_target_index": 0,
        }

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "room_id": self.room_id,
            "combatants": [c.to_dict() for c in self.combatants],
            "turn_order": self.turn_order,
            "current_turn_index": self.current_turn_index,
            "turn_number": self.turn_number,
            "current_combatant": (
                self.get_current_combatant().to_dict()
                if self.get_current_combatant()
                else None
            ),
            "is_active": self.is_active,
            "is_over": self.is_combat_over(),
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
        }


class CombatManager:
    """전투 매니저 - 전투 인스턴스 관리"""

    def __init__(self):
        """전투 매니저 초기화"""
        self.combat_instances: Dict[str, CombatInstance] = (
            {}
        )  # combat_id -> CombatInstance
        self.room_combats: Dict[str, str] = {}  # room_id -> combat_id
        self.player_combats: Dict[str, str] = {}  # player_id -> combat_id
        logger.info("CombatManager 초기화 완료")

    def create_combat(self, room_id: str) -> CombatInstance:
        """새로운 전투 인스턴스 생성"""
        combat = CombatInstance(room_id=room_id)
        self.combat_instances[combat.id] = combat
        self.room_combats[room_id] = combat.id
        logger.info(f"방 {room_id}에 전투 인스턴스 {combat.id} 생성")
        return combat

    def get_combat_instances(self) -> Dict[str, CombatInstance]:
        return self.combat_instances

    def get_combat(self, combat_id: str) -> Optional[CombatInstance]:
        """전투 인스턴스 조회"""
        return self.combat_instances.get(combat_id)

    def get_combat_by_room(self, room_id: str) -> Optional[CombatInstance]:
        """방 ID로 전투 인스턴스 조회"""
        combat_id = self.room_combats.get(room_id)
        if combat_id:
            return self.get_combat(combat_id)
        return None

    def get_combat_by_player(self, player_id: str) -> Optional[CombatInstance]:
        """플레이어 ID로 전투 인스턴스 조회"""
        combat_id = self.player_combats.get(player_id)
        if combat_id:
            return self.get_combat(combat_id)
        return None

    def is_player_in_combat(self, player_id: str) -> bool:
        """플레이어가 전투 중인지 확인"""
        combat = self.get_combat_by_player(player_id)
        return combat is not None and combat.is_active

    def is_room_in_combat(self, room_id: str) -> bool:
        """방에 전투가 진행 중인지 확인"""
        combat = self.get_combat_by_room(room_id)
        return combat is not None and combat.is_active

    def add_player_to_combat(
        self, combat_id: str, player: Player, player_id: str
    ) -> bool:
        """플레이어를 전투에 추가"""
        combat = self.get_combat(combat_id)
        if not combat or not combat.is_active:
            logger.warning(f"전투 {combat_id}를 찾을 수 없거나 비활성 상태")
            return False

        # 이미 다른 전투에 참가 중인지 확인
        if self.is_player_in_combat(player_id):
            logger.warning(f"플레이어 {player_id}는 이미 전투 중")
            return False

        # Combatant 생성
        from .stats import StatType

        combatant = Combatant(
            id=player_id,
            name=player.get_display_name(),
            combatant_type=CombatantType.PLAYER,
            agility=player.stats.get_primary_stat(StatType.DEX),
            max_hp=player.stats.get_secondary_stat(StatType.HP),
            # current_hp=player.stats.get_secondary_stat(StatType.HP),
            current_hp=player.stats.get_current_hp(),
            attack_power=player.stats.get_secondary_stat(StatType.ATK),
            defense=player.stats.get_secondary_stat(StatType.DEF),
        )
        logger.info(f"플레이어 {player_id}를 전투 {combat_id}에 추가")
        combatant.data = {"player": player}
        combat.add_combatant(combatant)
        self.player_combats[player_id] = combat_id
        return True

    def add_monster_to_combat(self, combat_id: str, monster: Monster) -> bool:
        """몬스터를 전투에 추가"""
        logger.info("invoked")
        combat = self.get_combat(combat_id)
        if not combat or not combat.is_active:
            logger.warning(f"전투 {combat_id}를 찾을 수 없거나 비활성 상태")
            return False
        logger.info(combat)

        # Combatant 생성 (D&D 능력치 사용)
        # 몬스터 이름은 원본 Monster 객체를 참조하여 동적으로 처리
        combatant = Combatant(
            id=monster.id,
            name=monster.id,  # ID로 저장하고 표시 시 동적으로 언어별 이름 조회
            combatant_type=CombatantType.MONSTER,
            agility=monster.stats.dexterity,  # 민첩 사용
            max_hp=monster.stats.max_hp,
            current_hp=monster.stats.current_hp,  # 얘도 전투가 종료 되도 이 전에 hp 를 보존 하고 있어야 함
            attack_power=monster.stats.attack_power,
            defense=monster.stats.defense,
        )
        logger.info(combatant)
        # Monster 객체의 추가 정보를 data에 저장 (전투 계산에 사용)
        combatant.data = {
            "monster": monster,  # Monster 객체 전체 저장 (다국어 이름 조회용)
            "armor_class": monster.stats.armor_class,
            "attack_bonus": monster.stats.attack_bonus,
            "initiative_bonus": monster.stats.initiative_bonus,  # 불필요
            "gold_reward": monster.gold_reward,  # 불필요
            "level": monster.stats.level,
        }
        logger.info(
            f"몬스터 {monster.id}를 전투 {combat_id}에 추가 (AC: {monster.stats.armor_class}, 공격보너스: {monster.stats.attack_bonus})"
        )
        combat.add_combatant(combatant)
        return True

    def remove_player_from_combat(self, player_id: str) -> bool:
        """플레이어를 전투에서 제거"""
        combat = self.get_combat_by_player(player_id)
        if not combat:
            return False

        success = combat.remove_combatant(player_id)
        if success:
            del self.player_combats[player_id]
            logger.info(f"플레이어 {player_id}를 전투에서 제거")

        return success

    def end_combat(self, combat_id: str) -> bool:
        """전투 종료"""
        combat = self.get_combat(combat_id)
        if not combat:
            return False

        combat.end_combat()

        # 플레이어 전투 매핑 제거
        for player_id in list(self.player_combats.keys()):
            if self.player_combats[player_id] == combat_id:
                del self.player_combats[player_id]

        # 방 전투 매핑 제거
        if combat.room_id in self.room_combats:
            del self.room_combats[combat.room_id]

        logger.info(f"전투 {combat_id} 종료 및 정리 완료")
        return True

    def cleanup_finished_combats(self) -> int:
        """종료된 전투 인스턴스 정리"""
        finished_combats = [
            combat_id
            for combat_id, combat in self.combat_instances.items()
            if not combat.is_active
        ]

        for combat_id in finished_combats:
            del self.combat_instances[combat_id]

        if finished_combats:
            logger.info(f"{len(finished_combats)}개의 종료된 전투 인스턴스 정리")

        return len(finished_combats)

    def get_active_combats_count(self) -> int:
        """활성 전투 수 반환"""
        return sum(1 for combat in self.combat_instances.values() if combat.is_active)
