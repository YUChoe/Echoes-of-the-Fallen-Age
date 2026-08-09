# -*- coding: utf-8 -*-
"""JSON 라인 프로토콜 직렬화 계층

모델을 클라이언트가 소비할 dict 로 변환한다. 언어 선택과 텍스트 조립을 하지 않으며
번역과 표시는 클라이언트가 담당한다.

프로토콜 계약: docs/protocol/
"""

from .entity import (
    coerce_properties,
    is_container,
    is_readable,
    is_usable,
    localized_dict,
    serialize_monster,
    serialize_object,
    serialize_player,
)
from .envelope import (
    MAX_LINE_BYTES,
    action_rejected,
    build,
    encode,
    encode_line,
    error,
    message_payload,
)

__all__ = [
    "MAX_LINE_BYTES",
    "action_rejected",
    "build",
    "coerce_properties",
    "encode",
    "encode_line",
    "error",
    "is_container",
    "is_readable",
    "is_usable",
    "localized_dict",
    "message_payload",
    "serialize_monster",
    "serialize_object",
    "serialize_player",
]
