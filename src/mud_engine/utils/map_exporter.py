#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""월드 맵 데이터 생성

`world_map_unified.html` 을 만들던 HTML 렌더러를 대체한다. 서버는 쿼리 결과만
내보내고 렌더링은 Godot 어드민 패널이 담당한다.

이 데이터는 좌표, 막힌 출구, 종족별 분포를 노출하므로 플레이어에게 제공하지
않는다. 어드민 채널 전용이다.

프로토콜 계약: docs/protocol/admin.md
"""

import json
import logging
from typing import Any, Optional

from ..database.connection import DatabaseManager

logger = logging.getLogger(__name__)


class MapExporter:
    """어드민 맵 응답에 담을 데이터를 모은다."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    async def build_map_data(
        self, include_descriptions: bool = False
    ) -> dict[str, Any]:
        """맵 전체 데이터를 만든다.

        좌표가 없는 방은 제외한다. 지도에 놓을 자리가 없기 때문이다.

        Args:
            include_descriptions: 방 설명을 담을지. 설명이 응답의 3분의 2를
                차지해 한 라인의 상한(256KB)에 육박하므로 기본은 제외다.
                상세 설명은 `admin_get` 으로 방 하나씩 읽는다

        Returns:
            `bounds` 와 `rooms` 를 담은 딕셔너리
        """
        rooms = await self._fetch_rooms()

        if not rooms:
            return {"bounds": _empty_bounds(), "rooms": []}

        creatures = await self._count_creatures_by_room()
        players = await self._count_players_by_room()
        items = await self._count_items_by_room()
        factions = await self._count_factions_by_room()

        payload = []

        for room in rooms:
            entry = {
                "id": room["id"],
                "x": room["x"],
                "y": room["y"],
                "room_type": room["room_type"],
                "blocked_exits": _parse_blocked_exits(room["blocked_exits"]),
                "creature_count": creatures.get(room["id"], 0),
                "player_count": players.get(room["id"], 0),
                "item_count": items.get(room["id"], 0),
                "factions": factions.get(room["id"], {}),
            }

            if include_descriptions:
                entry["description_ko"] = room["description_ko"]
                entry["description_en"] = room["description_en"]

            payload.append(entry)

        return {"bounds": _bounds(rooms), "rooms": payload}

    # 조회 --------------------------------------------------------------------

    async def _fetch_rooms(self) -> list[dict[str, Any]]:
        """좌표가 있는 방을 모두 가져온다."""
        return await self.db_manager.fetch_all(
            """
            SELECT id, description_ko, description_en, x, y, blocked_exits, room_type
            FROM rooms
            WHERE x IS NOT NULL AND y IS NOT NULL
            ORDER BY x, y
            """
        )

    async def _count_creatures_by_room(self) -> dict[str, int]:
        """방별 생존 몬스터 수. 몬스터는 좌표로 방과 이어진다."""
        rows = await self.db_manager.fetch_all(
            """
            SELECT r.id AS room_id, COUNT(*) AS total
            FROM rooms r
            INNER JOIN monsters m ON r.x = m.x AND r.y = m.y
            WHERE m.is_alive = 1
            GROUP BY r.id
            """
        )
        return {row["room_id"]: int(row["total"]) for row in rows}

    async def _count_players_by_room(self) -> dict[str, int]:
        """방별 플레이어 수.

        `players.last_room_x/y` 기준이므로 접속 중이 아닌 계정도 포함된다.
        실시간 접속자는 `admin_stats` 의 `online_players` 를 본다.
        """
        rows = await self.db_manager.fetch_all(
            """
            SELECT r.id AS room_id, COUNT(*) AS total
            FROM players p
            INNER JOIN rooms r ON p.last_room_x = r.x AND p.last_room_y = r.y
            GROUP BY r.id
            """
        )
        return {row["room_id"]: int(row["total"]) for row in rows}

    async def _count_items_by_room(self) -> dict[str, int]:
        """방에 놓인 오브젝트 수.

        `location_type` 이 `room` 과 `ROOM` 으로 섞여 있어 대소문자를 무시한다.
        """
        rows = await self.db_manager.fetch_all(
            """
            SELECT location_id AS room_id, COUNT(*) AS total
            FROM game_objects
            WHERE LOWER(location_type) = 'room' AND location_id IS NOT NULL
            GROUP BY location_id
            """
        )
        return {row["room_id"]: int(row["total"]) for row in rows}

    async def _count_factions_by_room(self) -> dict[str, dict[str, int]]:
        """방별 종족 분포. 생존 몬스터만 센다."""
        rows = await self.db_manager.fetch_all(
            """
            SELECT r.id AS room_id, m.faction_id, COUNT(*) AS total
            FROM rooms r
            INNER JOIN monsters m ON r.x = m.x AND r.y = m.y
            WHERE m.is_alive = 1
            GROUP BY r.id, m.faction_id
            """
        )

        by_room: dict[str, dict[str, int]] = {}

        for row in rows:
            room_id = row["room_id"]
            faction = row["faction_id"] or "unknown"
            by_room.setdefault(room_id, {})[faction] = int(row["total"])

        return by_room


def _bounds(rooms: list[dict[str, Any]]) -> dict[str, int]:
    """방 좌표의 최소·최대 범위"""
    xs = [room["x"] for room in rooms]
    ys = [room["y"] for room in rooms]

    return {
        "min_x": min(xs),
        "max_x": max(xs),
        "min_y": min(ys),
        "max_y": max(ys),
    }


def _empty_bounds() -> dict[str, int]:
    """방이 없을 때의 범위"""
    return {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0}


def _parse_blocked_exits(raw: Optional[str]) -> list[str]:
    """`blocked_exits` 는 TEXT 컬럼에 담긴 JSON 배열이다."""
    if not raw:
        return []

    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        logger.warning(f"blocked_exits 파싱 실패: {raw!r}")
        return []

    return [item for item in parsed if isinstance(item, str)] if isinstance(parsed, list) else []
