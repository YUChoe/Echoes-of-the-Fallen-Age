"""
어드민 실시간 액션 단위 테스트

14종 등록, 파라미터 검증, 접속 여부 판정, 방향 출구 규칙을 확인한다.
계약: docs/protocol/admin.md
"""

import pytest

from src.mud_engine.server import serialization as ser
from src.mud_engine.server.admin.actions import AdminActionHandlers
from src.mud_engine.server.admin.manager_bridge import AdminManagerSession
from src.mud_engine.server.admin.world_actions import (
    DIRECTION_OFFSETS,
    ActionError,
    WorldActions,
    optional_str,
)

# 계약이 규정한 14종
CONTRACT_ACTIONS = {
    "goto",
    "kick",
    "spawn_monster",
    "spawn_item",
    "terminate",
    "create_room",
    "update_room",
    "create_exit",
    "validate_world",
    "list_monster_templates",
    "list_item_templates",
    "scheduler",
    "change_display_name",
    "room_info",
}


class _StubPlayer:
    def __init__(self, username: str) -> None:
        self.username = username


class _StubSession:
    def __init__(self, username: str) -> None:
        self.player = _StubPlayer(username)


class _StubSessionManager:
    def __init__(self, usernames: list[str]) -> None:
        self._sessions = [_StubSession(name) for name in usernames]

    def get_authenticated_sessions(self) -> list[_StubSession]:
        return self._sessions


class _StubRoom:
    def __init__(self, room_id: str, x: int, y: int, blocked=None) -> None:
        self.id = room_id
        self.x = x
        self.y = y
        self.blocked_exits = blocked or []
        self.room_type = "unknown"


class _StubWorldManager:
    def __init__(self, rooms: list[_StubRoom]) -> None:
        self._rooms = rooms

    async def get_rooms_in_area(self, x, y, radius) -> list[_StubRoom]:
        return [room for room in self._rooms if room.x == x and room.y == y]

    async def get_room(self, room_id: str):
        return next((room for room in self._rooms if room.id == room_id), None)


class _StubEngine:
    def __init__(self, usernames=(), rooms=()) -> None:
        self.session_manager = _StubSessionManager(list(usernames))
        self.world_manager = _StubWorldManager(list(rooms))


class _StubPrincipal:
    name = "player5426"


class _StubAdminSession:
    session_id = "s-1"
    principal = _StubPrincipal()


# 액션 등록 ------------------------------------------------------------------


def test_all_fourteen_contract_actions_are_registered():
    """계약의 14종이 모두 라우팅된다"""
    handlers = AdminActionHandlers(_StubEngine())

    resolved = {
        action
        for action in CONTRACT_ACTIONS
        if handlers._resolve(action, _StubAdminSession()) is not None
    }

    assert resolved == CONTRACT_ACTIONS


def test_unknown_action_is_not_routed():
    """계약에 없는 액션은 구현으로 이어지지 않는다"""
    handlers = AdminActionHandlers(_StubEngine())

    assert handlers._resolve("drop_database", _StubAdminSession()) is None


# 접속 여부 ------------------------------------------------------------------


def test_offline_target_raises_player_not_online():
    """게임 세션이 없으면 PLAYER_NOT_ONLINE 이다"""
    handlers = AdminActionHandlers(_StubEngine(usernames=["player5426"]))

    with pytest.raises(ActionError) as exc:
        handlers._find_game_session("nobody")

    assert exc.value.reason_code == "PLAYER_NOT_ONLINE"


def test_online_target_is_found():
    """접속 중이면 세션을 돌려준다"""
    handlers = AdminActionHandlers(_StubEngine(usernames=["player5426"]))

    session = handlers._find_game_session("player5426")

    assert session.player.username == "player5426"


# 좌표 해석 ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_room_at_missing_coordinates_raises_not_found():
    """좌표에 방이 없으면 NOT_FOUND 다"""
    world = WorldActions(_StubEngine(rooms=[_StubRoom("r1", 0, 7)]))

    with pytest.raises(ActionError) as exc:
        await world.room_at(9, 9)

    assert exc.value.reason_code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_room_at_returns_room():
    """좌표의 방을 찾는다"""
    world = WorldActions(_StubEngine(rooms=[_StubRoom("r1", 0, 7)]))

    assert (await world.room_at(0, 7)).id == "r1"


# 출구 개방 ------------------------------------------------------------------


def test_direction_offsets_cover_four_directions():
    """방향 이동은 좌표로 결정되며 네 방향뿐이다"""
    assert set(DIRECTION_OFFSETS) == {"north", "south", "east", "west"}
    assert DIRECTION_OFFSETS["north"] == (0, 1)
    assert DIRECTION_OFFSETS["west"] == (-1, 0)


@pytest.mark.asyncio
async def test_create_exit_rejects_unknown_direction():
    """대각선과 상하 방향은 이 세계에 없다"""
    world = WorldActions(_StubEngine(rooms=[_StubRoom("r1", 0, 0)]))

    with pytest.raises(ActionError) as exc:
        await world.create_exit(
            {"from_id": "r1", "to_id": "r2", "direction": "northeast"}
        )

    assert exc.value.reason_code == "INVALID_PARAMS"


@pytest.mark.asyncio
async def test_create_exit_rejects_mismatched_target():
    """인접 좌표의 방과 to_id 가 다르면 거절한다"""
    rooms = [_StubRoom("r1", 0, 0, ["north"]), _StubRoom("r2", 0, 1)]
    world = WorldActions(_StubEngine(rooms=rooms))

    with pytest.raises(ActionError) as exc:
        await world.create_exit(
            {"from_id": "r1", "to_id": "wrong", "direction": "north"}
        )

    assert exc.value.reason_code == "VALIDATION_FAILED"


@pytest.mark.asyncio
async def test_create_exit_is_noop_when_direction_not_blocked():
    """이미 열린 방향은 변경 없이 성공한다"""
    rooms = [_StubRoom("r1", 0, 0, []), _StubRoom("r2", 0, 1)]
    world = WorldActions(_StubEngine(rooms=rooms))

    data = await world.create_exit(
        {"from_id": "r1", "to_id": "r2", "direction": "north"}
    )

    assert data == {"from_id": "r1", "direction": "north", "changed": False}


@pytest.mark.asyncio
async def test_create_exit_rejects_missing_room():
    """출발 방이 없으면 NOT_FOUND 다"""
    world = WorldActions(_StubEngine(rooms=[]))

    with pytest.raises(ActionError) as exc:
        await world.create_exit(
            {"from_id": "gone", "to_id": "r2", "direction": "north"}
        )

    assert exc.value.reason_code == "NOT_FOUND"


# 파라미터 검증 --------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_string_parameter_is_rejected():
    """필수 문자열이 없으면 INVALID_PARAMS 다"""
    world = WorldActions(_StubEngine())

    with pytest.raises(ActionError) as exc:
        await world.terminate({})

    assert exc.value.reason_code == "INVALID_PARAMS"


@pytest.mark.asyncio
async def test_boolean_is_not_accepted_as_integer():
    """bool 은 int 의 하위 타입이라 명시적으로 배제한다"""
    world = WorldActions(_StubEngine())

    with pytest.raises(ActionError) as exc:
        await world.spawn_monster({"template_id": "t", "x": True, "y": 0})

    assert exc.value.reason_code == "INVALID_PARAMS"


def test_optional_string_falls_back_to_default():
    """선택 파라미터는 없거나 빈 값이면 기본값이다"""
    assert optional_str({}, "reason", "기본") == "기본"
    assert optional_str({"reason": ""}, "reason", "기본") == "기본"
    assert optional_str({"reason": 3}, "reason", "기본") == "기본"
    assert optional_str({"reason": "사유"}, "reason", "기본") == "사유"


# 스케줄러 --------------------------------------------------------------------


def test_scheduler_rejects_unknown_operation():
    """list/info/enable/disable 외에는 거절한다"""
    world = WorldActions(_StubEngine())

    with pytest.raises(ActionError) as exc:
        world.scheduler({"operation": "delete"})

    assert exc.value.reason_code == "INVALID_PARAMS"


# 매니저 어댑터 --------------------------------------------------------------


@pytest.mark.asyncio
async def test_bridge_collects_notices_instead_of_sending():
    """AdminManager 의 완성 문장은 소켓으로 나가지 않고 결과에 담긴다"""
    bridge = AdminManagerSession(_StubAdminSession())

    await bridge.send_admin_notice("방이 생성되었습니다", "success")

    assert bridge.notices == [{"severity": "success", "text": "방이 생성되었습니다"}]
    assert bridge.failed is False


@pytest.mark.asyncio
async def test_bridge_reports_failure_on_error_notice():
    """오류 문장이 있으면 실패로 판정할 수 있다"""
    bridge = AdminManagerSession(_StubAdminSession())

    await bridge.send_admin_notice("방 생성 실패", "error")

    assert bridge.failed is True


def test_bridge_has_no_game_player():
    """어드민 주체는 게임 플레이어가 아니다"""
    bridge = AdminManagerSession(_StubAdminSession())

    assert bridge.player is None
    assert bridge.session_id == "s-1"


# 응답 봉투 ------------------------------------------------------------------


def test_action_result_shape():
    """액션 결과 형식"""
    message = ser.admin_action_result(30, "spawn_monster", True, {"monster_id": "m1"})

    assert message["type"] == "admin_action_result"
    assert message["action"] == "spawn_monster"
    assert message["success"] is True
    assert message["data"] == {"monster_id": "m1"}


def test_action_result_defaults_to_empty_data():
    """데이터가 없어도 필드는 존재한다"""
    message = ser.admin_action_result(31, "validate_world", True)

    assert message["data"] == {}
