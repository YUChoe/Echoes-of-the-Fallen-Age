"""
몬스터 데이터 모델 및 관련 클래스들
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4
from enum import Enum

from ..database.repository import BaseModel


class MonsterType(Enum):
    """몬스터 타입"""
    AGGRESSIVE = "aggressive"  # 선공형 (플레이어를 보면 공격)
    PASSIVE = "passive"        # 후공형 (공격받으면 반격)
    NEUTRAL = "neutral"        # 중립형 (공격받아도 반격하지 않음)


class MonsterBehavior(Enum):
    """몬스터 행동 패턴"""
    STATIONARY = "stationary"  # 고정형 (제자리에서 대기)
    ROAMING = "roaming"        # 로밍형 (주변을 돌아다님)
    TERRITORIAL = "territorial" # 영역형 (특정 영역 내에서만 이동)


@dataclass
class MonsterStats:
    """몬스터 능력치"""
    max_hp: int = 100
    current_hp: int = 100
    attack_power: int = 10
    defense: int = 5
    speed: int = 10
    accuracy: int = 80  # 명중률 (%)
    critical_chance: int = 5  # 크리티컬 확률 (%)

    def __post_init__(self):
        """초기화 후 현재 HP를 최대 HP로 설정"""
        if self.current_hp <= 0:
            self.current_hp = self.max_hp

    def is_alive(self) -> bool:
        """생존 여부 확인"""
        return self.current_hp > 0

    def take_damage(self, damage: int) -> int:
        """데미지를 받고 실제 받은 데미지 반환"""
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

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'max_hp': self.max_hp,
            'current_hp': self.current_hp,
            'attack_power': self.attack_power,
            'defense': self.defense,
            'speed': self.speed,
            'accuracy': self.accuracy,
            'critical_chance': self.critical_chance
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MonsterStats':
        """딕셔너리에서 생성"""
        return cls(**data)


@dataclass
class DropItem:
    """드롭 아이템 정보"""
    item_id: str
    drop_chance: float  # 0.0 ~ 1.0 (0% ~ 100%)
    min_quantity: int = 1
    max_quantity: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'item_id': self.item_id,
            'drop_chance': self.drop_chance,
            'min_quantity': self.min_quantity,
            'max_quantity': self.max_quantity
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DropItem':
        """딕셔너리에서 생성"""
        return cls(**data)


@dataclass
class Monster(BaseModel):
    """몬스터 모델"""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: Dict[str, str] = field(default_factory=dict)  # {'en': 'name', 'ko': '이름'}
    description: Dict[str, str] = field(default_factory=dict)
    monster_type: MonsterType = MonsterType.PASSIVE
    behavior: MonsterBehavior = MonsterBehavior.STATIONARY
    stats: MonsterStats = field(default_factory=MonsterStats)
    experience_reward: int = 50  # 처치 시 주는 경험치
    gold_reward: int = 10  # 처치 시 주는 골드
    drop_items: List[DropItem] = field(default_factory=list)  # 드롭 아이템 목록
    spawn_room_id: Optional[str] = None  # 스폰 방 ID
    current_room_id: Optional[str] = None  # 현재 위치한 방 ID
    respawn_time: int = 300  # 리스폰 시간 (초)
    last_death_time: Optional[datetime] = None  # 마지막 사망 시간
    is_alive: bool = True  # 생존 상태
    aggro_range: int = 1  # 어그로 범위 (방 단위)
    roaming_range: int = 2  # 로밍 범위 (방 단위)
    properties: Dict[str, Any] = field(default_factory=dict)  # 추가 속성
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """초기화 후 검증"""
        self.validate()
        # 현재 방이 설정되지 않았으면 스폰 방으로 설정
        if not self.current_room_id and self.spawn_room_id:
            self.current_room_id = self.spawn_room_id

    def validate(self) -> None:
        """몬스터 데이터 유효성 검증"""
        if not isinstance(self.name, dict):
            raise ValueError("몬스터 이름은 딕셔너리 형태여야 합니다")

        if not self.name.get('en') and not self.name.get('ko'):
            raise ValueError("몬스터 이름은 최소 하나의 언어로 설정되어야 합니다")

        if not isinstance(self.description, dict):
            raise ValueError("몬스터 설명은 딕셔너리 형태여야 합니다")

        if not isinstance(self.monster_type, MonsterType):
            raise ValueError("올바르지 않은 몬스터 타입입니다")

        if not isinstance(self.behavior, MonsterBehavior):
            raise ValueError("올바르지 않은 몬스터 행동 패턴입니다")

        if not isinstance(self.stats, MonsterStats):
            raise ValueError("몬스터 능력치는 MonsterStats 객체여야 합니다")

        if self.experience_reward < 0:
            raise ValueError("경험치 보상은 0 이상이어야 합니다")

        if self.gold_reward < 0:
            raise ValueError("골드 보상은 0 이상이어야 합니다")

        if not isinstance(self.drop_items, list):
            raise ValueError("드롭 아이템은 리스트 형태여야 합니다")

        if self.respawn_time < 0:
            raise ValueError("리스폰 시간은 0 이상이어야 합니다")

        if self.aggro_range < 0:
            raise ValueError("어그로 범위는 0 이상이어야 합니다")

        if self.roaming_range < 0:
            raise ValueError("로밍 범위는 0 이상이어야 합니다")

    def get_localized_name(self, locale: str = 'en') -> str:
        """로케일에 따른 몬스터 이름 반환"""
        return self.name.get(locale, self.name.get('en', self.name.get('ko', 'Unknown Monster')))

    def get_localized_description(self, locale: str = 'en') -> str:
        """로케일에 따른 몬스터 설명 반환"""
        return self.description.get(locale, self.description.get('en', self.description.get('ko', 'No description available.')))

    def is_aggressive(self) -> bool:
        """선공형 몬스터인지 확인"""
        return self.monster_type == MonsterType.AGGRESSIVE

    def is_passive(self) -> bool:
        """후공형 몬스터인지 확인"""
        return self.monster_type == MonsterType.PASSIVE

    def is_neutral(self) -> bool:
        """중립형 몬스터인지 확인"""
        return self.monster_type == MonsterType.NEUTRAL

    def can_roam(self) -> bool:
        """로밍 가능한지 확인"""
        return self.behavior in [MonsterBehavior.ROAMING, MonsterBehavior.TERRITORIAL]

    def is_ready_to_respawn(self) -> bool:
        """리스폰 가능한지 확인"""
        if self.is_alive or not self.last_death_time:
            return False

        time_since_death = (datetime.now() - self.last_death_time).total_seconds()
        return time_since_death >= self.respawn_time

    def die(self) -> None:
        """몬스터 사망 처리"""
        self.is_alive = False
        self.last_death_time = datetime.now()
        self.stats.current_hp = 0

    def respawn(self) -> None:
        """몬스터 리스폰 처리"""
        self.is_alive = True
        self.last_death_time = None
        self.stats.current_hp = self.stats.max_hp
        # 스폰 방으로 이동
        if self.spawn_room_id:
            self.current_room_id = self.spawn_room_id

    def get_drop_items(self) -> List[Dict[str, Any]]:
        """실제 드롭될 아이템 목록 계산"""
        import random

        dropped_items = []
        for drop_item in self.drop_items:
            if random.random() <= drop_item.drop_chance:
                quantity = random.randint(drop_item.min_quantity, drop_item.max_quantity)
                dropped_items.append({
                    'item_id': drop_item.item_id,
                    'quantity': quantity
                })

        return dropped_items

    def get_property(self, key: str, default: Any = None) -> Any:
        """속성 값 조회"""
        return self.properties.get(key, default)

    def set_property(self, key: str, value: Any) -> None:
        """속성 값 설정"""
        self.properties[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (데이터베이스 스키마에 맞게)"""
        # BaseModel.to_dict() 호출 전에 DropItem 객체들을 딕셔너리로 변환
        original_drop_items = self.drop_items
        if isinstance(self.drop_items, list):
            # 타입 체크를 위해 임시 변수 사용
            temp_drop_items: List[Dict[str, Any]] = []
            for item in self.drop_items:
                if isinstance(item, DropItem):
                    temp_drop_items.append(item.to_dict())
                else:
                    temp_drop_items.append(item)
            self.drop_items = temp_drop_items  # type: ignore

        # BaseModel의 to_dict 호출
        data = super().to_dict()

        # 원본 drop_items 복원
        self.drop_items = original_drop_items

        # name과 description을 개별 컬럼으로 분리
        if 'name' in data:
            name_dict = data.pop('name')
            if isinstance(name_dict, str):
                try:
                    name_dict = json.loads(name_dict)
                except (json.JSONDecodeError, TypeError):
                    name_dict = {}
            data['name_en'] = name_dict.get('en', '') if isinstance(name_dict, dict) else ''
            data['name_ko'] = name_dict.get('ko', '') if isinstance(name_dict, dict) else ''

        if 'description' in data:
            desc_dict = data.pop('description')
            if isinstance(desc_dict, str):
                try:
                    desc_dict = json.loads(desc_dict)
                except (json.JSONDecodeError, TypeError):
                    desc_dict = {}
            data['description_en'] = desc_dict.get('en', '') if isinstance(desc_dict, dict) else ''
            data['description_ko'] = desc_dict.get('ko', '') if isinstance(desc_dict, dict) else ''

        # Enum 값을 문자열로 변환
        if 'monster_type' in data:
            data['monster_type'] = data['monster_type'].value if isinstance(data['monster_type'], MonsterType) else data['monster_type']

        if 'behavior' in data:
            data['behavior'] = data['behavior'].value if isinstance(data['behavior'], MonsterBehavior) else data['behavior']

        # MonsterStats를 JSON 문자열로 변환
        if 'stats' in data and isinstance(data['stats'], MonsterStats):
            data['stats'] = json.dumps(data['stats'].to_dict(), ensure_ascii=False)

        # DropItem 리스트를 JSON 문자열로 변환
        if 'drop_items' in data and isinstance(data['drop_items'], list):
            drop_items_data = []
            for item in data['drop_items']:
                if isinstance(item, DropItem):
                    drop_items_data.append(item.to_dict())
                else:
                    drop_items_data.append(item)
            data['drop_items'] = json.dumps(drop_items_data, ensure_ascii=False)

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Monster':
        """딕셔너리에서 모델 생성"""
        converted_data = data.copy()

        # DB 컬럼명을 딕셔너리 필드로 통합
        if 'name' not in converted_data:
            converted_data['name'] = {}
        if 'description' not in converted_data:
            converted_data['description'] = {}

        if 'name_en' in converted_data:
            converted_data['name']['en'] = converted_data.pop('name_en')
        if 'name_ko' in converted_data:
            converted_data['name']['ko'] = converted_data.pop('name_ko')
        if 'description_en' in converted_data:
            converted_data['description']['en'] = converted_data.pop('description_en')
        if 'description_ko' in converted_data:
            converted_data['description']['ko'] = converted_data.pop('description_ko')

        # Enum 변환
        if 'monster_type' in converted_data:
            if isinstance(converted_data['monster_type'], str):
                converted_data['monster_type'] = MonsterType(converted_data['monster_type'])

        if 'behavior' in converted_data:
            if isinstance(converted_data['behavior'], str):
                converted_data['behavior'] = MonsterBehavior(converted_data['behavior'])

        # MonsterStats 변환
        if 'stats' in converted_data:
            stats_data = converted_data['stats']
            if isinstance(stats_data, str):
                try:
                    stats_dict = json.loads(stats_data)
                    converted_data['stats'] = MonsterStats.from_dict(stats_dict)
                except (json.JSONDecodeError, TypeError):
                    converted_data['stats'] = MonsterStats()
            elif isinstance(stats_data, dict):
                converted_data['stats'] = MonsterStats.from_dict(stats_data)
        else:
            converted_data['stats'] = MonsterStats()

        # DropItem 리스트 변환
        if 'drop_items' in converted_data:
            drop_items_data = converted_data['drop_items']
            if isinstance(drop_items_data, str):
                try:
                    drop_items_list = json.loads(drop_items_data)
                    converted_data['drop_items'] = [DropItem.from_dict(item) for item in drop_items_list]
                except (json.JSONDecodeError, TypeError):
                    converted_data['drop_items'] = []
            elif isinstance(drop_items_data, list):
                converted_data['drop_items'] = [
                    DropItem.from_dict(item) if isinstance(item, dict) else item
                    for item in drop_items_data
                ]
        else:
            converted_data['drop_items'] = []

        # properties 필드 처리
        if 'properties' in converted_data:
            properties_data = converted_data['properties']
            if isinstance(properties_data, str):
                try:
                    converted_data['properties'] = json.loads(properties_data)
                except (json.JSONDecodeError, TypeError):
                    converted_data['properties'] = {}
            elif not isinstance(properties_data, dict):
                converted_data['properties'] = {}
        else:
            converted_data['properties'] = {}

        # 날짜 필드 처리
        for date_field in ['created_at', 'last_death_time']:
            if date_field in converted_data and isinstance(converted_data[date_field], str):
                try:
                    converted_data[date_field] = datetime.fromisoformat(converted_data[date_field].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    if date_field == 'created_at':
                        converted_data[date_field] = datetime.now()
                    else:
                        converted_data[date_field] = None

        return cls(**converted_data)