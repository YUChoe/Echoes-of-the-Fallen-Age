# -*- coding: utf-8 -*-
"""JSON 라인 프로토콜 직렬화 계층

모델을 클라이언트가 소비할 dict 로 변환한다. 언어 선택과 텍스트 조립을 하지 않으며
번역과 표시는 클라이언트가 담당한다.

프로토콜 계약: docs/protocol/
"""

from .admin import (
    admin_get_result,
    admin_list_result,
    admin_login_result,
    admin_mutate_result,
    admin_rejected,
    service_login_result,
)
from .combat import build_combat_state, serialize_combatant
from .dialogue import build_dialogue, ensure_farewell_choice, serialize_choices
from .entity import (
    coerce_properties,
    is_container,
    is_readable,
    is_usable,
    localized_dict,
    serialize_monster,
    serialize_object,
    serialize_player,
    stack_count,
)
from .envelope import (
    MAX_LINE_BYTES,
    PROTOCOL_VERSION,
    action_rejected,
    build,
    build_event,
    encode,
    encode_line,
    error,
    message_payload,
)
from .inventory import (
    build_container_contents,
    build_inventory,
    serialize_equipped_slots,
)
from .player import build_player_state, serialize_stats
from .social import build_chat, build_who_result, serialize_player_summary
from .room import (
    UNKNOWN_ROOM_TYPE,
    build_room_info,
    serialize_nearby_rooms,
    serialize_room,
)

__all__ = [
    "MAX_LINE_BYTES",
    "PROTOCOL_VERSION",
    "UNKNOWN_ROOM_TYPE",
    "action_rejected",
    "admin_get_result",
    "admin_list_result",
    "admin_login_result",
    "admin_mutate_result",
    "admin_rejected",
    "build",
    "build_chat",
    "build_combat_state",
    "build_container_contents",
    "build_dialogue",
    "build_event",
    "build_inventory",
    "build_player_state",
    "build_room_info",
    "build_who_result",
    "coerce_properties",
    "encode",
    "encode_line",
    "ensure_farewell_choice",
    "error",
    "is_container",
    "is_readable",
    "is_usable",
    "localized_dict",
    "message_payload",
    "serialize_choices",
    "serialize_combatant",
    "serialize_equipped_slots",
    "serialize_monster",
    "serialize_nearby_rooms",
    "serialize_object",
    "serialize_player",
    "serialize_player_summary",
    "serialize_room",
    "serialize_stats",
    "service_login_result",
    "stack_count",
]
