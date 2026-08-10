#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""인증과 봉투 검증 시나리오

JSON 송신 전환(server-json-protocol Task 3)이 계약대로 동작하는지 확인한다.
검증 대상은 welcome 송신, 메시지 기반 로그인, ping/pong, 봉투 위반 처리다.

기대값은 구현에서 가져오지 않고 계약 문서(docs/protocol/)의 값을 그대로 적는다.
구현과 계약이 어긋나면 드러나야 하기 때문이다.
"""

from typing import Any

from .client import DEFAULT_PORT, HarnessClient, HarnessError
from .result import ScenarioResult

# 계약이 규정한 프로토콜 버전
EXPECTED_PROTOCOL_VERSION = 1

# 테스트 계정 (관리자)
TEST_USERNAME = "player5426"
TEST_PASSWORD = "test1234"


def _check_welcome(result: ScenarioResult, client: HarnessClient) -> None:
    """접속 직후 welcome 이 계약 형식으로 오는지 확인한다."""
    try:
        welcome = client.wait_for("welcome", timeout_ms=3000)
    except HarnessError as exc:
        result.fail("welcome 수신", str(exc))
        return

    problems: list[str] = []

    if welcome.get("channel") != "game":
        problems.append(f"channel 이 {welcome.get('channel')!r} (기대 'game')")

    if welcome.get("protocol_version") != EXPECTED_PROTOCOL_VERSION:
        problems.append(
            f"protocol_version 이 {welcome.get('protocol_version')!r} "
            f"(기대 {EXPECTED_PROTOCOL_VERSION})"
        )

    if not isinstance(welcome.get("server_version"), str):
        problems.append("server_version 이 문자열이 아니다")

    locales = welcome.get("supported_locales")
    if not isinstance(locales, list) or "en" not in locales or "ko" not in locales:
        problems.append(f"supported_locales 이 {locales!r}")

    title = welcome.get("title")
    if not isinstance(title, dict) or "en" not in title or "ko" not in title:
        problems.append(f"title 이 언어별 dict 가 아니다: {title!r}")

    if problems:
        result.fail("welcome 형식", "; ".join(problems))
    else:
        result.ok("welcome 형식", f"버전 {welcome['server_version']}")


def _check_ping(result: ScenarioResult, client: HarnessClient) -> None:
    """ping 에 같은 seq 의 pong 이 오는지 확인한다."""
    seq = client.send_json({"type": "ping"})

    try:
        pong = client.wait_for("pong", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("ping/pong", str(exc))
        return

    if not isinstance(pong.get("server_time"), str):
        result.fail("ping/pong", f"server_time 이 {pong.get('server_time')!r}")
        return

    result.ok("ping/pong", f"seq={seq} 응답 확인")


def _check_malformed_line(result: ScenarioResult, client: HarnessClient) -> None:
    """JSON 이 아닌 라인에 error(MALFORMED_MESSAGE) 로 응답하는지 확인한다."""
    client.send_line("this is not json")

    try:
        error = client.wait_for("error", timeout_ms=3000)
    except HarnessError as exc:
        result.fail("깨진 라인 처리", str(exc))
        return

    if error.get("reason_code") != "MALFORMED_MESSAGE":
        result.fail("깨진 라인 처리", f"reason_code 가 {error.get('reason_code')!r}")
        return

    result.ok("깨진 라인 처리", "MALFORMED_MESSAGE 응답")


def _check_type_required(result: ScenarioResult, client: HarnessClient) -> None:
    """type 이 없는 JSON 오브젝트를 거부하는지 확인한다."""
    client.send_line('{"username":"x"}')

    try:
        error = client.wait_for("error", timeout_ms=3000)
    except HarnessError as exc:
        result.fail("type 누락 처리", str(exc))
        return

    if error.get("reason_code") != "MALFORMED_MESSAGE":
        result.fail("type 누락 처리", f"reason_code 가 {error.get('reason_code')!r}")
        return

    result.ok("type 누락 처리", "MALFORMED_MESSAGE 응답")


def _check_action_before_login(result: ScenarioResult, client: HarnessClient) -> None:
    """인증 전 액션을 거부하는지 확인한다."""
    seq = client.send_json({"type": "action", "verb": "look"})

    try:
        error = client.wait_for("error", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("인증 전 액션 거부", str(exc))
        return

    if error.get("reason_code") != "NOT_AUTHENTICATED":
        result.fail("인증 전 액션 거부", f"reason_code 가 {error.get('reason_code')!r}")
        return

    result.ok("인증 전 액션 거부", "NOT_AUTHENTICATED 응답")


def _check_admin_message_rejected(
    result: ScenarioResult, client: HarnessClient
) -> None:
    """어드민 메시지를 게임 채널에서 보내면 채널을 알려주는지 확인한다."""
    seq = client.send_json(
        {"type": "admin_login", "username": TEST_USERNAME, "password": TEST_PASSWORD}
    )

    try:
        error = client.wait_for("error", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("어드민 메시지 거절", str(exc))
        return

    if error.get("reason_code") != "NOT_APPLICABLE":
        result.fail("어드민 메시지 거절", f"reason_code 가 {error.get('reason_code')!r}")
        return

    detail = error.get("detail", "")
    if "admin channel" not in detail:
        result.fail("어드민 메시지 거절", f"detail 이 채널을 알리지 않는다: {detail!r}")
        return

    result.ok("어드민 메시지 거절", "admin_login 을 NOT_APPLICABLE 로 거절하고 채널을 알린다")


def _check_login_failure(result: ScenarioResult, client: HarnessClient) -> None:
    """잘못된 비밀번호에 사용자명 존재 여부를 노출하지 않는지 확인한다."""
    seq = client.send_json(
        {"type": "login", "username": TEST_USERNAME, "password": "wrong-password"}
    )

    try:
        login_result = client.wait_for("login_result", seq=seq, timeout_ms=5000)
    except HarnessError as exc:
        result.fail("로그인 실패 응답", str(exc))
        return

    problems: list[str] = []

    if login_result.get("success") is not False:
        problems.append(f"success 가 {login_result.get('success')!r}")

    if login_result.get("reason_code") != "INVALID_CREDENTIALS":
        problems.append(f"reason_code 가 {login_result.get('reason_code')!r}")

    if "player" in login_result:
        problems.append("실패 응답에 player 가 포함됐다")

    if problems:
        result.fail("로그인 실패 응답", "; ".join(problems))
    else:
        result.ok("로그인 실패 응답", "INVALID_CREDENTIALS, 계정 정보 비노출")


def _check_login_success(
    result: ScenarioResult, client: HarnessClient
) -> dict[str, Any] | None:
    """정상 로그인이 player 정보를 담아 성공하는지 확인한다."""
    seq = client.send_json(
        {"type": "login", "username": TEST_USERNAME, "password": TEST_PASSWORD}
    )

    try:
        login_result = client.wait_for("login_result", seq=seq, timeout_ms=5000)
    except HarnessError as exc:
        result.fail("로그인 성공 응답", str(exc))
        return None

    if login_result.get("success") is not True:
        result.fail(
            "로그인 성공 응답",
            f"success={login_result.get('success')!r} "
            f"reason_code={login_result.get('reason_code')!r}",
        )
        return None

    player = login_result.get("player")
    if not isinstance(player, dict):
        result.fail("로그인 성공 응답", f"player 가 {player!r}")
        return None

    missing = [
        field
        for field in ("id", "username", "display_name", "is_admin", "faction_id")
        if field not in player
    ]
    if missing:
        result.fail("로그인 성공 응답", f"player 필드 누락: {missing}")
        return None

    # SQLite 가 boolean 을 정수로 저장하므로 계약 위반이 새기 쉬운 지점이다
    if not isinstance(player["is_admin"], bool):
        result.fail(
            "로그인 성공 응답",
            f"is_admin 이 boolean 이 아니다: {player['is_admin']!r}",
        )
        return None

    result.ok("로그인 성공 응답", f"{player['username']} (admin={player['is_admin']})")
    return login_result


def _check_room_info(result: ScenarioResult, client: HarnessClient) -> None:
    """로그인 후 room_info 가 계약 형식으로 오는지 확인한다."""
    try:
        room_info = client.wait_for("room_info", timeout_ms=5000)
    except HarnessError as exc:
        result.fail("room_info 수신", str(exc))
        return

    problems: list[str] = []

    room = room_info.get("room")
    if not isinstance(room, dict):
        problems.append(f"room 이 {room!r}")
    else:
        for field in ("id", "x", "y", "room_type", "description", "exits"):
            if field not in room:
                problems.append(f"room.{field} 누락")
        if "has_passage" not in room:
            problems.append("room.has_passage 누락")
        if not isinstance(room.get("description"), dict):
            problems.append("room.description 이 언어별 dict 가 아니다")

    if room_info.get("time_of_day") not in ("day", "night"):
        problems.append(f"time_of_day 가 {room_info.get('time_of_day')!r}")

    if not isinstance(room_info.get("entities"), list):
        problems.append(f"entities 가 {room_info.get('entities')!r}")

    if not isinstance(room_info.get("nearby_rooms"), list):
        problems.append(f"nearby_rooms 가 {room_info.get('nearby_rooms')!r}")

    if problems:
        result.fail("room_info 형식", "; ".join(problems))
        return

    entities = room_info["entities"]
    nearby = room_info["nearby_rooms"]
    result.ok(
        "room_info 형식",
        f"엔티티 {len(entities)}개, 주변 방 {len(nearby)}개, "
        f"통로 {room['has_passage']}",
    )


def _check_logout(result: ScenarioResult, client: HarnessClient) -> None:
    """logout 에 logout_result 로 응답하는지 확인한다."""
    seq = client.send_json({"type": "logout"})

    try:
        logout_result = client.wait_for("logout_result", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("로그아웃 응답", str(exc))
        return

    if logout_result.get("success") is not True:
        result.fail("로그아웃 응답", f"success 가 {logout_result.get('success')!r}")
        return

    result.ok("로그아웃 응답", "logout_result 확인")


def run(result: ScenarioResult, port: int = DEFAULT_PORT) -> None:
    """인증 시나리오를 실행한다.

    봉투 위반 검증을 로그인 전에 수행한다. 인증 전 경로도 같은 규칙을
    따르는지 확인해야 하기 때문이다.
    """
    try:
        with HarnessClient(port=port, verbose=False) as client:
            client.connect()

            _check_welcome(result, client)
            _check_ping(result, client)
            _check_malformed_line(result, client)
            _check_type_required(result, client)
            _check_action_before_login(result, client)
            _check_admin_message_rejected(result, client)
            _check_login_failure(result, client)

            if _check_login_success(result, client) is None:
                return

            _check_room_info(result, client)
            _check_logout(result, client)

    except HarnessError as exc:
        result.skip("인증 시나리오", str(exc))
