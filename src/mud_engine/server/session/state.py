# -*- coding: utf-8 -*-
"""세션 도메인 상태(Session State) 구성요소.

연결당 게임/도메인 상태(플레이어, 위치, 전투/대화 상태, 스태미나 등)를 담는
순수 상태 컨테이너. 전송/프로토콜/표현 책임은 포함하지 않는다.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ...game.models import Player


@dataclass
class SessionState:
    """클라이언트 연결당 게임 도메인 상태."""

    # 인증/플레이어
    player: Optional[Player] = None
    is_authenticated: bool = False

    # 위치
    current_room_id: Optional[str] = None
    current_room_type: str = "unknown"
    locale: str = "en"
    following_player: Optional[str] = None

    # 전투
    in_combat: bool = False
    original_room_id: Optional[str] = None
    combat_id: Optional[str] = None

    # 대화
    in_dialogue: bool = False
    dialogue_id: Optional[str] = None

    # 스태미나 (메모리 only, 로그인 시 초기화)
    stamina: float = 5.0
    max_stamina: float = 5.0

    # 명령/엔티티 매핑
    last_command: Optional[str] = None
    room_entity_map: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    inventory_entity_map: Dict[int, Dict[str, Any]] = field(default_factory=dict)
