"""
어드민 삭제의 참조 무결성과 게임 상태 재동기화 단위 테스트

참조 규칙은 문서가 아니라 실제 DB 에서 확인한 관계다. 선언된 외래키는 셋뿐이고
monsters.faction_id 와 game_objects.location_id 는 FK 없이 운영된다.
계약: docs/protocol/admin.md
"""

import pytest

from src.mud_engine.server import serialization as ser
from src.mud_engine.server.admin.references import RULES, ReferenceChecker
from src.mud_engine.server.admin.refresh import ROOM_AFFECTING, GameStateRefresher
from src.mud_engine.server.admin.resources import RESOURCES


class _StubRoom:
    def __init__(self, room_id: str, x: int, y: int) -> None:
        self.id = room_id
        self.x = x
        self.y = y


class _StubWorldManager:
    def __init__(self, rooms: list[_StubRoom]) -> None:
        self._rooms = rooms

    async def get_rooms_in_area(self, x: int, y: int, radius: int) -> list[_StubRoom]:
        return [room for room in self._rooms if room.x == x and room.y == y]


class _StubSession:
    def __init__(self, room_id: str) -> None:
        self.current_room_id = room_id


class _StubSessionManager:
    def __init__(self, sessions: list[_StubSession]) -> None:
        self._sessions = sessions

    def get_authenticated_sessions(self) -> list[_StubSession]:
        return self._sessions


class _StubMovementManager:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_room_info_to_player(self, session, room_id: str) -> None:
        self.sent.append((session.current_room_id, room_id))


class _StubGameEngine:
    def __init__(self, rooms: list[_StubRoom], sessions: list[_StubSession]) -> None:
        self.world_manager = _StubWorldManager(rooms)
        self.session_manager = _StubSessionManager(sessions)
        self.movement_manager = _StubMovementManager()


# 참조 규칙 정의 --------------------------------------------------------------


def test_factions_is_referenced_by_four_places():
    """players, monsters, faction_relations 양쪽이 종족을 가리킨다"""
    referrers = [(rule.resource, rule.columns) for rule in RULES["factions"]]

    assert ("players", ("faction_id",)) in referrers
    assert ("monsters", ("faction_id",)) in referrers
    assert ("faction_relations", ("faction_a_id",)) in referrers
    assert ("faction_relations", ("faction_b_id",)) in referrers


def test_monsters_faction_reference_has_no_declared_foreign_key():
    """FK 가 없어 SQLite 가 막지 못하므로 규칙으로 검사해야 한다"""
    rule = next(r for r in RULES["factions"] if r.resource == "monsters")

    assert rule.source_columns == ("id",)
    assert rule.unique_source is False


def test_room_coordinate_rules_require_unique_source():
    """좌표가 같은 방이 있으면 하나를 지워도 참조가 끊기지 않는다"""
    coordinate_rules = [
        rule for rule in RULES["rooms"] if rule.source_columns == ("x", "y")
    ]

    assert len(coordinate_rules) == 3
    assert all(rule.unique_source for rule in coordinate_rules)


def test_room_object_rule_matches_location_type():
    """location_id 는 location_type 에 따라 가리키는 대상이 달라진다"""
    rule = next(r for r in RULES["rooms"] if r.resource == "objects")

    assert rule.type_column == "location_type"
    assert rule.type_value == "room"
    # 실제 데이터에 room 과 ROOM 이 섞여 있어 비교는 대소문자를 무시한다
    assert rule.type_value == rule.type_value.lower()


def test_inventory_rule_covers_players_and_monsters():
    """소지품은 플레이어와 몬스터 양쪽이 소유한다"""
    for owner in ("players", "monsters"):
        rule = next(r for r in RULES[owner] if r.resource == "objects")
        assert rule.type_value == "inventory"


def test_resources_without_referrers_have_no_rules():
    """아무도 가리키지 않는 리소스는 규칙이 없다"""
    for name in ("room_connections", "item_prices", "faction_relations"):
        assert name not in RULES


def test_every_rule_points_at_a_known_resource():
    """규칙의 참조 대상이 모두 정의된 리소스여야 한다"""
    for target, rules in RULES.items():
        assert target in RESOURCES
        for rule in rules:
            assert rule.resource in RESOURCES


# 참조 검사 동작 --------------------------------------------------------------


@pytest.mark.asyncio
async def test_rule_is_skipped_when_source_value_is_missing():
    """참조 값이 없는 행은 검사 대상이 아니다"""
    checker = ReferenceChecker(None)

    found = await checker.find_references(RESOURCES["rooms"], {"id": None})

    assert found == []


@pytest.mark.asyncio
async def test_resource_without_rules_returns_no_references():
    """규칙이 없으면 DB 를 건드리지 않고 빈 결과를 준다"""
    checker = ReferenceChecker(None)

    found = await checker.find_references(
        RESOURCES["item_prices"], {"template_id": "silver_coin"}
    )

    assert found == []


# 재동기화 --------------------------------------------------------------------


def test_only_three_resources_affect_room_display():
    """방 화면을 바꾸는 리소스만 재전송 대상이다"""
    assert ROOM_AFFECTING == {"rooms", "monsters", "objects"}


@pytest.mark.asyncio
async def test_room_change_resends_to_players_in_that_room():
    """방을 바꾸면 그 방의 플레이어에게 방 정보를 다시 보낸다"""
    engine = _StubGameEngine([], [_StubSession("r1"), _StubSession("r2")])
    refresher = GameStateRefresher(engine)

    sent = await refresher.after_mutation("rooms", {"id": "r1"})

    assert sent == 1
    assert engine.movement_manager.sent == [("r1", "r1")]


@pytest.mark.asyncio
async def test_monster_change_resolves_room_by_coordinates():
    """몬스터는 좌표로만 위치를 가지므로 좌표에서 방을 찾는다"""
    rooms = [_StubRoom("r1", 0, 7), _StubRoom("r2", 0, 7)]
    engine = _StubGameEngine(rooms, [_StubSession("r2")])
    refresher = GameStateRefresher(engine)

    sent = await refresher.after_mutation("monsters", {"x": 0, "y": 7})

    assert sent == 1


@pytest.mark.asyncio
async def test_object_outside_a_room_triggers_no_resend():
    """소지품 변경은 방 화면을 바꾸지 않는다"""
    engine = _StubGameEngine([], [_StubSession("r1")])
    refresher = GameStateRefresher(engine)

    sent = await refresher.after_mutation(
        "objects", {"location_type": "inventory", "location_id": "p1"}
    )

    assert sent == 0


@pytest.mark.asyncio
async def test_object_location_type_comparison_ignores_case():
    """실제 데이터에 room 과 ROOM 이 섞여 있다"""
    engine = _StubGameEngine([], [_StubSession("r1")])
    refresher = GameStateRefresher(engine)

    sent = await refresher.after_mutation(
        "objects", {"location_type": "ROOM", "location_id": "r1"}
    )

    assert sent == 1


@pytest.mark.asyncio
async def test_unrelated_resource_triggers_no_resend():
    """가격표나 종족 변경은 방 정보를 다시 보내지 않는다"""
    engine = _StubGameEngine([], [_StubSession("r1")])
    refresher = GameStateRefresher(engine)

    assert await refresher.after_mutation("item_prices", {"template_id": "x"}) == 0
    assert await refresher.after_mutation("factions", {"id": "wild"}) == 0


@pytest.mark.asyncio
async def test_missing_game_engine_is_tolerated():
    """게임 엔진이 배선되지 않은 배포에서도 변경이 실패하지 않는다"""
    refresher = GameStateRefresher(None)

    assert await refresher.after_mutation("rooms", {"id": "r1"}) == 0


# 거절 메시지 ----------------------------------------------------------------


def test_referenced_rejection_carries_reference_list():
    """REFERENCED 거절은 무엇이 막았는지 함께 알린다"""
    references = [
        {"resource": "players", "columns": ["faction_id"], "count": 9, "samples": []}
    ]

    message = ser.admin_rejected(
        13, "admin_delete", "REFERENCED", "factions is referenced by 9 row(s)", references
    )

    assert message["reason_code"] == "REFERENCED"
    assert message["references"] == references


def test_other_rejections_omit_reference_list():
    """참조와 무관한 거절에는 필드를 담지 않는다"""
    message = ser.admin_rejected(14, "admin_get", "NOT_FOUND", "rooms not found")

    assert "references" not in message
