import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from ...database.repository import BaseModel
from ..stats import PlayerStats


@dataclass
class Room(BaseModel):
    """방 모델 (좌표 기반 이동 시스템)"""

    id: str = field(default_factory=lambda: str(uuid4()))
    description: Dict[str, str] = field(default_factory=dict)
    x: Optional[int] = None  # X 좌표
    y: Optional[int] = None  # Y 좌표
    blocked_exits: List[str] = field(default_factory=list)  # 막힌 출구 방향 (예: ["north", "west"])
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """초기화 후 검증"""
        self.validate()

    def validate(self) -> None:
        """방 데이터 유효성 검증"""
        if not isinstance(self.description, dict):
            raise ValueError("방 설명은 딕셔너리 형태여야 합니다")

    def get_localized_description(self, locale: str = "en") -> str:
        """로케일에 따른 방 설명 반환"""
        return self.description.get(
            locale,
            self.description.get(
                "en", self.description.get("ko", "No description available.")
            ),
        )

    def get_available_exits(self, room_repository=None) -> List[str]:
        """좌표 기반으로 사용 가능한 출구 방향 목록 반환"""
        if self.x is None or self.y is None:
            return []

        exits = []
        # x+1: 동쪽, x-1: 서쪽, y+1: 북쪽, y-1: 남쪽
        directions = [
            ("east", self.x + 1, self.y),
            ("west", self.x - 1, self.y),
            ("north", self.x, self.y + 1),
            ("south", self.x, self.y - 1),
        ]

        # room_repository가 제공된 경우 실제 방 존재 여부 확인
        if room_repository:
            import asyncio

            try:
                for direction, target_x, target_y in directions:
                    # 비동기 함수를 동기적으로 호출 (주의: 이벤트 루프 내에서만 사용)
                    if hasattr(room_repository, "get_room_by_coordinates"):
                        # 실제 구현에서는 비동기 처리 필요
                        exits.append(direction)  # 임시로 모든 방향 허용
            except Exception:
                # 에러 발생 시 기본 방향들 반환
                exits = ["north", "south", "east", "west"]
        else:
            # repository가 없으면 모든 방향 허용 (기본 동작)
            exits = ["north", "south", "east", "west"]

        return exits

    def get_coordinates(self) -> Tuple[int, int]:
        """방의 좌표 반환"""
        return (self.x or 0, self.y or 0)

    def set_coordinates(self, x: int, y: int) -> None:
        """방의 좌표 설정"""
        self.x = x
        self.y = y
        self.updated_at = datetime.now()

    def is_at_coordinates(self, x: int, y: int) -> bool:
        """특정 좌표에 위치하는지 확인"""
        return self.x == x and self.y == y

    def get_target_coordinates(self, direction: str) -> Optional[Tuple[int, int]]:
        """방향에 따른 목표 좌표 반환"""
        if self.x is None or self.y is None:
            return None

        direction_map = {
            "east": (self.x + 1, self.y),
            "west": (self.x - 1, self.y),
            "north": (self.x, self.y + 1),
            "south": (self.x, self.y - 1),
        }

        return direction_map.get(direction.lower())

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (데이터베이스 스키마에 맞게)"""
        data = super().to_dict()

        # description을 개별 컬럼으로 분리
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

        # blocked_exits를 JSON 문자열로 변환
        if "blocked_exits" in data and isinstance(data["blocked_exits"], list):
            data["blocked_exits"] = json.dumps(data["blocked_exits"], ensure_ascii=False)

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Room":
        """딕셔너리에서 모델 생성"""
        # 데이터베이스 컬럼명을 모델 필드로 변환
        converted_data = data.copy()

        # description 통합
        if "description" not in converted_data:
            converted_data["description"] = {}
        if "description_en" in converted_data:
            converted_data["description"]["en"] = converted_data.pop("description_en")
        if "description_ko" in converted_data:
            converted_data["description"]["ko"] = converted_data.pop("description_ko")

        # 날짜 필드 처리 (문자열을 datetime 객체로 변환)
        for date_field in ["created_at", "updated_at"]:
            if date_field in converted_data and isinstance(
                converted_data[date_field], str
            ):
                try:
                    from datetime import datetime

                    converted_data[date_field] = datetime.fromisoformat(
                        converted_data[date_field].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    converted_data[date_field] = datetime.now()

        # blocked_exits JSON 파싱
        if "blocked_exits" in converted_data:
            if isinstance(converted_data["blocked_exits"], str):
                try:
                    converted_data["blocked_exits"] = json.loads(converted_data["blocked_exits"])
                except (json.JSONDecodeError, TypeError):
                    converted_data["blocked_exits"] = []
            elif not isinstance(converted_data["blocked_exits"], list):
                converted_data["blocked_exits"] = []
        else:
            converted_data["blocked_exits"] = []

        # exits 필드 제거 (더 이상 사용하지 않음)
        converted_data.pop("exits", None)

        return cls(**converted_data)
