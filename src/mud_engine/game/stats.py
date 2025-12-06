"""
플레이어 능력치 시스템
"""

import json
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum


class StatType(Enum):
    """능력치 타입 정의"""
    # 1차 능력치 (기본 스탯)
    STR = "strength"      # 힘 - 물리 공격력, 소지 무게에 영향
    DEX = "dexterity"     # 민첩 - 회피율, 명중률, 속도에 영향
    INT = "intelligence"  # 지능 - 마법 공격력, MP에 영향
    WIS = "wisdom"        # 지혜 - 마법 방어력, MP 회복에 영향
    CON = "constitution"  # 체력 - HP, 스태미나에 영향
    CHA = "charisma"      # 매력 - NPC 상호작용, 거래에 영향

    # 2차 능력치 (파생 스탯)
    HP = "health_points"     # 생명력
    MP = "mana_points"       # 마나
    STA = "stamina"          # 스태미나
    ATK = "attack"           # 공격력
    DEF = "defense"          # 방어력
    SPD = "speed"            # 속도
    RES = "resistance"       # 마법 저항력
    LCK = "luck"             # 운
    INF = "influence"        # 영향력 (매력 기반)


@dataclass
class PlayerStats:
    """플레이어 능력치 클래스"""

    # 1차 능력치 (기본 스탯) - 기본값 10
    strength: int = 10
    dexterity: int = 10
    intelligence: int = 10
    wisdom: int = 10
    constitution: int = 10
    charisma: int = 10

    # 레벨 관련
    level: int = 1

    # 장비 보너스 (착용한 장비로부터 받는 추가 능력치)
    equipment_bonuses: Dict[str, int] = field(default_factory=dict)

    # 임시 효과 (버프/디버프)
    temporary_effects: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        """초기화 후 검증"""
        self.validate()

    def validate(self) -> None:
        """능력치 데이터 유효성 검증"""
        # 1차 능력치는 1-100 범위
        primary_stats = [self.strength, self.dexterity, self.intelligence,
                        self.wisdom, self.constitution, self.charisma]

        for stat in primary_stats:
            if not isinstance(stat, int) or stat < 1 or stat > 100:
                raise ValueError("1차 능력치는 1-100 범위의 정수여야 합니다")

        if self.level < 1 or self.level > 100:
            raise ValueError("레벨은 1-100 범위여야 합니다")

    def get_primary_stat(self, stat_type: StatType) -> int:
        """1차 능력치 조회 (장비 보너스 포함)"""
        base_value = getattr(self, stat_type.value, 0)
        equipment_bonus = self.equipment_bonuses.get(stat_type.value, 0)
        return base_value + equipment_bonus

    def get_secondary_stat(self, stat_type: StatType) -> int:
        """2차 능력치 계산 및 조회"""
        if stat_type == StatType.HP:
            return self._calculate_hp()
        elif stat_type == StatType.MP:
            return self._calculate_mp()
        elif stat_type == StatType.STA:
            return self._calculate_stamina()
        elif stat_type == StatType.ATK:
            return self._calculate_attack()
        elif stat_type == StatType.DEF:
            return self._calculate_defense()
        elif stat_type == StatType.SPD:
            return self._calculate_speed()
        elif stat_type == StatType.RES:
            return self._calculate_resistance()
        elif stat_type == StatType.LCK:
            return self._calculate_luck()
        elif stat_type == StatType.INF:
            return self._calculate_influence()
        else:
            return 0

    def _calculate_hp(self) -> int:
        """HP 계산: 기본 100 + (체력 * 5) + (레벨 * 10)"""
        base_hp = 100
        con_bonus = self.get_primary_stat(StatType.CON) * 5
        level_bonus = self.level * 10
        return base_hp + con_bonus + level_bonus

    def _calculate_mp(self) -> int:
        """MP 계산: 기본 50 + (지능 * 3) + (지혜 * 2) + (레벨 * 5)"""
        base_mp = 50
        int_bonus = self.get_primary_stat(StatType.INT) * 3
        wis_bonus = self.get_primary_stat(StatType.WIS) * 2
        level_bonus = self.level * 5
        return base_mp + int_bonus + wis_bonus + level_bonus

    def _calculate_stamina(self) -> int:
        """스태미나 계산: 기본 100 + (체력 * 3) + (민첩 * 2)"""
        base_sta = 100
        con_bonus = self.get_primary_stat(StatType.CON) * 3
        dex_bonus = self.get_primary_stat(StatType.DEX) * 2
        return base_sta + con_bonus + dex_bonus

    def _calculate_attack(self) -> int:
        """공격력 계산: 기본 10 + (힘 * 2) + (레벨)"""
        base_atk = 10
        str_bonus = self.get_primary_stat(StatType.STR) * 2
        level_bonus = self.level
        return base_atk + str_bonus + level_bonus

    def _calculate_defense(self) -> int:
        """방어력 계산: 기본 5 + (체력 * 1.5) + (레벨 * 0.5)"""
        base_def = 5
        con_bonus = int(self.get_primary_stat(StatType.CON) * 1.5)
        level_bonus = int(self.level * 0.5)
        return base_def + con_bonus + level_bonus

    def _calculate_speed(self) -> int:
        """속도 계산: 기본 10 + (민첩 * 1.5)"""
        base_spd = 10
        dex_bonus = int(self.get_primary_stat(StatType.DEX) * 1.5)
        return base_spd + dex_bonus

    def _calculate_resistance(self) -> int:
        """마법 저항력 계산: 기본 5 + (지혜 * 1.5) + (레벨 * 0.3)"""
        base_res = 5
        wis_bonus = int(self.get_primary_stat(StatType.WIS) * 1.5)
        level_bonus = int(self.level * 0.3)
        return base_res + wis_bonus + level_bonus

    def _calculate_luck(self) -> int:
        """운 계산: 기본 10 + (모든 능력치 평균 / 10)"""
        base_lck = 10
        avg_stats = (self.get_primary_stat(StatType.STR) +
                    self.get_primary_stat(StatType.DEX) +
                    self.get_primary_stat(StatType.INT) +
                    self.get_primary_stat(StatType.WIS) +
                    self.get_primary_stat(StatType.CON) +
                    self.get_primary_stat(StatType.CHA)) / 6
        avg_bonus = int(avg_stats / 10)
        return base_lck + avg_bonus

    def _calculate_influence(self) -> int:
        """영향력 계산: 기본 5 + (매력 * 2) + (레벨 * 0.5)"""
        base_inf = 5
        cha_bonus = self.get_primary_stat(StatType.CHA) * 2
        level_bonus = int(self.level * 0.5)
        return base_inf + cha_bonus + level_bonus

    def get_max_carry_weight(self) -> int:
        """최대 소지 무게 계산: 기본 50 + (힘 * 5)"""
        base_weight = 50
        str_bonus = self.get_primary_stat(StatType.STR) * 5
        return base_weight + str_bonus

    def add_equipment_bonus(self, stat_name: str, bonus: int) -> None:
        """장비 보너스 추가"""
        if stat_name not in self.equipment_bonuses:
            self.equipment_bonuses[stat_name] = 0
        self.equipment_bonuses[stat_name] += bonus

    def remove_equipment_bonus(self, stat_name: str, bonus: int) -> None:
        """장비 보너스 제거"""
        if stat_name in self.equipment_bonuses:
            self.equipment_bonuses[stat_name] -= bonus
            if self.equipment_bonuses[stat_name] <= 0:
                del self.equipment_bonuses[stat_name]



    def level_up_stat(self, stat_type: StatType, points: int = 1) -> bool:
        """능력치 레벨업 (스탯 포인트 사용)"""
        if stat_type in [StatType.STR, StatType.DEX, StatType.INT,
                        StatType.WIS, StatType.CON, StatType.CHA]:
            current_value = getattr(self, stat_type.value)
            if current_value + points <= 100:
                setattr(self, stat_type.value, current_value + points)
                return True
        return False

    def get_all_stats(self) -> Dict[str, int]:
        """모든 능력치 조회"""
        stats = {}

        # 1차 능력치
        for stat_type in [StatType.STR, StatType.DEX, StatType.INT,
                         StatType.WIS, StatType.CON, StatType.CHA]:
            stats[stat_type.value] = self.get_primary_stat(stat_type)

        # 2차 능력치
        for stat_type in [StatType.HP, StatType.MP, StatType.STA,
                         StatType.ATK, StatType.DEF, StatType.SPD,
                         StatType.RES, StatType.LCK, StatType.INF]:
            stats[stat_type.value] = self.get_secondary_stat(stat_type)

        # 레벨 정보
        stats['level'] = self.level
        stats['max_carry_weight'] = self.get_max_carry_weight()

        return stats

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (데이터베이스 저장용)"""
        return {
            'strength': self.strength,
            'dexterity': self.dexterity,
            'intelligence': self.intelligence,
            'wisdom': self.wisdom,
            'constitution': self.constitution,
            'charisma': self.charisma,
            'level': self.level,
            'equipment_bonuses': json.dumps(self.equipment_bonuses, ensure_ascii=False),
            'temporary_effects': json.dumps(self.temporary_effects, ensure_ascii=False)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlayerStats':
        """딕셔너리에서 객체 생성"""
        # 하위 호환성: 경험치 필드 제거 (더 이상 사용하지 않음)
        data_copy = data.copy()
        data_copy.pop('experience', None)
        data_copy.pop('experience_to_next', None)
        
        # JSON 문자열 필드 파싱
        if isinstance(data_copy.get('equipment_bonuses'), str):
            try:
                data_copy['equipment_bonuses'] = json.loads(data_copy['equipment_bonuses'])
            except (json.JSONDecodeError, TypeError):
                data_copy['equipment_bonuses'] = {}

        if isinstance(data_copy.get('temporary_effects'), str):
            try:
                data_copy['temporary_effects'] = json.loads(data_copy['temporary_effects'])
            except (json.JSONDecodeError, TypeError):
                data_copy['temporary_effects'] = {}

        # 기본값 설정
        for field in ['equipment_bonuses', 'temporary_effects']:
            if field not in data_copy:
                data_copy[field] = {}

        return cls(**data_copy)


@dataclass
class StatCalculator:
    """능력치 계산 유틸리티 클래스"""

    @staticmethod
    def calculate_success_rate(base_stat: int, difficulty: int = 50,
                             luck_modifier: int = 0) -> float:
        """
        행동 성공률 계산

        Args:
            base_stat: 기본 능력치
            difficulty: 난이도 (기본 50)
            luck_modifier: 운 보정값

        Returns:
            float: 성공률 (0.0 ~ 1.0)
        """
        # 기본 공식: (능력치 + 운보정) / (능력치 + 운보정 + 난이도)
        adjusted_stat = max(1, base_stat + luck_modifier)
        success_rate = adjusted_stat / (adjusted_stat + difficulty)

        # 최소 5%, 최대 95% 제한
        return max(0.05, min(0.95, success_rate))

    @staticmethod
    def calculate_damage(attack_stat: int, defense_stat: int,
                        weapon_damage: int = 0, luck_modifier: int = 0) -> int:
        """
        데미지 계산

        Args:
            attack_stat: 공격력
            defense_stat: 방어력
            weapon_damage: 무기 데미지
            luck_modifier: 운 보정값

        Returns:
            int: 최종 데미지
        """
        base_damage = attack_stat + weapon_damage + luck_modifier
        damage_reduction = defense_stat * 0.5
        final_damage = max(1, int(base_damage - damage_reduction))

        return final_damage

    @staticmethod
    def calculate_critical_chance(dexterity: int, luck: int) -> float:
        """
        크리티컬 확률 계산

        Args:
            dexterity: 민첩성
            luck: 운

        Returns:
            float: 크리티컬 확률 (0.0 ~ 1.0)
        """
        base_chance = 0.05  # 기본 5%
        dex_bonus = dexterity * 0.001  # 민첩 1당 0.1%
        luck_bonus = luck * 0.002  # 운 1당 0.2%

        total_chance = base_chance + dex_bonus + luck_bonus
        return min(0.5, total_chance)  # 최대 50% 제한