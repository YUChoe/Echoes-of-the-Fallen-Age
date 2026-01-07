import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from ...database.repository import BaseModel
from ..stats import PlayerStats
from ..stats import StatType
from .gameobject import GameObject


@dataclass
class Player(BaseModel):
    """플레이어 모델"""

    id: str = field(default_factory=lambda: str(uuid4()))
    username: str = ""
    password_hash: str = ""
    email: Optional[str] = None
    preferred_locale: str = "en"
    is_admin: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    last_room_id: str = "town_square"  # 마지막 위치

    # 사용자 이름 시스템
    display_name: Optional[str] = None  # 게임 내 표시 이름
    last_name_change: Optional[datetime] = None  # 마지막 이름 변경 시간

    # 마지막 위치 (좌표)
    last_room_x: int = 0  # 마지막 위치 X 좌표
    last_room_y: int = 0  # 마지막 위치 Y 좌표

    # 능력치 시스템
    stats: PlayerStats = field(default_factory=PlayerStats)

    # 경제 시스템
    gold: int = 100  # 기본 골드 100

    # 세력 시스템
    faction_id: Optional[str] = "ash_knights"  # 기본 세력: 잿빛 기사단

    # 퀘스트 시스템
    completed_quests: List[str] = field(default_factory=list)  # 완료된 퀘스트 ID 목록
    quest_progress: Dict[str, Any] = field(
        default_factory=dict
    )  # 진행 중인 퀘스트 상태

    def __post_init__(self):
        """초기화 후 검증"""
        self.validate()

    def validate(self) -> None:
        """플레이어 데이터 유효성 검증"""
        if not self.username:
            raise ValueError("사용자명은 필수입니다")

        if not self.is_valid_username(self.username):
            raise ValueError("사용자명은 3-20자의 영문, 숫자, 언더스코어만 허용됩니다")

        if not self.password_hash:
            raise ValueError("비밀번호 해시는 필수입니다")

        if self.email and not self.is_valid_email(self.email):
            raise ValueError("올바른 이메일 형식이 아닙니다")

        if self.preferred_locale not in ["en", "ko"]:
            raise ValueError("지원되지 않는 언어입니다 (en, ko만 지원)")

    @staticmethod
    def is_valid_username(username: str) -> bool:
        """사용자명 유효성 검사"""
        if not username:
            return False

        min_length = 3  # Config.USERNAME_MIN_LENGTH
        max_length = 20  # Config.USERNAME_MAX_LENGTH

        if len(username) < min_length or len(username) > max_length:
            return False

        return re.match(r"^[a-zA-Z0-9_]+$", username) is not None

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """이메일 유효성 검사"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    def get_display_name(self) -> str:
        """게임 내 표시 이름 반환 (display_name이 없으면 username 사용)"""
        return self.display_name if self.display_name else self.username

    def can_change_name(self) -> bool:
        """이름 변경 가능 여부 확인 (하루에 한 번만 가능)"""
        if self.is_admin:
            return True  # 관리자는 제한 없음

        if not self.last_name_change:
            return True  # 한 번도 변경하지 않았으면 가능

        # 마지막 변경 후 24시간이 지났는지 확인
        time_since_change = datetime.now() - self.last_name_change
        return time_since_change.total_seconds() >= 86400  # 24시간 = 86400초

    @staticmethod
    def is_valid_display_name(display_name: str) -> bool:
        """표시 이름 유효성 검사 (한글, 영문, 숫자만 허용, 공백 불가, 3-20자)"""
        if not display_name:
            return False

        # 앞뒤 공백 제거 후 길이 확인
        display_name = display_name.strip()
        if len(display_name) < 3 or len(display_name) > 20:
            return False

        # 공백 불허
        if " " in display_name:
            return False

        # 한글, 영문, 숫자만 허용
        pattern = r"^[가-힣a-zA-Z0-9]+$"
        return re.match(pattern, display_name) is not None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (비밀번호 해시 제외)"""
        data = super().to_dict()
        # 보안상 비밀번호 해시는 일반 직렬화에서 제외
        if "password_hash" in data:
            del data["password_hash"]

        # 능력치 정보 포함
        if hasattr(self, "stats") and self.stats:
            data["stats"] = self.stats.get_all_stats()

        return data

    def to_dict_with_password(self) -> Dict[str, Any]:
        """비밀번호 해시 포함 딕셔너리 변환 (데이터베이스 저장용)"""
        data = super().to_dict()

        # 능력치를 개별 컬럼으로 분리하여 저장
        if hasattr(self, "stats") and self.stats:
            stats_dict = self.stats.to_dict()
            for key, value in stats_dict.items():
                data[f"stat_{key}"] = value
            # 원본 stats 필드 제거
            if "stats" in data:
                del data["stats"]

        return data

    def get_max_carry_weight(self) -> float:
        """최대 소지 가능 무게 계산 (STR 기반)"""
        if hasattr(self, "stats") and self.stats:
            base_strength = self.stats.get_primary_stat(StatType.STR)
            # 기본 공식: STR * 2 + 10 (kg)
            return base_strength * 2.0 + 10.0
        return 30.0  # 기본값

    def get_current_carry_weight(self, inventory_objects: List["GameObject"]) -> float:
        """현재 소지 중인 무게 계산"""
        return sum(obj.weight for obj in inventory_objects)

    def can_carry_more(
        self, inventory_objects: List["GameObject"], additional_weight: float = 0.0
    ) -> bool:
        """추가 무게를 들 수 있는지 확인"""
        current_weight = self.get_current_carry_weight(inventory_objects)
        max_weight = self.get_max_carry_weight()
        return (current_weight + additional_weight) <= max_weight

    def get_carry_capacity_info(
        self, inventory_objects: List["GameObject"]
    ) -> Dict[str, Any]:
        """소지 용량 정보 반환"""
        current_weight = self.get_current_carry_weight(inventory_objects)
        max_weight = self.get_max_carry_weight()
        percentage = (current_weight / max_weight) * 100 if max_weight > 0 else 0

        return {
            "current_weight": current_weight,
            "max_weight": max_weight,
            "percentage": percentage,
            "available_weight": max_weight - current_weight,
            "is_overloaded": current_weight > max_weight,
        }

    def has_gold(self, amount: int) -> bool:
        """충분한 골드를 가지고 있는지 확인"""
        return self.gold >= amount

    def spend_gold(self, amount: int) -> bool:
        """골드 소모 (충분하지 않으면 False 반환)"""
        if self.has_gold(amount):
            self.gold -= amount
            return True
        return False

    def earn_gold(self, amount: int) -> None:
        """골드 획득"""
        self.gold += amount

    def get_gold_display(self) -> str:
        """골드를 표시용 문자열로 반환"""
        return f"{self.gold:,} gold"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Player":
        """딕셔너리에서 모델 생성"""
        # 능력치 관련 필드를 PlayerStats 객체로 변환
        stats_data = {}
        keys_to_remove = []

        for key, value in data.items():
            if key.startswith("stat_"):
                stat_key = key[5:]  # 'stat_' 제거
                stats_data[stat_key] = value
                keys_to_remove.append(key)

        # 능력치 필드들을 원본 데이터에서 제거
        for key in keys_to_remove:
            del data[key]

        # PlayerStats 객체 생성
        if stats_data:
            data["stats"] = PlayerStats.from_dict(stats_data)
        else:
            data["stats"] = PlayerStats()  # 기본값

        # 날짜 필드 처리
        for date_field in ["created_at", "last_login"]:
            if date_field in data and isinstance(data[date_field], str):
                try:
                    data[date_field] = datetime.fromisoformat(
                        data[date_field].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    if date_field == "created_at":
                        data[date_field] = datetime.now()
                    else:
                        data[date_field] = None

        return cls(**data)
