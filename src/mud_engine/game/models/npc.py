import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from ...database.repository import BaseModel
from ..stats import PlayerStats


@dataclass
class NPC(BaseModel):
    """NPC 모델"""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: Dict[str, str] = field(default_factory=dict)  # {'en': 'name', 'ko': '이름'}
    description: Dict[str, str] = field(default_factory=dict)
    x: int = 0  # X 좌표
    y: int = 0  # Y 좌표
    npc_type: str = "generic"  # 'merchant', 'guard', 'quest_giver', 'generic'
    dialogue: Dict[str, List[str]] = field(
        default_factory=dict
    )  # {'en': ['line1', 'line2'], 'ko': ['대사1', '대사2']}
    shop_inventory: List[str] = field(default_factory=list)  # 상점 아이템 ID 목록
    properties: Dict[str, Any] = field(default_factory=dict)  # 추가 속성
    is_active: bool = True  # NPC 활성 상태
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """초기화 후 검증"""
        self.validate()

    def validate(self) -> None:
        """NPC 데이터 유효성 검증"""
        if not isinstance(self.name, dict):
            raise ValueError("NPC 이름은 딕셔너리 형태여야 합니다")

        if not self.name.get("en") and not self.name.get("ko"):
            raise ValueError("NPC 이름은 최소 하나의 언어로 설정되어야 합니다")

        if not isinstance(self.description, dict):
            raise ValueError("NPC 설명은 딕셔너리 형태여야 합니다")

        if not isinstance(self.x, int) or not isinstance(self.y, int):
            raise ValueError("NPC의 좌표는 정수여야 합니다")

        valid_npc_types = {"merchant", "guard", "quest_giver", "generic"}
        if self.npc_type not in valid_npc_types:
            raise ValueError(f"올바르지 않은 NPC 타입입니다: {self.npc_type}")

        if not isinstance(self.dialogue, dict):
            raise ValueError("대화는 딕셔너리 형태여야 합니다")

        if not isinstance(self.shop_inventory, list):
            raise ValueError("상점 인벤토리는 리스트 형태여야 합니다")

        if not isinstance(self.properties, dict):
            raise ValueError("속성은 딕셔너리 형태여야 합니다")

    def get_localized_name(self, locale: str = "en") -> str:
        """로케일에 따른 NPC 이름 반환"""
        return self.name.get(
            locale, self.name.get("en", self.name.get("ko", "Unknown NPC"))
        )

    def get_localized_description(self, locale: str = "en") -> str:
        """로케일에 따른 NPC 설명 반환"""
        return self.description.get(
            locale,
            self.description.get(
                "en", self.description.get("ko", "No description available.")
            ),
        )

    def get_dialogue_lines(self, locale: str = "en") -> List[str]:
        """로케일에 따른 대화 대사 반환"""
        return self.dialogue.get(
            locale, self.dialogue.get("en", self.dialogue.get("ko", ["Hello!"]))
        )

    def get_random_dialogue(self, locale: str = "en") -> str:
        """랜덤 대화 대사 반환"""
        import random

        lines = self.get_dialogue_lines(locale)
        return random.choice(lines) if lines else "..."

    def is_merchant(self) -> bool:
        """상인 NPC인지 확인"""
        return self.npc_type == "merchant"

    def has_shop_item(self, item_id: str) -> bool:
        """상점에 특정 아이템이 있는지 확인"""
        return item_id in self.shop_inventory

    def add_shop_item(self, item_id: str) -> None:
        """상점에 아이템 추가"""
        if item_id not in self.shop_inventory:
            self.shop_inventory.append(item_id)

    def remove_shop_item(self, item_id: str) -> bool:
        """상점에서 아이템 제거"""
        if item_id in self.shop_inventory:
            self.shop_inventory.remove(item_id)
            return True
        return False

    def get_property(self, key: str, default: Any = None) -> Any:
        """속성 값 조회"""
        return self.properties.get(key, default)

    def set_property(self, key: str, value: Any) -> None:
        """속성 값 설정"""
        self.properties[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (데이터베이스 스키마에 맞게)"""
        data = super().to_dict()

        # name과 description을 개별 컬럼으로 분리하고 원본 제거
        if "name" in data:
            name_dict = data.pop("name")
            if isinstance(name_dict, str):
                try:
                    name_dict = json.loads(name_dict)
                except (json.JSONDecodeError, TypeError):
                    name_dict = {}
            data["name_en"] = (
                name_dict.get("en", "") if isinstance(name_dict, dict) else ""
            )
            data["name_ko"] = (
                name_dict.get("ko", "") if isinstance(name_dict, dict) else ""
            )

        if "description" in data:
            desc_dict = data.pop("description")
            if isinstance(desc_dict, str):
                try:
                    desc_dict = json.loads(desc_dict)
                except (json.JSONDecodeError, TypeError):
                    desc_dict = {}
            data["description_en"] = (
                desc_dict.get("en", "") if isinstance(desc_dict, dict) else ""
            )
            data["description_ko"] = (
                desc_dict.get("ko", "") if isinstance(desc_dict, dict) else ""
            )

        # dialogue, shop_inventory, properties는 JSON 문자열로 유지
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NPC":
        """딕셔너리에서 모델 생성"""
        converted_data = data.copy()

        # JSON 문자열을 딕셔너리/리스트로 변환
        for key in ["dialogue", "properties"]:
            value = converted_data.get(key)
            if isinstance(value, str):
                try:
                    converted_data[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    converted_data[key] = {}

        # shop_inventory JSON 문자열을 리스트로 변환
        shop_inventory = converted_data.get("shop_inventory")
        if isinstance(shop_inventory, str):
            try:
                converted_data["shop_inventory"] = json.loads(shop_inventory)
            except (json.JSONDecodeError, TypeError):
                converted_data["shop_inventory"] = []

        # DB 컬럼명을 딕셔너리 필드로 통합
        if "name" not in converted_data:
            converted_data["name"] = {}
        if "description" not in converted_data:
            converted_data["description"] = {}

        if "name_en" in converted_data:
            converted_data["name"]["en"] = converted_data.pop("name_en")
        if "name_ko" in converted_data:
            converted_data["name"]["ko"] = converted_data.pop("name_ko")
        if "description_en" in converted_data:
            converted_data["description"]["en"] = converted_data.pop("description_en")
        if "description_ko" in converted_data:
            converted_data["description"]["ko"] = converted_data.pop("description_ko")

        # 필수 필드 기본값 설정
        if "dialogue" not in converted_data:
            converted_data["dialogue"] = {}
        if "shop_inventory" not in converted_data:
            converted_data["shop_inventory"] = []
        if "properties" not in converted_data:
            converted_data["properties"] = {}

        # DB에만 있고 모델에 없는 필드 제거
        if "faction_id" in converted_data:
            converted_data.pop("faction_id")

        # 날짜 필드 처리
        for date_field in ["created_at"]:
            if date_field in converted_data and isinstance(
                converted_data[date_field], str
            ):
                try:
                    converted_data[date_field] = datetime.fromisoformat(
                        converted_data[date_field].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    converted_data[date_field] = datetime.now()

        return cls(**converted_data)
