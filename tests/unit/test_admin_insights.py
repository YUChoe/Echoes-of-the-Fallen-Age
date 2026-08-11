"""
어드민 통계와 맵 데이터 단위 테스트

맵 데이터가 계약 형식을 따르고 HTML 을 만들지 않는지, 통계 응답이 테이블별
행 수를 담는지 확인한다.
계약: docs/protocol/admin.md
"""

import inspect

import pytest

from src.mud_engine.server import serialization as ser
from src.mud_engine.server.admin.insights import COUNT_TABLES
from src.mud_engine.utils import map_exporter as map_module
from src.mud_engine.utils.map_exporter import (
    MapExporter,
    _bounds,
    _empty_bounds,
    _parse_blocked_exits,
)


class _StubDatabaseManager:
    """쿼리 문자열로 응답을 골라주는 최소 대역"""

    def __init__(self, rooms, creatures=(), players=(), items=(), factions=()) -> None:
        self._rooms = list(rooms)
        self._creatures = list(creatures)
        self._players = list(players)
        self._items = list(items)
        self._factions = list(factions)

    async def fetch_all(self, query: str, parameters: tuple = ()) -> list[dict]:
        # 집계 쿼리도 rooms 를 조인하므로 구분되는 컬럼으로 판정한다
        if "blocked_exits" in query:
            return self._rooms
        if "m.faction_id" in query:
            return self._factions
        if "INNER JOIN monsters" in query:
            return self._creatures
        if "FROM players" in query:
            return self._players
        if "FROM game_objects" in query:
            return self._items
        return []


def _room(room_id: str, x: int, y: int, blocked: str = "[]", room_type="unknown"):
    return {
        "id": room_id,
        "description_ko": "광장",
        "description_en": "Plaza",
        "x": x,
        "y": y,
        "blocked_exits": blocked,
        "room_type": room_type,
    }


# HTML 제거 ------------------------------------------------------------------


def test_map_exporter_no_longer_renders_html():
    """HTML 생성 경로가 남아 있지 않다"""
    names = {name for name, _ in inspect.getmembers(MapExporter)}

    assert "export_to_file" not in names
    assert "generate_html_with_factions" not in names
    assert "get_faction_colors" not in names


def test_map_module_has_no_html_literals():
    """모듈 소스에 HTML 문서 조각이 없다"""
    source = inspect.getsource(map_module)

    assert "<html" not in source.lower()
    assert "<!doctype" not in source.lower()


# 맵 데이터 ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_map_data_follows_contract_fields():
    """계약이 규정한 방 필드를 모두 담는다"""
    db = _StubDatabaseManager(
        rooms=[_room("r1", 0, 7, '["west"]', "gate")],
        creatures=[{"room_id": "r1", "total": 3}],
        players=[{"room_id": "r1", "total": 1}],
        items=[{"room_id": "r1", "total": 4}],
        factions=[
            {"room_id": "r1", "faction_id": "ash_knights", "total": 2},
            {"room_id": "r1", "faction_id": None, "total": 1},
        ],
    )

    data = await MapExporter(db).build_map_data()

    assert data["bounds"] == {"min_x": 0, "max_x": 0, "min_y": 7, "max_y": 7}

    room = data["rooms"][0]
    assert room["id"] == "r1"
    assert room["room_type"] == "gate"
    assert room["blocked_exits"] == ["west"]
    assert room["creature_count"] == 3
    assert room["player_count"] == 1
    assert room["item_count"] == 4
    assert room["factions"] == {"ash_knights": 2, "unknown": 1}


@pytest.mark.asyncio
async def test_descriptions_are_excluded_by_default():
    """설명이 응답의 3분의 2를 차지해 기본으로 담지 않는다"""
    db = _StubDatabaseManager(rooms=[_room("r1", 0, 0)])

    room = (await MapExporter(db).build_map_data())["rooms"][0]

    assert "description_ko" not in room
    assert "description_en" not in room


@pytest.mark.asyncio
async def test_descriptions_are_included_on_request():
    """요청하면 설명을 담는다"""
    db = _StubDatabaseManager(rooms=[_room("r1", 0, 0)])

    room = (await MapExporter(db).build_map_data(True))["rooms"][0]

    assert room["description_ko"] == "광장"
    assert room["description_en"] == "Plaza"


@pytest.mark.asyncio
async def test_rooms_without_counts_default_to_zero():
    """집계에 없는 방은 0으로 채운다"""
    db = _StubDatabaseManager(rooms=[_room("r1", 1, 1)])

    room = (await MapExporter(db).build_map_data())["rooms"][0]

    assert room["creature_count"] == 0
    assert room["player_count"] == 0
    assert room["item_count"] == 0
    assert room["factions"] == {}


@pytest.mark.asyncio
async def test_empty_world_yields_empty_bounds():
    """방이 없으면 범위를 0으로 돌려주고 집계를 조회하지 않는다"""
    data = await MapExporter(_StubDatabaseManager(rooms=[])).build_map_data()

    assert data == {"bounds": _empty_bounds(), "rooms": []}


def test_bounds_spans_negative_coordinates():
    """좌표는 음수를 포함한다"""
    rooms = [_room("a", -25, -11), _room("b", 12, 14)]

    assert _bounds(rooms) == {"min_x": -25, "max_x": 12, "min_y": -11, "max_y": 14}


# blocked_exits 파싱 ---------------------------------------------------------


def test_blocked_exits_parses_json_array():
    """TEXT 컬럼에 담긴 JSON 배열을 리스트로 만든다"""
    assert _parse_blocked_exits('["north", "west"]') == ["north", "west"]


def test_blocked_exits_handles_empty_and_null():
    """빈 값과 NULL 은 빈 리스트다"""
    assert _parse_blocked_exits("") == []
    assert _parse_blocked_exits(None) == []
    assert _parse_blocked_exits("[]") == []


def test_blocked_exits_survives_broken_json():
    """깨진 값에도 맵 생성이 멈추지 않는다"""
    assert _parse_blocked_exits("not json") == []
    assert _parse_blocked_exits('{"north": true}') == []


def test_blocked_exits_drops_non_strings():
    """문자열이 아닌 항목은 버린다"""
    assert _parse_blocked_exits('["north", 3, null]') == ["north"]


# 통계 -----------------------------------------------------------------------

def test_count_tables_cover_contract_counts():
    """계약의 counts 항목에 해당하는 테이블을 센다"""
    assert set(COUNT_TABLES) == {
        "rooms",
        "monsters",
        "players",
        "objects",
        "factions",
    }
    assert COUNT_TABLES["objects"] == "game_objects"


# 응답 봉투 ------------------------------------------------------------------


def test_stats_result_passes_manager_dict_through():
    """매니저 반환값을 가공하지 않고 그대로 싣는다"""
    message = ser.admin_stats_result(20, {"counts": {"rooms": 520}, "engine": {}})

    assert message["type"] == "admin_stats_result"
    assert message["seq"] == 20
    assert message["counts"] == {"rooms": 520}
    assert message["engine"] == {}


def test_map_result_shape():
    """맵 응답 형식"""
    bounds = {"min_x": 0, "max_x": 1, "min_y": 0, "max_y": 1}
    message = ser.admin_map_result(21, bounds, [{"id": "r1"}])

    assert message["type"] == "admin_map_result"
    assert message["bounds"] == bounds
    assert message["rooms"] == [{"id": "r1"}]
