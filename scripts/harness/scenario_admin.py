#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""어드민 채널 시나리오 (TCP 4001)

server-json-protocol Task 7.1 이 계약대로 동작하는지 확인한다. 검증 대상은
IAC 협상 없는 프레이밍, 인증 전 거절, 관리자 인증, 서비스 인증, 게임 세션
인증 상태의 비전이다.

기대값은 구현에서 가져오지 않고 계약 문서(docs/protocol/admin.md)의 값을
그대로 적는다.
"""

from .client import (
    DEFAULT_ADMIN_PORT,
    DEFAULT_PORT,
    HarnessClient,
    HarnessError,
)
from .result import ScenarioResult

# 계약이 규정한 프로토콜 버전
EXPECTED_PROTOCOL_VERSION = 1

# 테스트 계정 (관리자)
ADMIN_USERNAME = "player5426"
ADMIN_PASSWORD = "test1234"


def _admin_client(port: int) -> HarnessClient:
    """어드민 채널 클라이언트를 만든다.

    어드민 채널은 IAC 협상을 하지 않으므로 Telnet 필터를 끈다.
    """
    return HarnessClient(port=port, verbose=False, filter_telnet=False)


def _check_welcome(result: ScenarioResult, client: HarnessClient) -> None:
    """접속 직후 welcome 이 어드민 채널임을 밝히는지 확인한다.

    게임 채널과 같은 타입이지만 `channel` 이 admin 이고, 번역을 하지 않으므로
    `supported_locales` 와 `title` 이 없다.
    """
    try:
        welcome = client.wait_for("welcome", timeout_ms=3000)
    except HarnessError as exc:
        result.fail("어드민 welcome 수신", str(exc))
        return

    problems: list[str] = []

    if welcome.get("channel") != "admin":
        problems.append(f"channel 이 {welcome.get('channel')!r} (기대 'admin')")

    if welcome.get("protocol_version") != EXPECTED_PROTOCOL_VERSION:
        problems.append(f"protocol_version 이 {welcome.get('protocol_version')!r}")

    if not isinstance(welcome.get("server_version"), str):
        problems.append("server_version 이 문자열이 아니다")

    for absent in ("supported_locales", "title"):
        if absent in welcome:
            problems.append(f"{absent} 가 담겨 있다")

    if problems:
        result.fail("어드민 welcome 형식", "; ".join(problems))
        return

    result.ok("어드민 welcome 형식", "channel=admin")


def _check_game_message_rejected(
    result: ScenarioResult, client: HarnessClient
) -> None:
    """게임 채널 메시지를 어드민 채널에서 보내면 채널을 알려주는지 확인한다."""
    seq = client.send_json(
        {"type": "login", "username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )

    try:
        rejected = client.wait_for("admin_rejected", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("게임 메시지 거절", str(exc))
        return

    if rejected.get("reason_code") != "NOT_APPLICABLE":
        result.fail("게임 메시지 거절", f"reason_code 가 {rejected.get('reason_code')!r}")
        return

    detail = rejected.get("detail", "")
    if "game channel" not in detail:
        result.fail("게임 메시지 거절", f"detail 이 채널을 알리지 않는다: {detail!r}")
        return

    result.ok("게임 메시지 거절", "login 을 NOT_APPLICABLE 로 거절하고 채널을 알린다")


def _check_preauth_rejected(result: ScenarioResult, client: HarnessClient) -> None:
    """인증 전 어드민 메시지가 NOT_AUTHENTICATED 로 거절되는지 확인한다."""
    seq = client.send_json({"type": "admin_stats"})

    try:
        rejected = client.wait_for("admin_rejected", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("인증 전 거절", str(exc))
        return

    if rejected.get("reason_code") != "NOT_AUTHENTICATED":
        result.fail("인증 전 거절", f"reason_code 가 {rejected.get('reason_code')!r}")
        return

    result.ok("인증 전 거절", "admin_stats 를 NOT_AUTHENTICATED 로 거절")


def _check_ping(result: ScenarioResult, client: HarnessClient) -> None:
    """인증 전 ping 이 허용되는지 확인한다."""
    seq = client.send_json({"type": "ping"})

    try:
        pong = client.wait_for("pong", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("인증 전 ping/pong", str(exc))
        return

    if not isinstance(pong.get("server_time"), str):
        result.fail("인증 전 ping/pong", f"server_time 이 {pong.get('server_time')!r}")
        return

    result.ok("인증 전 ping/pong", "인증 없이 허용")


def _check_bad_password(result: ScenarioResult, client: HarnessClient) -> None:
    """잘못된 비밀번호가 거절되는지 확인한다."""
    seq = client.send_json(
        {"type": "admin_login", "username": ADMIN_USERNAME, "password": "wrong-pass"}
    )

    try:
        login = client.wait_for("admin_login_result", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("잘못된 자격 거절", str(exc))
        return

    if login.get("success") is not False:
        result.fail("잘못된 자격 거절", f"success 가 {login.get('success')!r}")
        return

    if login.get("reason_code") != "NOT_AUTHENTICATED":
        result.fail("잘못된 자격 거절", f"reason_code 가 {login.get('reason_code')!r}")
        return

    result.ok("잘못된 자격 거절", "NOT_AUTHENTICATED 응답")


def _check_bad_service_token(result: ScenarioResult, client: HarnessClient) -> None:
    """잘못된 서비스 토큰이 거절되는지 확인한다."""
    seq = client.send_json(
        {"type": "service_login", "service": "landing", "token": "wrong-token"}
    )

    try:
        login = client.wait_for("service_login_result", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("잘못된 서비스 토큰 거절", str(exc))
        return

    if login.get("success") is not False:
        result.fail("잘못된 서비스 토큰 거절", f"success 가 {login.get('success')!r}")
        return

    result.ok("잘못된 서비스 토큰 거절", f"reason_code {login.get('reason_code')}")


def _check_admin_login(result: ScenarioResult, client: HarnessClient) -> bool:
    """관리자 인증이 성공하는지 확인한다.

    Returns:
        인증 성공 여부. 이후 검증의 선행 조건이다
    """
    seq = client.send_json(
        {
            "type": "admin_login",
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD,
        }
    )

    try:
        login = client.wait_for("admin_login_result", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("관리자 인증", str(exc))
        return False

    if login.get("success") is not True:
        result.fail(
            "관리자 인증",
            f"success 가 {login.get('success')!r}, "
            f"reason_code {login.get('reason_code')!r}",
        )
        return False

    problems: list[str] = []

    admin = login.get("admin")
    if not isinstance(admin, dict):
        problems.append(f"admin 이 dict 가 아니다: {admin!r}")
    else:
        if admin.get("username") != ADMIN_USERNAME:
            problems.append(f"username 이 {admin.get('username')!r}")
        if not isinstance(admin.get("id"), str):
            problems.append(f"id 가 {admin.get('id')!r}")

    if not isinstance(login.get("expires_at"), str):
        problems.append(f"expires_at 이 {login.get('expires_at')!r}")

    if problems:
        result.fail("관리자 인증", "; ".join(problems))
        return False

    result.ok("관리자 인증", f"만료 {login['expires_at']}")
    return True


def _check_unimplemented(result: ScenarioResult, client: HarnessClient) -> None:
    """인증 후 미등록 메시지가 NOT_APPLICABLE 로 거절되는지 확인한다.

    리소스 CRUD 와 액션은 Task 7.2~7.5 에서 등록한다. 그때까지는 처리기가
    없다는 사실이 거절로 드러나야 한다.
    """
    seq = client.send_json({"type": "admin_list", "resource": "monsters"})

    try:
        rejected = client.wait_for("admin_rejected", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("미등록 메시지 거절", str(exc))
        return

    if rejected.get("reason_code") != "NOT_APPLICABLE":
        result.fail("미등록 메시지 거절", f"reason_code 가 {rejected.get('reason_code')!r}")
        return

    result.ok("미등록 메시지 거절", "admin_list 는 Task 7.2 에서 등록된다")


def _check_no_session_transfer(
    result: ScenarioResult, admin_port: int, game_port: int
) -> None:
    """게임 세션의 인증 상태가 어드민 채널로 전이되지 않는지 확인한다.

    같은 관리자 계정으로 게임 채널에 로그인한 상태에서 어드민 채널에 새로
    접속해도 인증되지 않은 상태여야 한다.
    """
    game = HarnessClient(port=game_port, verbose=False)

    try:
        game.connect()
        game.wait_for("welcome", timeout_ms=3000)
        seq = game.send_json(
            {
                "type": "login",
                "username": ADMIN_USERNAME,
                "password": ADMIN_PASSWORD,
            }
        )
        login = game.wait_for("login_result", seq=seq, timeout_ms=5000)

        if login.get("success") is not True:
            result.skip("게임 세션 비전이", "게임 채널 로그인에 실패해 확인할 수 없다")
            return

        with _admin_client(admin_port) as admin:
            admin.connect()
            admin_seq = admin.send_json({"type": "admin_stats"})
            rejected = admin.wait_for(
                "admin_rejected", seq=admin_seq, timeout_ms=3000
            )

        if rejected.get("reason_code") != "NOT_AUTHENTICATED":
            result.fail(
                "게임 세션 비전이", f"reason_code 가 {rejected.get('reason_code')!r}"
            )
            return

        result.ok("게임 세션 비전이", "게임 로그인 상태가 어드민 채널로 넘어가지 않는다")
    except HarnessError as exc:
        result.fail("게임 세션 비전이", str(exc))
    finally:
        game.close()


def run(
    result: ScenarioResult,
    port: int = DEFAULT_ADMIN_PORT,
    game_port: int = DEFAULT_PORT,
) -> None:
    """어드민 채널 시나리오를 실행한다."""
    try:
        with _admin_client(port) as client:
            client.connect()

            _check_welcome(result, client)
            _check_preauth_rejected(result, client)
            _check_game_message_rejected(result, client)
            _check_ping(result, client)
            _check_bad_password(result, client)
            _check_bad_service_token(result, client)

            if _check_admin_login(result, client):
                _check_unimplemented(result, client)
            else:
                result.skip("미등록 메시지 거절", "관리자 인증에 실패해 확인할 수 없다")
    except HarnessError as exc:
        result.fail("어드민 채널 접속", str(exc))
        return

    _check_no_session_transfer(result, port, game_port)
