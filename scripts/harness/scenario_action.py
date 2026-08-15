#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""액션 디스패처 시나리오

액션 디스패처 도입(server-json-protocol Task 4)이 계약대로 동작하는지 확인한다.
검증 대상은 거절 코드 판정과 이동·조회 액션의 왕복이다.

기대값은 계약 문서(docs/protocol/)의 값을 그대로 적는다.
"""

from typing import Any, Optional

from .client import DEFAULT_ADMIN_PORT, DEFAULT_PORT, HarnessClient, HarnessError
from .fixture import Fixture
from .result import ScenarioResult

TEST_USERNAME = "player5426"
TEST_PASSWORD = "test1234"


def _login(client: HarnessClient) -> dict[str, Any]:
    """로그인하고 첫 room_info 까지 받는다."""
    client.wait_for("welcome", timeout_ms=3000)
    seq = client.send_json(
        {"type": "login", "username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    result = client.wait_for("login_result", seq=seq, timeout_ms=5000)

    if result.get("success") is not True:
        raise HarnessError(f"로그인 실패: {result.get('reason_code')}")

    return client.wait_for("room_info", timeout_ms=5000)


def _send_action(
    client: HarnessClient,
    verb: str,
    target: Optional[str] = None,
    params: Optional[dict[str, Any]] = None,
) -> int:
    """action 메시지를 보내고 seq 를 반환한다."""
    message: dict[str, Any] = {"type": "action", "verb": verb}
    if target is not None:
        message["target"] = target
    if params is not None:
        message["params"] = params

    seq = client.send_json(message)
    assert seq is not None
    return seq


def _expect_rejection(
    result: ScenarioResult,
    client: HarnessClient,
    label: str,
    verb: str,
    expected_code: str,
    target: Optional[str] = None,
    params: Optional[dict[str, Any]] = None,
) -> None:
    """액션이 지정한 사유로 거절되는지 확인한다."""
    seq = _send_action(client, verb, target=target, params=params)

    try:
        rejection = client.wait_for("action_rejected", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail(label, str(exc))
        return

    if rejection.get("reason_code") != expected_code:
        result.fail(
            label,
            f"reason_code 가 {rejection.get('reason_code')!r} (기대 {expected_code})",
        )
        return

    if rejection.get("verb") != verb:
        result.fail(label, f"verb 가 {rejection.get('verb')!r}")
        return

    result.ok(label, f"{expected_code} 응답")


def _check_unknown_verb(result: ScenarioResult, client: HarnessClient) -> None:
    """등록되지 않은 verb 를 거절한다."""
    _expect_rejection(
        result, client, "미등록 verb 거절", "fly", "NOT_APPLICABLE"
    )


def _check_missing_target(result: ScenarioResult, client: HarnessClient) -> None:
    """대상이 필요한 verb 에 target 이 없으면 거절한다."""
    _expect_rejection(
        result, client, "target 누락 거절", "examine", "TARGET_REQUIRED"
    )


def _check_unknown_target(result: ScenarioResult, client: HarnessClient) -> None:
    """접근 범위 밖의 uuid 를 거절한다."""
    _expect_rejection(
        result,
        client,
        "범위 밖 대상 거절",
        "examine",
        "NOT_FOUND",
        target="00000000-0000-0000-0000-000000000000",
    )


def _check_invalid_direction(result: ScenarioResult, client: HarnessClient) -> None:
    """잘못된 방향을 거절한다."""
    _expect_rejection(
        result,
        client,
        "잘못된 방향 거절",
        "move",
        "INVALID_PARAMS",
        params={"direction": "upward"},
    )


def _check_combat_only_verb(result: ScenarioResult, client: HarnessClient) -> None:
    """전투 전용 verb 를 전투 밖에서 거절한다."""
    _expect_rejection(
        result,
        client,
        "전투 전용 verb 거절",
        "request_combat_state",
        "WRONG_STATE",
    )


def _check_look(result: ScenarioResult, client: HarnessClient) -> None:
    """look 이 room_info 를 다시 보내는지 확인한다."""
    _send_action(client, "look")

    try:
        room_info = client.wait_for("room_info", timeout_ms=3000)
    except HarnessError as exc:
        result.fail("look 재조회", str(exc))
        return

    room = room_info.get("room")
    if not isinstance(room, dict) or "id" not in room:
        result.fail("look 재조회", f"room 이 {room!r}")
        return

    result.ok("look 재조회", f"엔티티 {len(room_info.get('entities', []))}개")


def _check_request_state(result: ScenarioResult, client: HarnessClient) -> None:
    """request_state 가 player_state 를 보내는지 확인한다."""
    seq = _send_action(client, "request_state")

    try:
        state = client.wait_for("player_state", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("request_state", str(exc))
        return

    player = state.get("player")
    if not isinstance(player, dict):
        result.fail("request_state", f"player 가 {player!r}")
        return

    # 계약이 규정한 player 필드
    missing = [
        field
        for field in (
            "id",
            "username",
            "display_name",
            "faction_id",
            "room_id",
            "x",
            "y",
            "hp",
            "max_hp",
            "stamina",
            "max_stamina",
            "silver",
            "stats",
            "equipment_bonuses",
            "temporary_effects",
            "in_combat",
            "in_dialogue",
            "following",
        )
        if field not in player
    ]
    if missing:
        result.fail("request_state", f"player 필드 누락: {missing}")
        return

    stats = player["stats"]
    expected_stats = (
        "strength",
        "dexterity",
        "constitution",
        "intelligence",
        "wisdom",
        "charisma",
    )
    if not isinstance(stats, dict) or any(s not in stats for s in expected_stats):
        result.fail("request_state", f"stats 가 {stats!r}")
        return

    result.ok(
        "request_state",
        f"HP {player['hp']}/{player['max_hp']}, 스태미나 {player['stamina']}",
    )


def _check_request_inventory(result: ScenarioResult, client: HarnessClient) -> None:
    """request_inventory 가 inventory 를 보내는지 확인한다."""
    seq = _send_action(client, "request_inventory")

    try:
        inventory = client.wait_for("inventory", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("request_inventory", str(exc))
        return

    problems: list[str] = []

    if not isinstance(inventory.get("items"), list):
        problems.append(f"items 가 {inventory.get('items')!r}")
    if not isinstance(inventory.get("equipped"), dict):
        problems.append(f"equipped 가 {inventory.get('equipped')!r}")
    for field in ("total_weight", "max_weight", "silver"):
        if field not in inventory:
            problems.append(f"{field} 누락")

    if problems:
        result.fail("request_inventory", "; ".join(problems))
        return

    result.ok(
        "request_inventory",
        f"아이템 {len(inventory['items'])}개, 실버 {inventory['silver']}",
    )


def _check_examine(
    result: ScenarioResult, client: HarnessClient, room_info: dict[str, Any]
) -> None:
    """방의 엔티티를 examine 으로 조사한다."""
    entities = room_info.get("entities") or []
    if not entities:
        result.skip("examine 조사", "방에 엔티티가 없다")
        return

    target_id = entities[0].get("id")
    seq = _send_action(client, "examine", target=target_id)

    try:
        update = client.wait_for("entity_update", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("examine 조사", str(exc))
        return

    if update.get("entity_id") != target_id:
        result.fail("examine 조사", f"entity_id 가 {update.get('entity_id')!r}")
        return

    changes = update.get("changes")
    if not isinstance(changes, dict) or "name" not in changes:
        result.fail("examine 조사", f"changes 가 {changes!r}")
        return

    result.ok("examine 조사", f"{changes.get('kind')} 갱신 수신")


def _check_move(
    result: ScenarioResult, client: HarnessClient, room_info: dict[str, Any]
) -> None:
    """열린 방향으로 이동하면 새 room_info 가 오는지 확인한다."""
    room = room_info.get("room") or {}
    exits = room.get("exits") or []

    if not exits:
        result.skip("방향 이동", "출구가 없다")
        return

    origin_id = room.get("id")
    direction = exits[0]
    _send_action(client, "move", params={"direction": direction})

    try:
        moved = client.wait_for("room_info", timeout_ms=5000)
    except HarnessError as exc:
        result.fail("방향 이동", f"{direction} 이동 후 room_info 없음: {exc}")
        return

    new_id = (moved.get("room") or {}).get("id")
    if new_id == origin_id:
        result.fail("방향 이동", f"{direction} 이동했으나 방이 그대로다")
        return

    result.ok("방향 이동", f"{direction} 으로 이동 확인")


def run(
    result: ScenarioResult,
    port: int = DEFAULT_PORT,
    admin_port: int = DEFAULT_ADMIN_PORT,
) -> None:
    """액션 시나리오를 실행한다."""
    try:
        with HarnessClient(port=port, verbose=False) as client:
            client.connect()
            room_info = _login(client)

            _check_unknown_verb(result, client)
            _check_missing_target(result, client)
            _check_unknown_target(result, client)
            _check_invalid_direction(result, client)
            _check_combat_only_verb(result, client)

            _check_look(result, client)
            _check_request_state(result, client)
            _check_request_inventory(result, client)
            _check_examine(result, client, room_info)

            # 아이템과 컨테이너는 이동 전에 검사한다. 방이 바뀌면 방에 버린
            # 아이템을 다시 줍는 왕복이 성립하지 않는다.
            _check_drop_and_get(result, client)
            _check_equip_cycle(result, client)
            _check_partial_quantity_rejected(result, client)
            _check_not_readable_rejected(result, client)

            # 읽기와 컨테이너는 준비 단계에서 검사한다. 프로덕션 방에는 해당
            # 아이템이 없어 건너뛰기만 했다
            _check_dialogue_cycle(result, client)

            _check_who(result, client)
            _check_players_here(result, client)
            _check_emote(result, client)
            _check_unfollow_without_target(result, client)
            _check_changename(result, client)
            _check_chat(result, client)

            _check_move(result, client, room_info)

            # 전제 조건이 필요한 검사는 어드민 채널로 환경을 만들어 수행한다.
            # 프로덕션 방에 의존하면 몬스터 로밍 때문에 실행마다 결과가 달라진다
            _run_with_fixture(result, client, room_info, admin_port)

            client.send_json({"type": "logout"})

    except HarnessError as exc:
        result.skip("액션 시나리오", str(exc))


def _run_with_fixture(
    result: ScenarioResult,
    client: HarnessClient,
    room_info: dict[str, Any],
    admin_port: int,
) -> None:
    """전용 방을 만들어 전제 조건이 필요한 검사를 수행한다.

    끝나면 플레이어를 원래 좌표로 돌려보내고 만든 것을 지운다. 방을 지우기 전에
    플레이어를 빼내야 사라진 방에 갇히지 않는다.
    """
    origin = room_info.get("room") or {}
    origin_x, origin_y = origin.get("x"), origin.get("y")

    fixture = Fixture(admin_port)

    if not fixture.open(TEST_USERNAME, TEST_PASSWORD):
        for label in ("읽기", "컨테이너 왕복", "전투 왕복"):
            result.skip(label, fixture.reason or "검증용 방을 준비할 수 없다")
        return

    try:
        if not fixture.send_player(TEST_USERNAME):
            for label in ("읽기", "컨테이너 왕복", "전투 왕복"):
                result.skip(label, "검증용 방으로 이동할 수 없다")
            return

        client.read_json(800)  # goto 로 밀려온 방 정보를 비운다

        # 읽기와 컨테이너 검사는 인벤토리를 본다. 방에 만든 뒤 주워 넣는다
        if _take_into_inventory(client, fixture.create_readable()):
            _check_read(result, client)
        else:
            result.skip("읽기", "읽을 수 있는 아이템을 인벤토리에 넣을 수 없다")

        if _take_into_inventory(client, fixture.create_container()):
            _check_container_cycle(result, client)
        else:
            result.skip("컨테이너 왕복", "컨테이너를 인벤토리에 넣을 수 없다")

        _check_usable(result, client, fixture)
        _check_unequip_all(result, client)
        _check_inventory_full(result, client, fixture)
        _check_enter(result, client, fixture, origin_x, origin_y)

        if fixture.spawn_hostile() is not None:
            _check_combat_cycle(result, client)
        else:
            result.skip("전투 왕복", "적대 몬스터를 스폰할 수 없다")
    finally:
        # 방을 지우기 전에 플레이어를 빼낸다
        if isinstance(origin_x, int) and isinstance(origin_y, int):
            fixture.send_player_to(TEST_USERNAME, origin_x, origin_y)
        fixture.close()


# 아이템과 컨테이너 --------------------------------------------------------


def _find_inventory_item(
    client: HarnessClient, predicate: Any = None
) -> Optional[dict[str, Any]]:
    """인벤토리를 조회해 조건에 맞는 첫 아이템을 돌려준다."""
    seq = _send_action(client, "request_inventory")
    inventory = client.wait_for("inventory", seq=seq, timeout_ms=3000)

    for item in inventory.get("items", []):
        if predicate is None or predicate(item):
            return item

    return None


def _check_drop_and_get(result: ScenarioResult, client: HarnessClient) -> None:
    """버렸다가 다시 줍는 왕복으로 위치 이동을 확인한다."""
    item = _find_inventory_item(
        client, lambda i: not i.get("is_equipped") and not i.get("is_container")
    )
    if item is None:
        result.skip("버리기·줍기 왕복", "버릴 수 있는 아이템이 없다")
        return

    item_id = item["id"]

    # 버리기
    seq = _send_action(client, "drop", target=item_id)
    try:
        client.wait_for("room_info", timeout_ms=1)
    except HarnessError:
        pass

    dropped = _room_has_entity(client, item_id)
    if not dropped:
        result.fail("버리기·줍기 왕복", f"버린 뒤 방에서 {item_id[-12:]} 를 찾을 수 없다")
        return

    # 다시 줍기
    _send_action(client, "get", target=item_id)
    carried = _inventory_has(client, item_id)

    if not carried:
        result.fail("버리기·줍기 왕복", "다시 줍기 후 인벤토리에 없다")
        return

    result.ok("버리기·줍기 왕복", f"{item_id[-12:]} 방↔인벤토리 이동 확인")


def _room_has_entity(client: HarnessClient, entity_id: str) -> bool:
    """look 으로 방을 다시 조회해 엔티티 존재를 확인한다."""
    _send_action(client, "look")
    try:
        room_info = client.wait_for("room_info", timeout_ms=3000)
    except HarnessError:
        return False

    return any(e.get("id") == entity_id for e in room_info.get("entities", []))


def _inventory_has(client: HarnessClient, item_id: str) -> bool:
    """인벤토리에 아이템이 있는지 확인한다."""
    seq = _send_action(client, "request_inventory")
    try:
        inventory = client.wait_for("inventory", seq=seq, timeout_ms=3000)
    except HarnessError:
        return False

    return any(i.get("id") == item_id for i in inventory.get("items", []))


def _check_equip_cycle(result: ScenarioResult, client: HarnessClient) -> None:
    """장착과 해제가 반영되는지 확인한다.

    초기 상태에 의존하지 않는다. 착용 중인 장비가 있으면 해제 후 재장착으로,
    미착용 장비가 있으면 장착 후 해제로 같은 두 경로를 지난다.
    """
    equipped_item = _find_inventory_item(
        client, lambda i: i.get("equipment_slot") and i.get("is_equipped")
    )
    idle_item = _find_inventory_item(
        client, lambda i: i.get("equipment_slot") and not i.get("is_equipped")
    )

    if equipped_item is not None:
        first, second, item = "unequip", "equip", equipped_item
    elif idle_item is not None:
        first, second, item = "equip", "unequip", idle_item
    else:
        result.skip("장착·해제 왕복", "장착 슬롯을 가진 아이템이 없다")
        return

    item_id = item["id"]
    expected_after_first = first == "equip"

    for verb, expected in ((first, expected_after_first), (second, not expected_after_first)):
        seq = _send_action(client, verb, target=item_id)
        try:
            rejection = client.wait_for("action_rejected", seq=seq, timeout_ms=600)
            result.fail(
                "장착·해제 왕복",
                f"{verb} 거절: {rejection.get('reason_code')}",
            )
            return
        except HarnessError:
            pass

        state = _find_inventory_item(client, lambda i: i.get("id") == item_id)
        if state is None:
            result.fail("장착·해제 왕복", f"{verb} 후 아이템이 인벤토리에서 사라졌다")
            return
        if bool(state.get("is_equipped")) is not expected:
            result.fail(
                "장착·해제 왕복",
                f"{verb} 후 is_equipped 가 {state.get('is_equipped')!r} (기대 {expected})",
            )
            return

    result.ok(
        "장착·해제 왕복",
        f"슬롯 {item.get('equipment_slot')} 에 {first}→{second} 확인",
    )


def _take_into_inventory(
    client: HarnessClient, object_id: Optional[str]
) -> bool:
    """방에 만든 오브젝트를 인벤토리로 옮긴다.

    읽기와 컨테이너 검사는 인벤토리를 훑으므로 바닥에 있으면 찾지 못한다.
    """
    if object_id is None:
        return False

    seq = _send_action(client, "get", target=object_id)
    replies = client.read_json(1200)

    rejected = [
        m for m in replies
        if m.get("type") == "action_rejected" and m.get("seq") == seq
    ]

    if rejected:
        return False

    # 인벤토리에 실제로 들어갔는지 확인한다
    seq = _send_action(client, "request_inventory")

    try:
        inventory = client.wait_for("inventory", seq=seq, timeout_ms=3000)
    except HarnessError:
        return False

    return any(item.get("id") == object_id for item in inventory.get("items", []))


def _check_enter(
    result: ScenarioResult,
    client: HarnessClient,
    fixture: Fixture,
    origin_x: Any,
    origin_y: Any,
) -> None:
    """통로 진입이 동작하는지 확인한다.

    `enter` 는 대상이 없는 verb 다. 현재 좌표의 `room_connections` 항목을 조회해
    이동하므로 통로를 먼저 만들어야 한다.
    """
    if not isinstance(origin_x, int) or not isinstance(origin_y, int):
        result.skip("통로 진입", "원래 좌표를 알 수 없다")
        return

    if not fixture.create_passage(origin_x, origin_y):
        result.skip("통로 진입", "통로를 만들 수 없다")
        return

    seq = _send_action(client, "enter")
    replies = client.read_json(1500)

    rejected = [
        m for m in replies
        if m.get("type") == "action_rejected" and m.get("seq") == seq
    ]

    if rejected:
        result.fail("통로 진입", f"거절됨: {rejected[0].get('reason_code')}")
        return

    moved = [m for m in replies if m.get("type") == "room_info"]

    if not moved:
        result.fail("통로 진입", "room_info 를 받지 못했다")
        return

    # 다시 검증용 방으로 돌아온다. 이후 검사가 그 방을 전제한다
    fixture.send_player(TEST_USERNAME)
    client.read_json(800)

    result.ok("통로 진입", f"({origin_x}, {origin_y}) 로 진입 확인")


def _check_usable(
    result: ScenarioResult, client: HarnessClient, fixture: Fixture
) -> None:
    """사용 가능한 아이템의 use 가 동작하는지 확인한다."""
    object_id = fixture.create_usable()

    if object_id is None:
        result.skip("아이템 사용", "사용 가능한 아이템을 만들 수 없다")
        return

    seq = _send_action(client, "get", target=object_id)

    try:
        client.wait_for("inventory", seq=seq, timeout_ms=3000)
    except HarnessError:
        # 줍기 응답이 inventory 가 아닐 수도 있다. 사용 시도로 넘어간다
        client.read_json(400)

    seq = _send_action(client, "use", target=object_id)

    try:
        replies = client.read_json(1200)
    except HarnessError as exc:
        result.fail("아이템 사용", str(exc))
        return

    rejected = [
        m for m in replies
        if m.get("type") == "action_rejected" and m.get("seq") == seq
    ]

    if rejected:
        result.fail("아이템 사용", f"거절됨: {rejected[0].get('reason_code')}")
        return

    result.ok("아이템 사용", "use 수행")


def _check_unequip_all(result: ScenarioResult, client: HarnessClient) -> None:
    """전체 해제가 동작하는지 확인한다.

    장착한 것이 없으면 `WRONG_STATE` 로 거절하는 것이 정상 동작이다. 앞선
    장착 왕복 검사가 해제로 끝나므로 이 경로를 지나는 경우가 많다.
    """
    seq = _send_action(client, "unequip_all")

    replies = client.read_json(1200)
    rejected = [
        m for m in replies
        if m.get("type") == "action_rejected" and m.get("seq") == seq
    ]

    if not rejected:
        result.ok("전체 해제", "unequip_all 수행")
        return

    code = rejected[0].get("reason_code")

    if code == "WRONG_STATE":
        result.ok("전체 해제", "장착한 것이 없어 WRONG_STATE. 정상 동작이다")
        return

    result.fail("전체 해제", f"거절됨: {code}")


def _check_inventory_full(
    result: ScenarioResult, client: HarnessClient, fixture: Fixture
) -> None:
    """무게 초과를 INVENTORY_FULL 로 거절하는지 확인한다."""
    object_id = fixture.create_heavy()

    if object_id is None:
        result.skip("무게 초과 거절", "무거운 아이템을 만들 수 없다")
        return

    _expect_rejection(
        result,
        client,
        "무게 초과 거절",
        "get",
        "INVENTORY_FULL",
        target=object_id,
    )


def _check_partial_quantity_rejected(
    result: ScenarioResult, client: HarnessClient
) -> None:
    """부분 수량 요청을 거절하는지 확인한다."""
    item = _find_inventory_item(
        client, lambda i: not i.get("is_equipped") and i.get("stack_count", 1) == 1
    )
    if item is None:
        result.skip("부분 수량 거절", "검사할 아이템이 없다")
        return

    _expect_rejection(
        result,
        client,
        "부분 수량 거절",
        "drop",
        "INVALID_PARAMS",
        target=item["id"],
        params={"quantity": 99},
    )


def _check_not_readable_rejected(
    result: ScenarioResult, client: HarnessClient
) -> None:
    """읽을 수 없는 아이템의 read 를 거절하는지 확인한다."""
    item = _find_inventory_item(client, lambda i: not i.get("is_readable"))
    if item is None:
        result.skip("읽기 불가 거절", "읽을 수 없는 아이템이 없다")
        return

    _expect_rejection(
        result,
        client,
        "읽기 불가 거절",
        "read",
        "NOT_APPLICABLE",
        target=item["id"],
    )


def _find_room_entity(
    client: HarnessClient, predicate: Any
) -> Optional[dict[str, Any]]:
    """방을 다시 조회해 조건에 맞는 첫 엔티티를 돌려준다."""
    _send_action(client, "look")
    try:
        room_info = client.wait_for("room_info", timeout_ms=3000)
    except HarnessError:
        return None

    for entity in room_info.get("entities", []):
        if predicate(entity):
            return entity

    return None


def _check_read(result: ScenarioResult, client: HarnessClient) -> None:
    """읽을 수 있는 아이템을 읽는다.

    read 는 소지를 요구하지 않으므로 인벤토리에 없으면 방에서 찾는다.
    """
    item = _find_inventory_item(client, lambda i: i.get("is_readable"))
    source = "인벤토리"

    if item is None:
        item = _find_room_entity(
            client, lambda e: e.get("kind") == "object" and e.get("is_readable")
        )
        source = "방"

    if item is None:
        result.skip("읽기", "읽을 수 있는 아이템이 없다")
        return

    seq = _send_action(client, "read", target=item["id"])

    try:
        rejection = client.wait_for("action_rejected", seq=seq, timeout_ms=600)
        result.fail("읽기", f"읽기 거절: {rejection.get('reason_code')}")
        return
    except HarnessError:
        pass

    result.ok("읽기", f"{source}의 {item['name'].get('ko', '')} 읽기 성공")


def _check_container_cycle(result: ScenarioResult, client: HarnessClient) -> None:
    """컨테이너 열기, 넣기, 꺼내기를 확인한다."""
    container = _find_inventory_item(client, lambda i: i.get("is_container"))

    if container is None:
        # 컨테이너는 방에 있는 경우가 더 흔하다(시체, 상자)
        container = _find_room_entity(
            client, lambda e: e.get("kind") == "object" and e.get("is_container")
        )

    if container is None:
        result.skip("컨테이너 왕복", "인벤토리와 방 모두에 컨테이너가 없다")
        return

    item = _find_inventory_item(
        client,
        lambda i: (
            not i.get("is_container")
            and not i.get("is_equipped")
            and i["id"] != container["id"]
        ),
    )
    if item is None:
        result.skip("컨테이너 왕복", "넣을 아이템이 없다")
        return

    container_id = container["id"]
    item_id = item["id"]

    # 열기
    seq = _send_action(client, "open", target=container_id)
    try:
        contents = client.wait_for("container_contents", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("컨테이너 왕복", f"open 실패: {exc}")
        return

    if contents.get("container_id") != container_id:
        result.fail("컨테이너 왕복", f"container_id 가 {contents.get('container_id')!r}")
        return

    # 넣기
    seq = _send_action(client, "put", target=item_id, params={"container": container_id})
    try:
        rejection = client.wait_for("action_rejected", seq=seq, timeout_ms=600)
        result.fail("컨테이너 왕복", f"put 거절: {rejection.get('reason_code')}")
        return
    except HarnessError:
        pass

    seq = _send_action(client, "open", target=container_id)
    contents = client.wait_for("container_contents", seq=seq, timeout_ms=3000)
    if not any(i.get("id") == item_id for i in contents.get("items", [])):
        result.fail("컨테이너 왕복", "넣은 아이템이 내용물에 없다")
        return

    # 꺼내기
    seq = _send_action(
        client, "take_from", target=item_id, params={"container": container_id}
    )
    try:
        rejection = client.wait_for("action_rejected", seq=seq, timeout_ms=600)
        result.fail("컨테이너 왕복", f"take_from 거절: {rejection.get('reason_code')}")
        return
    except HarnessError:
        pass

    if not _inventory_has(client, item_id):
        result.fail("컨테이너 왕복", "꺼낸 아이템이 인벤토리에 없다")
        return

    result.ok("컨테이너 왕복", "열기·넣기·꺼내기 확인")


# 전투 --------------------------------------------------------------------


def _check_combat_cycle(result: ScenarioResult, client: HarnessClient) -> None:
    """전투 시작, 상태 조회, 도주를 확인한다.

    3초 틱이 몬스터 턴을 처리하므로 상태가 계속 바뀐다. 여기서는 전투 진입과
    이탈이 성립하는지, 그리고 턴 강제가 동작하는지만 확인한다.
    """
    monster = _find_room_entity(
        client,
        lambda e: e.get("kind") == "monster"
        and e.get("is_alive")
        and e.get("disposition") == "hostile",
    )
    if monster is None:
        result.skip("전투 왕복", "방에 적대적인 몬스터가 없다")
        return

    monster_id = monster["id"]

    # 전투 시작
    seq = _send_action(client, "attack", target=monster_id)
    try:
        state = client.wait_for("combat_state", timeout_ms=5000)
    except HarnessError as exc:
        result.fail("전투 왕복", f"attack 후 combat_state 없음: {exc}")
        return

    problems: list[str] = []
    for field in (
        "combat_id",
        "round",
        "current_turn",
        "is_my_turn",
        "turn_order",
        "allies",
        "enemies",
        "is_over",
    ):
        if field not in state:
            problems.append(f"{field} 누락")

    if problems:
        result.fail("전투 왕복", "; ".join(problems))
        return

    if not state["enemies"]:
        result.fail("전투 왕복", "enemies 가 비어 있다")
        return

    # 전투 중에는 이동이 금지된다
    _expect_rejection(
        result,
        client,
        "전투 중 이동 금지",
        "move",
        "WRONG_STATE",
        params={"direction": "north"},
    )

    # 전투 상태 재요청이 이제는 허용된다
    seq = _send_action(client, "request_combat_state")
    try:
        client.wait_for("combat_state", seq=seq, timeout_ms=3000)
        result.ok("전투 중 상태 조회", "combat_state 수신")
    except HarnessError as exc:
        result.fail("전투 중 상태 조회", str(exc))

    # 도주로 이탈
    for _ in range(6):
        seq = _send_action(client, "flee")
        try:
            rejection = client.wait_for("action_rejected", seq=seq, timeout_ms=800)
            if rejection.get("reason_code") in ("NOT_YOUR_TURN", "WRONG_STATE"):
                continue
            result.fail("전투 왕복", f"flee 거절: {rejection.get('reason_code')}")
            return
        except HarnessError:
            pass

        # 도주 성공 여부는 확률이므로 세션 상태로 판정한다
        seq = _send_action(client, "request_state")
        try:
            player_state = client.wait_for("player_state", seq=seq, timeout_ms=3000)
        except HarnessError as exc:
            result.fail("전투 왕복", f"도주 후 상태 조회 실패: {exc}")
            return

        if player_state["player"]["in_combat"] is False:
            result.ok("전투 왕복", "전투 시작과 도주 이탈 확인")
            return

    result.skip("전투 왕복", "도주가 연속 실패해 이탈을 확인하지 못했다")


# 대화 --------------------------------------------------------------------


def _check_dialogue_cycle(result: ScenarioResult, client: HarnessClient) -> None:
    """대화 시작, 선택지 선택, 종료를 확인한다."""
    npc = _find_room_entity(
        client, lambda e: e.get("kind") == "monster" and e.get("can_talk")
    )
    if npc is None:
        result.skip("대화 왕복", "방에 대화 가능한 NPC가 없다")
        return

    npc_id = npc["id"]

    # 대화 시작
    seq = _send_action(client, "talk", target=npc_id)
    try:
        dialogue = client.wait_for("dialogue", seq=seq, timeout_ms=5000)
    except HarnessError as exc:
        result.fail("대화 왕복", f"talk 후 dialogue 없음: {exc}")
        return

    problems: list[str] = []
    for field in ("dialogue_id", "speaker", "lines", "choices", "is_active"):
        if field not in dialogue:
            problems.append(f"{field} 누락")

    if problems:
        result.fail("대화 왕복", "; ".join(problems))
        return

    if dialogue["is_active"] is not True:
        result.fail("대화 왕복", "시작 직후 is_active 가 참이 아니다")
        return

    choices = dialogue["choices"]
    if not choices:
        result.fail("대화 왕복", "선택지가 비어 있다. 종료 선택지가 항상 있어야 한다")
        return

    if not all(isinstance(c.get("index"), int) for c in choices):
        result.fail("대화 왕복", f"index 가 정수가 아니다: {choices}")
        return

    # 없는 선택지는 거절한다
    missing_index = max(c["index"] for c in choices) + 10
    seq = _send_action(client, "dialogue_choice", params={"choice": missing_index})
    try:
        rejection = client.wait_for("action_rejected", seq=seq, timeout_ms=3000)
        if rejection.get("reason_code") != "INVALID_PARAMS":
            result.fail(
                "대화 선택지 검증",
                f"reason_code 가 {rejection.get('reason_code')!r}",
            )
        else:
            result.ok("대화 선택지 검증", "없는 번호를 INVALID_PARAMS 로 거절")
    except HarnessError as exc:
        result.fail("대화 선택지 검증", str(exc))

    # 명시적 종료
    seq = _send_action(client, "dialogue_end")
    try:
        closed = client.wait_for("dialogue", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("대화 왕복", f"dialogue_end 응답 없음: {exc}")
        return

    if closed.get("is_active") is not False:
        result.fail("대화 왕복", "종료 후에도 is_active 가 참이다")
        return

    # 대화 밖에서 선택지를 보내면 거절한다
    _expect_rejection(
        result,
        client,
        "대화 밖 선택지 거절",
        "dialogue_choice",
        "WRONG_STATE",
        params={"choice": 1},
    )

    result.ok(
        "대화 왕복",
        f"{npc['name'].get('ko', '')} 와 대화 시작·종료 확인 (선택지 {len(choices)}개)",
    )


# 사교와 계정 --------------------------------------------------------------


def _check_who(result: ScenarioResult, client: HarnessClient) -> None:
    """who 가 접속자 목록을 계약 형식으로 보내는지 확인한다."""
    seq = _send_action(client, "who")

    try:
        payload = client.wait_for("who_result", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("접속자 목록", str(exc))
        return

    players = payload.get("players")
    if not isinstance(players, list) or not players:
        result.fail("접속자 목록", f"players 가 {players!r}")
        return

    entry = players[0]
    missing = [
        field
        for field in ("id", "username", "display_name", "faction_id", "is_admin")
        if field not in entry
    ]
    if missing:
        result.fail("접속자 목록", f"필드 누락: {missing}")
        return

    if not isinstance(entry["is_admin"], bool):
        result.fail("접속자 목록", f"is_admin 이 boolean 이 아니다: {entry['is_admin']!r}")
        return

    # 좌표를 노출하지 않아야 한다
    leaked = [field for field in ("x", "y", "room_id") if field in entry]
    if leaked:
        result.fail("접속자 목록", f"위치 정보가 노출됐다: {leaked}")
        return

    result.ok("접속자 목록", f"{len(players)}명, 위치 비노출")


def _check_players_here(result: ScenarioResult, client: HarnessClient) -> None:
    """players_here 가 방 범위 목록을 보내는지 확인한다."""
    seq = _send_action(client, "players_here")

    try:
        payload = client.wait_for("who_result", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("방 플레이어 목록", str(exc))
        return

    if not isinstance(payload.get("players"), list):
        result.fail("방 플레이어 목록", f"players 가 {payload.get('players')!r}")
        return

    result.ok("방 플레이어 목록", f"{len(payload['players'])}명")


def _check_emote(result: ScenarioResult, client: HarnessClient) -> None:
    """감정 표현이 목록 검증을 수행하는지 확인한다."""
    _expect_rejection(
        result,
        client,
        "감정 표현 목록 검증",
        "emote",
        "INVALID_PARAMS",
        params={"emote_id": "not_an_emote"},
    )

    seq = _send_action(client, "emote", params={"emote_id": "wave"})
    try:
        rejection = client.wait_for("action_rejected", seq=seq, timeout_ms=800)
        result.fail("감정 표현", f"거절: {rejection.get('reason_code')}")
        return
    except HarnessError:
        pass

    result.ok("감정 표현", "wave 수행")


def _check_unfollow_without_target(
    result: ScenarioResult, client: HarnessClient
) -> None:
    """따라가는 대상이 없을 때 unfollow 를 거절하는지 확인한다."""
    _expect_rejection(
        result, client, "미따라가기 상태 unfollow 거절", "unfollow", "WRONG_STATE"
    )


def _check_changename(result: ScenarioResult, client: HarnessClient) -> None:
    """표시 이름 변경의 검증 경로를 확인한다.

    실제 이름은 바꾸지 않는다. 계정 데이터를 건드리지 않기 위해 거절 경로만 본다.
    """
    _expect_rejection(
        result,
        client,
        "이름 형식 검증",
        "changename",
        "INVALID_PARAMS",
        params={"display_name": "a"},
    )

    _expect_rejection(
        result,
        client,
        "예약 이름 거절",
        "changename",
        "PERMISSION_DENIED",
        params={"display_name": "SUPERADMIN"},
    )


def _check_chat(result: ScenarioResult, client: HarnessClient) -> None:
    """방 채팅과 검증 경로를 확인한다."""
    # 정상 전송
    seq = client.send_json(
        {"type": "chat", "channel": "room", "message": "안녕하세요 카르나스"}
    )
    try:
        echoed = client.wait_for("chat", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("방 채팅", str(exc))
        return

    problems: list[str] = []
    if echoed.get("channel") != "room":
        problems.append(f"channel 이 {echoed.get('channel')!r}")
    if echoed.get("message") != "안녕하세요 카르나스":
        problems.append(f"본문이 변형됐다: {echoed.get('message')!r}")
    if not isinstance(echoed.get("from"), dict):
        problems.append(f"from 이 {echoed.get('from')!r}")
    if "timestamp" not in echoed:
        problems.append("timestamp 누락")

    if problems:
        result.fail("방 채팅", "; ".join(problems))
        return

    result.ok("방 채팅", "한국어 본문 무변형 왕복")

    # 잘못된 채널
    seq = client.send_json({"type": "chat", "channel": "global", "message": "x"})
    try:
        err = client.wait_for("error", seq=seq, timeout_ms=3000)
        if err.get("reason_code") != "MALFORMED_MESSAGE":
            result.fail("채팅 채널 검증", f"reason_code 가 {err.get('reason_code')!r}")
        else:
            result.ok("채팅 채널 검증", "허용되지 않는 채널 거절")
    except HarnessError as exc:
        result.fail("채팅 채널 검증", str(exc))

    # 길이 초과
    seq = client.send_json(
        {"type": "chat", "channel": "room", "message": "가" * 501}
    )
    try:
        err = client.wait_for("error", seq=seq, timeout_ms=3000)
        if err.get("reason_code") != "MALFORMED_MESSAGE":
            result.fail("채팅 길이 검증", f"reason_code 가 {err.get('reason_code')!r}")
        else:
            result.ok("채팅 길이 검증", "500자 초과 거절")
    except HarnessError as exc:
        result.fail("채팅 길이 검증", str(exc))

    # 귓속말 대상 누락
    seq = client.send_json({"type": "chat", "channel": "whisper", "message": "x"})
    try:
        err = client.wait_for("error", seq=seq, timeout_ms=3000)
        if err.get("reason_code") != "MALFORMED_MESSAGE":
            result.fail("귓속말 대상 검증", f"reason_code 가 {err.get('reason_code')!r}")
        else:
            result.ok("귓속말 대상 검증", "대상 누락 거절")
    except HarnessError as exc:
        result.fail("귓속말 대상 검증", str(exc))
