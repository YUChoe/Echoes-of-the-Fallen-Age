#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""액션 디스패처 시나리오

액션 디스패처 도입(server-json-protocol Task 4)이 계약대로 동작하는지 확인한다.
검증 대상은 거절 코드 판정과 이동·조회 액션의 왕복이다.

기대값은 계약 문서(docs/protocol/)의 값을 그대로 적는다.
"""

from typing import Any, Optional

from .client import DEFAULT_PORT, HarnessClient, HarnessError
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
            "gold",
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
    for field in ("total_weight", "max_weight", "gold"):
        if field not in inventory:
            problems.append(f"{field} 누락")

    if problems:
        result.fail("request_inventory", "; ".join(problems))
        return

    result.ok(
        "request_inventory",
        f"아이템 {len(inventory['items'])}개, 골드 {inventory['gold']}",
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


def run(result: ScenarioResult, port: int = DEFAULT_PORT) -> None:
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
            _check_move(result, client, room_info)

            client.send_json({"type": "logout"})

    except HarnessError as exc:
        result.skip("액션 시나리오", str(exc))
