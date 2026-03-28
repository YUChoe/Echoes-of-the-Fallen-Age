"""
전투 참가자 모델 - CombatAction, CombatantType, Combatant
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CombatAction(Enum):
    """전투 행동 타입"""

    ATTACK = "attack"
    SKILL = "skill"
    FLEE = "flee"
    ENDTURN = "endturn"


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
            return self.name
        elif self.combatant_type == CombatantType.MONSTER:
            if world_manager:
                try:
                    if self.data and "monster" in self.data:
                        monster = self.data["monster"]
                        return monster.get_localized_name(locale)
                except Exception:
                    pass
            # data에서 직접 조회
            if self.data and "monster" in self.data:
                try:
                    return self.data["monster"].get_localized_name(locale)
                except Exception:
                    pass
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
