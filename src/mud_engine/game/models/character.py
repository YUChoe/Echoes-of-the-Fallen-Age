import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from ...database.repository import BaseModel
from ..stats import PlayerStats


@dataclass
class Character(BaseModel):
    """캐릭터 모델"""

    id: str = field(default_factory=lambda: str(uuid4()))
    player_id: str = ""
    name: str = ""
    current_room_id: Optional[str] = None
    inventory: List[str] = field(default_factory=list)  # 객체 ID 목록
    stats: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """초기화 후 검증"""
        self.validate()

    def validate(self) -> None:
        """캐릭터 데이터 유효성 검증"""
        if not self.player_id:
            raise ValueError("플레이어 ID는 필수입니다")

        if not self.name:
            raise ValueError("캐릭터 이름은 필수입니다")

        if not self.is_valid_character_name(self.name):
            raise ValueError("캐릭터 이름은 2-15자의 한글, 영문, 숫자만 허용됩니다")

        if not isinstance(self.inventory, list):
            raise ValueError("인벤토리는 리스트 형태여야 합니다")

        if not isinstance(self.stats, dict):
            raise ValueError("스탯은 딕셔너리 형태여야 합니다")

    @staticmethod
    def is_valid_character_name(name: str) -> bool:
        """캐릭터 이름 유효성 검사"""
        if not name or len(name) < 2 or len(name) > 15:
            return False
        # 한글, 영문, 숫자 허용
        return re.match(r"^[가-힣a-zA-Z0-9\s]+$", name) is not None

    def add_to_inventory(self, object_id: str) -> None:
        """인벤토리에 객체 추가"""
        if object_id not in self.inventory:
            self.inventory.append(object_id)

    def remove_from_inventory(self, object_id: str) -> bool:
        """인벤토리에서 객체 제거"""
        if object_id in self.inventory:
            self.inventory.remove(object_id)
            return True
        return False

    def has_in_inventory(self, object_id: str) -> bool:
        """인벤토리에 객체가 있는지 확인"""
        return object_id in self.inventory

    def get_stat(self, stat_name: str, default: Any = 0) -> Any:
        """스탯 값 조회"""
        return self.stats.get(stat_name, default)

    def set_stat(self, stat_name: str, value: Any) -> None:
        """스탯 값 설정"""
        self.stats[stat_name] = value

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        data = super().to_dict()
        # 리스트와 딕셔너리는 JSON 문자열로 변환
        if isinstance(data.get("inventory"), list):
            data["inventory"] = json.dumps(data["inventory"], ensure_ascii=False)
        if isinstance(data.get("stats"), dict):
            data["stats"] = json.dumps(data["stats"], ensure_ascii=False)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Character":
        """딕셔너리에서 모델 생성"""
        # JSON 문자열을 파이썬 객체로 변환
        if isinstance(data.get("inventory"), str):
            try:
                data["inventory"] = json.loads(data["inventory"])
            except (json.JSONDecodeError, TypeError):
                data["inventory"] = []

        if isinstance(data.get("stats"), str):
            try:
                data["stats"] = json.loads(data["stats"])
            except (json.JSONDecodeError, TypeError):
                data["stats"] = {}

        return cls(**data)
