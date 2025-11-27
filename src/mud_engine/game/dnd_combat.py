# -*- coding: utf-8 -*-
"""D&D 5e 기반 전투 시스템"""

import logging
import random
from dataclasses import dataclass
from typing import Tuple

logger = logging.getLogger(__name__)


@dataclass
class CombatStats:
    """전투 능력치"""
    max_hp: int
    current_hp: int
    armor_class: int
    attack_bonus: int
    damage_dice: str
    initiative_bonus: int


class DnDCombatEngine:
    """D&D 5e 룰 기반 전투 엔진"""
    
    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def roll_d20(self) -> int:
        """d20 주사위 굴리기"""
        return random.randint(1, 20)
    
    def roll_dice(self, dice_notation: str) -> int:
        """주사위 굴리기 (예: 1d8+2, 2d6)"""
        try:
            if '+' in dice_notation:
                dice_part, bonus_str = dice_notation.split('+')
                bonus = int(bonus_str)
            elif '-' in dice_notation:
                dice_part, bonus_str = dice_notation.split('-')
                bonus = -int(bonus_str)
            else:
                dice_part = dice_notation
                bonus = 0
            
            count_str, sides_str = dice_part.split('d')
            count = int(count_str)
            sides = int(sides_str)
            
            total = sum(random.randint(1, sides) for _ in range(count))
            return total + bonus
            
        except Exception as e:
            self.logger.error(f"주사위 파싱 오류: {dice_notation}, {e}")
            return 1
    
    def roll_initiative(self, initiative_bonus: int) -> int:
        """선공 판정"""
        return self.roll_d20() + initiative_bonus
    
    def make_attack_roll(self, attack_bonus: int) -> Tuple[int, bool]:
        """공격 굴림 (d20 + 공격 보너스)"""
        roll = self.roll_d20()
        is_critical = (roll == 20)
        is_fumble = (roll == 1)
        
        if is_fumble:
            return (0, False)
        
        total = roll + attack_bonus
        return (total, is_critical)
    
    def calculate_damage(self, damage_dice: str, is_critical: bool = False) -> int:
        """데미지 계산"""
        damage = self.roll_dice(damage_dice)
        
        if is_critical:
            extra_damage = self.roll_dice(damage_dice)
            damage += extra_damage
            self.logger.info("크리티컬 히트! 데미지 2배")
        
        return max(1, damage)
    
    def check_hit(self, attack_roll: int, target_ac: int) -> bool:
        """명중 판정"""
        return attack_roll >= target_ac
    
    def apply_damage(self, target_hp: int, damage: int) -> int:
        """데미지 적용"""
        new_hp = target_hp - damage
        return max(0, new_hp)
    
    def calculate_initiative_bonus(self, dexterity: int) -> int:
        """민첩 능력치로 선공 보너스 계산"""
        return (dexterity - 10) // 2
    
    def calculate_attack_bonus(self, proficiency: int, ability_modifier: int) -> int:
        """공격 보너스 계산"""
        return proficiency + ability_modifier
    
    def calculate_ability_modifier(self, ability_score: int) -> int:
        """능력치 보정치 계산"""
        return (ability_score - 10) // 2
