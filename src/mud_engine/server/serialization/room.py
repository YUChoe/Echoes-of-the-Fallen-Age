# -*- coding: utf-8 -*-
"""방 정보 페이로드 직렬화

서버는 텍스트를 조립하지 않는다. 좌표와 지형만 내보내고 미니맵 렌더링은
클라이언트가 담당한다.

프로토콜 계약: docs/protocol/server-to-client.md
"""

from typing import Any, Iterable, Optional

from ...game.models.room import Room

# 지형을 알 수 없을 때의 기본값. 클라이언트도 같은 값으로 폴백한다.
UNKNOWN_ROOM_TYPE = "unknown"


def serialize_room(
    room: Room,
    exits: Iterable[str],
    has_passage: bool = False,
) -> dict[str, Any]:
    """방 자체의 정보를 변환한다.

    `rooms` 테이블에 방 이름 컬럼이 없으므로 이름을 제공하지 않는다.
    클라이언트는 좌표와 지형으로 위치를 표시한다.

    Args:
        room: 대상 방
        exits: 이동 가능한 방향 목록. 좌표 기반으로 산출된 값을 호출부가 전달한다
        has_passage: 이 좌표에 room_connections 항목이 있는지.
            호출부가 조회해 전달한다. RoomManager 로의 조회 이전은 차후 작업이다
    """
    return {
        "id": str(room.id),
        "x": room.x,
        "y": room.y,
        "room_type": room.room_type or UNKNOWN_ROOM_TYPE,
        "description": _description_dict(room),
        "exits": list(exits),
        "blocked_exits": list(room.blocked_exits or []),
        "has_passage": bool(has_passage),
    }


def serialize_nearby_rooms(rooms: Iterable[Room]) -> list[dict[str, Any]]:
    """미니맵용 주변 방 목록을 변환한다.

    좌표와 지형만 담는다. 설명과 엔티티는 포함하지 않는다.
    좌표가 없는 방은 렌더링할 수 없으므로 제외한다.
    """
    payload: list[dict[str, Any]] = []

    for room in rooms:
        if room.x is None or room.y is None:
            continue
        payload.append(
            {
                "x": room.x,
                "y": room.y,
                "room_type": room.room_type or UNKNOWN_ROOM_TYPE,
            }
        )

    return payload


def build_room_info(
    room: Room,
    exits: Iterable[str],
    entities: list[dict[str, Any]],
    nearby_rooms: Iterable[Room],
    time_of_day: str,
    has_passage: bool = False,
    seq: Optional[int] = None,
) -> dict[str, Any]:
    """room_info 메시지를 만든다.

    Args:
        room: 현재 방
        exits: 이동 가능한 방향 목록
        entities: 직렬화된 엔티티 목록. entity 모듈이 만든 결과를 받는다
        nearby_rooms: 반경 이내의 방 목록
        time_of_day: `day` 또는 `night`
        has_passage: 통로 존재 여부
        seq: 클라이언트 요청에 대한 응답이면 그 번호
    """
    from .envelope import build

    return build(
        "room_info",
        seq=seq,
        room=serialize_room(room, exits, has_passage),
        time_of_day=time_of_day,
        entities=entities,
        nearby_rooms=serialize_nearby_rooms(nearby_rooms),
    )


def _description_dict(room: Room) -> dict[str, str]:
    """방 설명을 언어별 dict 로 정규화한다."""
    from .entity import localized_dict

    return localized_dict(room.description)
