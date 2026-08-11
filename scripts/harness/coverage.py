#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""하니스 커버리지 기록

무엇을 검증했는지 grep 으로 추정하지 않고 실행 중에 기록한다. 시나리오가
보낸 verb 와 서버가 돌려준 거절 코드를 모아, 등록된 verb 전체와 계약의 거절
코드 전체에 대해 빠진 것을 보고한다.

기준 목록은 코드와 계약 문서에서 읽는다. 하드코딩하면 verb 가 늘어날 때
커버리지가 조용히 낮아진다.
"""

import re
from pathlib import Path
from typing import Any, Optional

PROTOCOL_DIR = Path("docs/protocol")

# 계약 문서의 거절 코드 표. 첫 칸이 대문자 코드다.
# 표를 헤더로 구분해 첫 칸이 `코드` 인 표만 읽는다. 모든 대문자 첫 칸을 긁으면
# 환경변수 표의 `ADMIN_HOST`, `LANDING_SERVICE_TOKEN` 이 섞인다
_CODE_ROW = re.compile(r"^\|\s*`([A-Z][A-Z_]+)`\s*\|")

# 서버가 상황에 따라 만들 수 없어 하니스로 재현하기 어려운 코드.
# 빠진 것으로 세지 않되 이유를 남긴다
UNREACHABLE_CODES: dict[str, str] = {
    "OUT_OF_RANGE": "거리 개념이 구현되지 않았다. 같은 방 안에서만 대상 지정이 성립한다",
    "INSUFFICIENT_FUNDS": "상점 미구현. 화폐를 소비하는 경로가 없다",
    "SLOT_OCCUPIED": "장비 교체가 기존 장비를 자동 해제한다. 슬롯 충돌이 발생하지 않는다",
    "COOLDOWN": "재사용 대기 시간을 쓰는 액션이 없다",
    "SESSION_EXPIRED": "어드민 세션 만료는 2시간이라 하니스 한 번에 재현할 수 없다",
    "INSUFFICIENT_QUANTITY": (
        "서버 어디에서도 발생하지 않는다. 계약에만 있는 코드다. "
        "부분 수량 요청은 INVALID_PARAMS 로 거절한다"
    ),
    "INTERNAL_ERROR": "서버 내부 오류를 뜻한다. 의도적으로 재현하면 검증이 아니라 결함 주입이 된다",
    "NOT_YOUR_TURN": "전투가 짧아 상대 턴을 안정적으로 잡을 수 없다. 전투 턴 검증을 별도로 설계해야 한다",
}

# 하니스가 대상으로 삼기 어려운 verb. 빠진 것으로 세지 않되 이유를 남긴다
UNREACHABLE_VERBS: dict[str, str] = {
    "give": "같은 방에 다른 플레이어가 있어야 한다. 테스트 계정이 하나뿐이다",
    "follow": "같은 방에 다른 플레이어가 있어야 한다",
    "use_item": "combat_only 이고 대상이 필요하다. 전투가 짧아 인벤토리 아이템 사용 시점을 잡기 어렵다",
    "end_turn": "combat_only 다. 전투가 한두 턴에 끝나 턴 종료 시점을 잡기 어렵다",
}


class Coverage:
    """하니스 실행 중 무엇을 건드렸는지 기록한다."""

    def __init__(self) -> None:
        self.verbs_sent: set[str] = set()
        self.codes_seen: set[str] = set()
        self.types_sent: set[str] = set()
        self.types_received: set[str] = set()

    def record_sent(self, message: dict[str, Any]) -> None:
        """송신 메시지를 기록한다."""
        msg_type = message.get("type")

        if isinstance(msg_type, str):
            self.types_sent.add(msg_type)

        verb = message.get("verb")
        if msg_type == "action" and isinstance(verb, str):
            self.verbs_sent.add(verb)

        action = message.get("action")
        if msg_type == "admin_action" and isinstance(action, str):
            self.verbs_sent.add(f"admin:{action}")

    def record_received(self, message: dict[str, Any]) -> None:
        """수신 메시지를 기록한다. 거절 코드를 모은다."""
        msg_type = message.get("type")

        if isinstance(msg_type, str):
            self.types_received.add(msg_type)

        code = message.get("reason_code")
        if isinstance(code, str):
            self.codes_seen.add(code)


def registered_verbs() -> set[str]:
    """디스패처에 등록된 verb 전체.

    소스에서 읽으므로 verb 가 늘어나면 커버리지가 자동으로 낮아진다.
    """
    try:
        from src.mud_engine.commands.actions import build_handlers

        return {handler.verb for handler in build_handlers()}
    except Exception:
        # 임포트에 실패하면 커버리지 보고를 건너뛴다. 하니스 자체는 계속 돈다
        return set()


def contract_reason_codes() -> set[str]:
    """계약이 정의한 거절 코드 전체.

    첫 칸이 `코드` 인 표만 읽는다. 계약 문서에는 환경변수 표와 필드 표가 함께
    있어 모든 대문자 첫 칸을 긁으면 코드가 아닌 항목이 섞인다.
    """
    codes: set[str] = set()

    for name in ("entities.md", "admin.md"):
        path = PROTOCOL_DIR / name
        if not path.exists():
            continue

        in_code_table = False

        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()

            if not stripped.startswith("|"):
                in_code_table = False
                continue

            cells = [cell.strip() for cell in stripped.strip("|").split("|")]

            if cells and cells[0] in ("코드", "`코드`"):
                in_code_table = True
                continue

            if cells and set(cells[0]) <= {"-", ":"}:
                continue

            if in_code_table:
                match = _CODE_ROW.match(stripped)
                if match:
                    codes.add(match.group(1))

    return codes


def report(coverage: Coverage) -> int:
    """커버리지를 출력한다.

    Returns:
        빠진 항목 수. 도달 불가로 기록한 것은 세지 않는다
    """
    verbs = registered_verbs()
    codes = contract_reason_codes()

    print()
    print("=" * 60)
    print("하니스 커버리지")
    print("-" * 60)

    gaps = 0

    if verbs:
        covered = verbs & coverage.verbs_sent
        missing = sorted(verbs - coverage.verbs_sent - set(UNREACHABLE_VERBS))
        skipped = sorted(verbs & set(UNREACHABLE_VERBS))

        print(f"  액션 verb      {len(covered)}/{len(verbs)}")
        if missing:
            gaps += len(missing)
            print(f"    미검증 {len(missing)}종: {', '.join(missing)}")
        for verb in skipped:
            print(f"    제외 {verb}: {UNREACHABLE_VERBS[verb]}")
    else:
        print("  액션 verb      기준 목록을 읽을 수 없어 건너뜀")

    if codes:
        covered_codes = codes & coverage.codes_seen
        missing_codes = sorted(codes - coverage.codes_seen - set(UNREACHABLE_CODES))
        skipped_codes = sorted(codes & set(UNREACHABLE_CODES))

        print(f"  거절 코드      {len(covered_codes)}/{len(codes)}")
        if missing_codes:
            gaps += len(missing_codes)
            print(f"    미검증 {len(missing_codes)}종: {', '.join(missing_codes)}")
        for code in skipped_codes:
            print(f"    제외 {code}: {UNREACHABLE_CODES[code]}")
    else:
        print("  거절 코드      기준 목록을 읽을 수 없어 건너뜀")

    print(f"  수신 메시지    {len(coverage.types_received)}종")
    print("=" * 60)

    return gaps


# 하니스 전역 기록기. 클라이언트가 여기에 기록한다
_ACTIVE: Optional[Coverage] = None


def activate() -> Coverage:
    """기록을 시작한다."""
    global _ACTIVE
    _ACTIVE = Coverage()
    return _ACTIVE


def active() -> Optional[Coverage]:
    """현재 기록기. 없으면 None."""
    return _ACTIVE
