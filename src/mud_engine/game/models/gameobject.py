import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from ...database.repository import BaseModel
from ..stats import PlayerStats


@dataclass
class GameObject(BaseModel):
    """게임 객체 모델"""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: Dict[str, str] = field(default_factory=dict)  # {'en': 'name', 'ko': '이름'}
    description: Dict[str, str] = field(default_factory=dict)
    location_type: str = ""  # 'room', 'inventory'
    location_id: Optional[str] = None  # room_id 또는 character_id
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0  # 무게 (kg 단위)
    max_stack: int = 1  # 최대 스택 개수 (1이면 스택 불가)
    equipment_slot: Optional[str] = None  # 장비 슬롯: weapon, armor, accessory
    is_equipped: bool = False  # 착용 여부
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """초기화 후 검증"""
        self.validate()

    def validate(self) -> None:
        """게임 객체 데이터 유효성 검증"""
        if not isinstance(self.name, dict):
            raise ValueError("객체 이름은 딕셔너리 형태여야 합니다")

        if not self.name.get("en") and not self.name.get("ko"):
            raise ValueError("객체 이름은 최소 하나의 언어로 설정되어야 합니다")

        if not isinstance(self.description, dict):
            raise ValueError("객체 설명은 딕셔너리 형태여야 합니다")

        if not self.location_type:
            raise ValueError("위치 타입은 필수입니다")

        valid_location_types = {
            "room",
            "inventory",
            "container",
            "template",
            "ROOM",
            "INVENTORY",
            "CONTAINER",
            "TEMPLATE",
        }
        if self.location_type not in valid_location_types:
            raise ValueError(f"올바르지 않은 위치 타입입니다: {self.location_type}")

        if not isinstance(self.properties, dict):
            raise ValueError("속성은 딕셔너리 형태여야 합니다")

        # 무게 검증
        if not isinstance(self.weight, (int, float)) or self.weight < 0:
            raise ValueError("무게는 0 이상의 숫자여야 합니다")

        # max_stack 검증
        if not isinstance(self.max_stack, int) or self.max_stack < 1:
            raise ValueError("최대 스택 개수는 1 이상의 정수여야 합니다")

        # 장비 슬롯 검증
        if self.equipment_slot is not None:
            valid_slots = {
                "head",  # 머리: 모자, 헬맷, 두건 등 방어구
                "shoulder",  # 어깨: 방어구
                "chest",  # 몸통: 방어구
                "right_arm",  # 오른팔: 방어구
                "left_arm",  # 왼팔: 방어구
                "right_hand",  # 오른손: 무기
                "left_hand",  # 왼손: 무기, 방어구
                "waist",  # 허리: 벨트, 스태시 등
                "legs",  # 다리: 바지, 스커트 등 방어구
                "feet",  # 발: 신발류 방어구
                "back",  # 등: 방어구
                "ring",  # 반지
                "RING",  # 반지 (대문자)
                "weapon",  # 기존 호환성을 위한 일반 무기
                "armor",  # 기존 호환성을 위한 일반 방어구
                "accessory",  # 기존 호환성을 위한 액세서리
            }
            if self.equipment_slot not in valid_slots:
                raise ValueError(
                    f"올바르지 않은 장비 슬롯입니다: {self.equipment_slot}"
                )

    def get_localized_name(self, locale: str = "en") -> str:
        """로케일에 따른 객체 이름 반환"""
        return self.name.get(
            locale, self.name.get("en", self.name.get("ko", "Unknown Object"))
        )

    def get_localized_description(self, locale: str = "en") -> str:
        """로케일에 따른 객체 설명 반환"""
        return self.description.get(
            locale,
            self.description.get(
                "en", self.description.get("ko", "No description available.")
            ),
        )

    def is_stackable(self) -> bool:
        """스택 가능한 아이템인지 확인"""
        return self.max_stack > 1

    def get_property(self, key: str, default: Any = None) -> Any:
        """속성 값 조회"""
        return self.properties.get(key, default)

    def set_property(self, key: str, value: Any) -> None:
        """속성 값 설정"""
        self.properties[key] = value

    def move_to_room(self, room_id: str) -> None:
        """방으로 이동"""
        self.location_type = "room"
        self.location_id = room_id

    def move_to_inventory(self, character_id: str) -> None:
        """인벤토리로 이동"""
        self.location_type = "inventory"
        self.location_id = character_id

    def is_in_room(self, room_id: str) -> bool:
        """특정 방에 있는지 확인"""
        return self.location_type == "room" and self.location_id == room_id

    def is_in_inventory(self, character_id: str) -> bool:
        """특정 캐릭터의 인벤토리에 있는지 확인"""
        return self.location_type == "inventory" and self.location_id == character_id

    def can_be_equipped(self) -> bool:
        """장비할 수 있는 아이템인지 확인"""
        return self.equipment_slot is not None

    def equip(self) -> None:
        """아이템 착용"""
        if not self.can_be_equipped():
            raise ValueError("이 아이템은 착용할 수 없습니다")
        self.is_equipped = True

    def unequip(self) -> None:
        """아이템 착용 해제"""
        self.is_equipped = False

    def get_weight_display(self) -> str:
        """무게를 표시용 문자열로 반환"""
        if self.weight < 1.0:
            return f"{int(self.weight * 1000)}g"
        else:
            return f"{self.weight:.1f}kg"

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (데이터베이스 스키마에 맞게)"""
        data = super().to_dict()

        # name과 description을 개별 컬럼으로 분리하고 원본 제거
        if "name" in data:
            name_dict = data.pop("name")
            # BaseModel에서 이미 JSON 문자열로 변환된 경우 다시 파싱
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
            # BaseModel에서 이미 JSON 문자열로 변환된 경우 다시 파싱
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

        # properties는 JSON 문자열로 유지 (BaseModel에서 이미 변환됨)
        # 추가 처리 불필요

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameObject":
        """딕셔너리에서 모델 생성"""
        # 데이터베이스 컬럼명을 모델 필드명으로 변환
        converted_data: Dict[str, Any] = {}

        for key, value in data.items():
            if key == "name_en" or key == "name_ko":
                # name_en, name_ko를 name 딕셔너리로 변환
                if "name" not in converted_data:
                    converted_data["name"] = {}
                locale = "en" if key == "name_en" else "ko"
                converted_data["name"][locale] = value
            elif key == "description_en" or key == "description_ko":
                # description_en, description_ko를 description 딕셔너리로 변환
                if "description" not in converted_data:
                    converted_data["description"] = {}
                locale = "en" if key == "description_en" else "ko"
                converted_data["description"][locale] = value
            elif key == "properties":
                # properties JSON 문자열을 딕셔너리로 변환
                if isinstance(value, str):
                    try:
                        converted_data[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        converted_data[key] = {}
                else:
                    converted_data[key] = value or {}
            elif key in ["object_type", "category"]:
                # 제거된 필드들은 무시
                continue
            else:
                converted_data[key] = value

        # 필수 필드 기본값 설정
        if "name" not in converted_data:
            converted_data["name"] = {}
        if "description" not in converted_data:
            converted_data["description"] = {}
        if "properties" not in converted_data:
            converted_data["properties"] = {}

        # 날짜 필드 처리 (문자열을 datetime 객체로 변환)
        for date_field in ["created_at"]:
            if date_field in converted_data and isinstance(
                converted_data[date_field], str
            ):
                try:
                    from datetime import datetime

                    converted_data[date_field] = datetime.fromisoformat(
                        converted_data[date_field].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    # 파싱 실패 시 현재 시간으로 설정
                    converted_data[date_field] = datetime.now()

        return cls(**converted_data)
