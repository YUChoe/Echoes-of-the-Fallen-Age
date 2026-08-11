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

    통계와 맵은 Task 7.5 에서 등록한다. 그때까지는 처리기가 없다는 사실이
    거절로 드러나야 한다.
    """
    seq = client.send_json({"type": "admin_stats"})

    try:
        rejected = client.wait_for("admin_rejected", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("미등록 메시지 거절", str(exc))
        return

    if rejected.get("reason_code") != "NOT_APPLICABLE":
        result.fail("미등록 메시지 거절", f"reason_code 가 {rejected.get('reason_code')!r}")
        return

    result.ok("미등록 메시지 거절", "admin_stats 는 Task 7.5 에서 등록된다")


def _check_unknown_action(result: ScenarioResult, client: HarnessClient) -> None:
    """계약에 없는 액션이 거절되는지 확인한다."""
    seq = client.send_json({"type": "admin_action", "action": "drop_database"})

    try:
        rejected = client.wait_for("admin_rejected", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("알 수 없는 액션 거절", str(exc))
        return

    if rejected.get("reason_code") != "NOT_APPLICABLE":
        result.fail("알 수 없는 액션 거절", f"reason_code 가 {rejected.get('reason_code')!r}")
        return

    result.ok("알 수 없는 액션 거절", "계약의 14종만 수행한다")


def _check_template_listing(result: ScenarioResult, client: HarnessClient) -> None:
    """템플릿 목록 액션이 동작하는지 확인한다."""
    seq = client.send_json(
        {"type": "admin_action", "action": "list_monster_templates"}
    )

    try:
        listed = client.wait_for("admin_action_result", seq=seq, timeout_ms=5000)
    except HarnessError as exc:
        result.fail("몬스터 템플릿 목록", str(exc))
        return

    templates = (listed.get("data") or {}).get("templates")

    if not isinstance(templates, list) or not templates:
        result.fail("몬스터 템플릿 목록", f"templates 가 {templates!r}")
        return

    result.ok("몬스터 템플릿 목록", f"{len(templates)}종")


def _check_validate_world(result: ScenarioResult, client: HarnessClient) -> None:
    """기존에 명령어로 노출되지 않았던 세계 검증이 동작하는지 확인한다."""
    seq = client.send_json({"type": "admin_action", "action": "validate_world"})

    try:
        validated = client.wait_for("admin_action_result", seq=seq, timeout_ms=10000)
    except HarnessError as exc:
        result.fail("세계 무결성 검증", str(exc))
        return

    data = validated.get("data") or {}

    if "validation" not in data:
        result.fail("세계 무결성 검증", f"data 가 {sorted(data)}")
        return

    issues = data["validation"]
    total = sum(len(v) for v in issues.values()) if isinstance(issues, dict) else -1

    result.ok("세계 무결성 검증", f"발견 {total}건")


def _check_room_info_action(result: ScenarioResult, client: HarnessClient) -> None:
    """좌표로 방을 조회하는 액션이 동작하는지 확인한다."""
    seq = client.send_json(
        {"type": "admin_action", "action": "room_info", "params": {"x": 0, "y": 0}}
    )

    try:
        info = client.wait_for("admin_action_result", seq=seq, timeout_ms=5000)
    except HarnessError:
        # (0,0) 에 방이 없는 배포도 있다. 그때는 거절이 정상이다
        result.skip("방 조회 액션", "(0,0) 에 방이 없다")
        return

    room = (info.get("data") or {}).get("room") or {}

    if room.get("x") != 0 or room.get("y") != 0:
        result.fail("방 조회 액션", f"room 이 {room!r}")
        return

    result.ok("방 조회 액션", f"{room.get('id', '')[:8]} 조회")


def _check_offline_goto(result: ScenarioResult, client: HarnessClient) -> None:
    """접속하지 않은 플레이어로의 goto 가 거절되는지 확인한다."""
    seq = client.send_json(
        {
            "type": "admin_action",
            "action": "goto",
            "params": {"target_player": "no-such-player", "x": 0, "y": 0},
        }
    )

    try:
        rejected = client.wait_for("admin_rejected", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("미접속 goto 거절", str(exc))
        return

    if rejected.get("reason_code") != "PLAYER_NOT_ONLINE":
        result.fail("미접속 goto 거절", f"reason_code 가 {rejected.get('reason_code')!r}")
        return

    result.ok("미접속 goto 거절", "게임 세션이 있어야 이동시킬 수 있다")


def _check_bad_action_params(result: ScenarioResult, client: HarnessClient) -> None:
    """액션 파라미터 형식 오류가 거절되는지 확인한다."""
    seq = client.send_json(
        {
            "type": "admin_action",
            "action": "spawn_monster",
            "params": {"template_id": "template_small_rat", "x": True, "y": 0},
        }
    )

    try:
        rejected = client.wait_for("admin_rejected", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("액션 파라미터 검증", str(exc))
        return

    if rejected.get("reason_code") != "INVALID_PARAMS":
        result.fail("액션 파라미터 검증", f"reason_code 가 {rejected.get('reason_code')!r}")
        return

    result.ok("액션 파라미터 검증", "bool 은 정수로 받지 않는다")


def _check_list(result: ScenarioResult, client: HarnessClient) -> None:
    """admin_list 가 페이지네이션과 원본 컬럼명을 담는지 확인한다."""
    seq = client.send_json(
        {
            "type": "admin_list",
            "resource": "monsters",
            "page": 1,
            "page_size": 5,
            "sort": {"field": "name_en", "order": "asc"},
        }
    )

    try:
        listed = client.wait_for("admin_list_result", seq=seq, timeout_ms=5000)
    except HarnessError as exc:
        result.fail("리소스 목록", str(exc))
        return

    problems: list[str] = []

    if listed.get("resource") != "monsters":
        problems.append(f"resource 가 {listed.get('resource')!r}")

    if listed.get("page_size") != 5:
        problems.append(f"page_size 가 {listed.get('page_size')!r}")

    total = listed.get("total")
    if not isinstance(total, int) or total < 1:
        problems.append(f"total 이 {total!r}")

    rows = listed.get("rows")
    if not isinstance(rows, list):
        problems.append(f"rows 가 {rows!r}")
    elif len(rows) > 5:
        problems.append(f"page_size 를 초과한 {len(rows)}행")
    elif rows:
        # 어드민은 언어별 dict 로 묶지 않고 원본 컬럼명을 유지한다
        if "name_en" not in rows[0] or "name_ko" not in rows[0]:
            problems.append(f"원본 컬럼명이 아니다: {sorted(rows[0])[:6]}")

    if problems:
        result.fail("리소스 목록", "; ".join(problems))
        return

    result.ok("리소스 목록", f"monsters {len(rows)}/{total}행, 원본 컬럼명 유지")


def _check_password_hash_hidden(
    result: ScenarioResult, client: HarnessClient
) -> None:
    """players 응답에 비밀번호 해시가 실리지 않는지 확인한다."""
    seq = client.send_json(
        {"type": "admin_list", "resource": "players", "page_size": 10}
    )

    try:
        listed = client.wait_for("admin_list_result", seq=seq, timeout_ms=5000)
    except HarnessError as exc:
        result.fail("비밀번호 해시 비노출", str(exc))
        return

    rows = listed.get("rows") or []

    if not rows:
        result.skip("비밀번호 해시 비노출", "players 행이 없다")
        return

    leaked = [row for row in rows if "password_hash" in row]

    if leaked:
        result.fail("비밀번호 해시 비노출", f"{len(leaked)}행에 password_hash 가 있다")
        return

    if "username" not in rows[0]:
        result.fail("비밀번호 해시 비노출", f"username 이 없다: {sorted(rows[0])[:6]}")
        return

    result.ok("비밀번호 해시 비노출", f"players {len(rows)}행에서 제거됨")


def _check_composite_key(result: ScenarioResult, client: HarnessClient) -> None:
    """복합키 리소스가 key 오브젝트로 조회되는지 확인한다."""
    seq = client.send_json(
        {"type": "admin_list", "resource": "faction_relations", "page_size": 1}
    )

    try:
        listed = client.wait_for("admin_list_result", seq=seq, timeout_ms=5000)
    except HarnessError as exc:
        result.fail("복합키 상세 조회", str(exc))
        return

    rows = listed.get("rows") or []

    if not rows:
        result.skip("복합키 상세 조회", "faction_relations 행이 없다")
        return

    key = {
        "faction_a_id": rows[0]["faction_a_id"],
        "faction_b_id": rows[0]["faction_b_id"],
    }

    seq = client.send_json(
        {"type": "admin_get", "resource": "faction_relations", "key": key}
    )

    try:
        got = client.wait_for("admin_get_result", seq=seq, timeout_ms=5000)
    except HarnessError as exc:
        result.fail("복합키 상세 조회", str(exc))
        return

    if got.get("key") != key:
        result.fail("복합키 상세 조회", f"key 가 {got.get('key')!r}")
        return

    if not isinstance(got.get("row"), dict):
        result.fail("복합키 상세 조회", f"row 가 {got.get('row')!r}")
        return

    result.ok("복합키 상세 조회", f"{key}")


def _check_composite_key_rejects_id(
    result: ScenarioResult, client: HarnessClient
) -> None:
    """복합키 리소스에 id 를 보내면 거절하는지 확인한다."""
    seq = client.send_json(
        {"type": "admin_get", "resource": "faction_relations", "id": "wild"}
    )

    try:
        rejected = client.wait_for("admin_rejected", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("복합키 id 거절", str(exc))
        return

    if rejected.get("reason_code") != "INVALID_PARAMS":
        result.fail("복합키 id 거절", f"reason_code 가 {rejected.get('reason_code')!r}")
        return

    result.ok("복합키 id 거절", "key 오브젝트를 요구한다")


def _check_unknown_column(result: ScenarioResult, client: HarnessClient) -> None:
    """존재하지 않는 정렬 컬럼을 거절하는지 확인한다.

    컬럼 이름은 SQL 에 직접 들어가므로 실제 테이블과 대조해야 한다.
    """
    seq = client.send_json(
        {
            "type": "admin_list",
            "resource": "rooms",
            "sort": {"field": "name; DROP TABLE rooms", "order": "asc"},
        }
    )

    try:
        rejected = client.wait_for("admin_rejected", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("알 수 없는 컬럼 거절", str(exc))
        return

    if rejected.get("reason_code") != "INVALID_PARAMS":
        result.fail("알 수 없는 컬럼 거절", f"reason_code 가 {rejected.get('reason_code')!r}")
        return

    result.ok("알 수 없는 컬럼 거절", "정렬 컬럼을 실제 테이블과 대조한다")


def _check_readonly_column(result: ScenarioResult, client: HarnessClient) -> None:
    """비밀번호 해시 직접 수정을 거절하는지 확인한다."""
    seq = client.send_json(
        {
            "type": "admin_update",
            "resource": "players",
            "id": "does-not-matter",
            "values": {"password_hash": "injected"},
        }
    )

    try:
        rejected = client.wait_for("admin_rejected", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("쓰기 금지 컬럼 거절", str(exc))
        return

    if rejected.get("reason_code") != "VALIDATION_FAILED":
        result.fail("쓰기 금지 컬럼 거절", f"reason_code 가 {rejected.get('reason_code')!r}")
        return

    result.ok("쓰기 금지 컬럼 거절", "password_hash 는 이 경로로 쓸 수 없다")


def _check_crud_roundtrip(result: ScenarioResult, client: HarnessClient) -> None:
    """생성·수정·삭제가 왕복하는지 확인한다.

    프로덕션 데이터를 건드리지 않도록 하니스가 만든 방만 다룬다.
    """
    seq = client.send_json(
        {
            "type": "admin_create",
            "resource": "rooms",
            "values": {
                "description_en": "Harness scratch room.",
                "description_ko": "하니스 임시 방.",
                "x": -9999,
                "y": -9999,
                "room_type": "harness",
            },
        }
    )

    try:
        created = client.wait_for("admin_mutate_result", seq=seq, timeout_ms=5000)
    except HarnessError as exc:
        result.fail("CRUD 왕복", f"생성 실패: {exc}")
        return

    room_id = (created.get("key") or {}).get("id")

    if not isinstance(room_id, str):
        result.fail("CRUD 왕복", f"생성 응답의 key 가 {created.get('key')!r}")
        return

    try:
        seq = client.send_json(
            {
                "type": "admin_update",
                "resource": "rooms",
                "id": room_id,
                "values": {"description_ko": "수정된 하니스 임시 방."},
            }
        )
        updated = client.wait_for("admin_mutate_result", seq=seq, timeout_ms=5000)

        row = updated.get("row") or {}
        if row.get("description_ko") != "수정된 하니스 임시 방.":
            result.fail("CRUD 왕복", f"수정 결과가 {row.get('description_ko')!r}")
            return
    except HarnessError as exc:
        result.fail("CRUD 왕복", f"수정 실패: {exc}")
        return
    finally:
        _delete_room(client, room_id)

    seq = client.send_json({"type": "admin_get", "resource": "rooms", "id": room_id})

    try:
        rejected = client.wait_for("admin_rejected", seq=seq, timeout_ms=3000)
    except HarnessError as exc:
        result.fail("CRUD 왕복", f"삭제 후 조회 실패: {exc}")
        return

    if rejected.get("reason_code") != "NOT_FOUND":
        result.fail("CRUD 왕복", f"삭제 후 reason_code 가 {rejected.get('reason_code')!r}")
        return

    result.ok("CRUD 왕복", "생성·수정·삭제 후 NOT_FOUND 확인")


def _check_referenced_delete(result: ScenarioResult, client: HarnessClient) -> None:
    """참조되는 종족 삭제가 REFERENCED 로 거절되는지 확인한다.

    프로덕션 데이터의 종족은 플레이어와 몬스터가 가리키므로 지워지면 안 된다.
    거절이 성립해야 이 검증 자체가 데이터를 훼손하지 않는다.
    """
    seq = client.send_json(
        {"type": "admin_delete", "resource": "factions", "id": "ash_knights"}
    )

    try:
        rejected = client.wait_for("admin_rejected", seq=seq, timeout_ms=5000)
    except HarnessError as exc:
        result.fail("참조 삭제 거절", str(exc))
        return

    if rejected.get("reason_code") != "REFERENCED":
        result.fail("참조 삭제 거절", f"reason_code 가 {rejected.get('reason_code')!r}")
        return

    references = rejected.get("references")

    if not isinstance(references, list) or not references:
        result.fail("참조 삭제 거절", f"references 가 {references!r}")
        return

    resources = {item.get("resource") for item in references}

    # monsters 는 외래키가 선언돼 있지 않아 규칙으로만 잡힌다
    if "players" not in resources or "monsters" not in resources:
        result.fail("참조 삭제 거절", f"참조 목록이 {sorted(resources)}")
        return

    total = sum(item.get("count", 0) for item in references)
    result.ok("참조 삭제 거절", f"{sorted(resources)} 에서 {total}건")


def _check_unreferenced_delete(
    result: ScenarioResult, client: HarnessClient
) -> None:
    """참조가 없는 행은 삭제되는지 확인한다.

    참조 검사가 모든 삭제를 막아버리면 기능이 죽는다. 하니스가 만든 방만 쓴다.
    """
    seq = client.send_json(
        {
            "type": "admin_create",
            "resource": "rooms",
            "values": {
                "description_en": "Harness reference room.",
                "description_ko": "하니스 참조 검사 방.",
                "x": -9998,
                "y": -9998,
                "room_type": "harness",
            },
        }
    )

    try:
        created = client.wait_for("admin_mutate_result", seq=seq, timeout_ms=5000)
    except HarnessError as exc:
        result.fail("비참조 삭제 허용", f"생성 실패: {exc}")
        return

    room_id = (created.get("key") or {}).get("id")

    if not isinstance(room_id, str):
        result.fail("비참조 삭제 허용", f"생성 응답의 key 가 {created.get('key')!r}")
        return

    seq = client.send_json(
        {"type": "admin_delete", "resource": "rooms", "id": room_id}
    )

    try:
        deleted = client.wait_for("admin_mutate_result", seq=seq, timeout_ms=5000)
    except HarnessError as exc:
        result.fail("비참조 삭제 허용", f"삭제 실패: {exc}")
        _delete_room(client, room_id)
        return

    if deleted.get("success") is not True:
        result.fail("비참조 삭제 허용", f"success 가 {deleted.get('success')!r}")
        return

    result.ok("비참조 삭제 허용", "참조가 없는 방은 삭제된다")


def _delete_room(client: HarnessClient, room_id: str) -> None:
    """하니스가 만든 방을 지운다. 실패해도 시나리오를 멈추지 않는다."""
    try:
        seq = client.send_json(
            {"type": "admin_delete", "resource": "rooms", "id": room_id}
        )
        client.wait_for("admin_mutate_result", seq=seq, timeout_ms=5000)
    except HarnessError:
        pass


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
                _check_list(result, client)
                _check_password_hash_hidden(result, client)
                _check_composite_key(result, client)
                _check_composite_key_rejects_id(result, client)
                _check_unknown_column(result, client)
                _check_readonly_column(result, client)
                _check_crud_roundtrip(result, client)
                _check_referenced_delete(result, client)
                _check_unreferenced_delete(result, client)
                _check_unknown_action(result, client)
                _check_bad_action_params(result, client)
                _check_offline_goto(result, client)
                _check_template_listing(result, client)
                _check_room_info_action(result, client)
                _check_validate_world(result, client)
            else:
                result.skip("리소스 CRUD", "관리자 인증에 실패해 확인할 수 없다")
    except HarnessError as exc:
        result.fail("어드민 채널 접속", str(exc))
        return

    _check_no_session_transfer(result, port, game_port)
