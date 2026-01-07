import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from ...database.repository import BaseModel
from ..stats import PlayerStats


@dataclass
class Session(BaseModel):
    """세션 모델 (메모리에서만 사용, 데이터베이스 저장 안함)"""

    id: str = field(default_factory=lambda: str(uuid4()))
    player_id: str = ""
    character_id: str = ""
    websocket: Any = None  # web.WebSocketResponse (순환 참조 방지)
    current_room_id: str = ""
    locale: str = "en"
    connected_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """초기화 후 검증"""
        self.validate()

    def validate(self) -> None:
        """세션 데이터 유효성 검증"""
        if not self.player_id:
            raise ValueError("플레이어 ID는 필수입니다")

        if not self.character_id:
            raise ValueError("캐릭터 ID는 필수입니다")

        if self.locale not in ["en", "ko"]:
            raise ValueError("지원되지 않는 언어입니다 (en, ko만 지원)")

    def update_activity(self) -> None:
        """마지막 활동 시간 업데이트"""
        self.last_activity = datetime.now()

    def is_active(self, timeout_minutes: int = 30) -> bool:
        """세션이 활성 상태인지 확인"""
        if not self.last_activity:
            return False

        time_diff = datetime.now() - self.last_activity
        return time_diff.total_seconds() < (timeout_minutes * 60)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (WebSocket 제외)"""
        data = super().to_dict()
        # WebSocket 객체는 직렬화에서 제외
        if "websocket" in data:
            del data["websocket"]
        return data
