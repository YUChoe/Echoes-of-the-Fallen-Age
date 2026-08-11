#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""계약과 구현의 메시지 타입 정합성을 점검한다.

서버가 송신하는 모든 타입이 계약에 정의돼 있는지, 계약의 모든 클라이언트 메시지가
처리되는지 확인한다. 계약(`docs/protocol/`)이 세 저장소의 단일 기준이므로 어긋나면
계약을 먼저 고치고 구현을 맞춘다.

계약에 없는 타입을 서버가 보내면 클라이언트가 "알 수 없는 type 은 무시" 규칙으로
버리므로 통신은 깨지지 않는다. 대신 해당 알림이 전달되지 않는다. 조용히 사라지는
경로를 드러내는 것이 이 스크립트의 목적이다.

실행:
    PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe \
        scripts/check_protocol_consistency.py
"""

import json
import re
import sys
from pathlib import Path

PROTOCOL_DIR = Path("docs/protocol")
SOURCE_DIR = Path("src/mud_engine")

# 계약 문서의 JSON 예시에 담긴 "type": "x"
_DOC_JSON_TYPE = re.compile(r'"type"\s*:\s*"([a-z_]+)"')

# 표에서 타입을 뽑을 때는 첫 칸이 `type` 인 표만 본다. 계약 문서에는 verb 표,
# 필드 표, 폐기 명령어 매핑 표가 함께 있어 모든 표를 긁으면 노이즈가 섞인다
_TABLE_ROW = re.compile(r"^\|\s*`([a-z_]+)`\s*\|", re.MULTILINE)

# 구현에서 송신 타입을 뽑는 두 가지 형태.
# 문자 집합을 좁히면 안 된다. `"moving message"` 처럼 공백이 든 타입을 실제로
# 보내고 있었는데 `[a-z_]+` 로는 잡히지 않아 점검을 통과했다
_SRC_BUILD = re.compile(r'build\(\s*"([^"]+)"')
_SRC_LITERAL = re.compile(r'"type"\s*:\s*"([^"]+)"')

# 클라이언트 메시지를 구현이 처리하는 형태
_SRC_MSG_TYPE_EQ = re.compile(r'msg_type\s*==\s*"([a-z_]+)"')
_SRC_REGISTER = re.compile(r'register\(\s*"([a-z_]+)"')
_SRC_TYPE_SET = re.compile(r'^\s+"([a-z_]+)",\s*$', re.MULTILINE)

# 두 채널이 공유하는 서버 메시지. `admin.md` 에도 예시가 있어 요청으로
# 오분류되지 않게 명시한다
SHARED_SERVER_TYPES = frozenset({"welcome", "pong", "error", "event", "admin_rejected"})

# 표에서 타입이 아닌 것이 잡히는 경우를 걸러낸다. 사유 코드, 필드명, verb 등
NOT_MESSAGE_TYPES = frozenset(
    {
        # 사유 코드는 대문자라 정규식에 걸리지 않지만 소문자 필드명이 걸린다
        "seq", "type", "verb", "target", "params", "id", "key", "values",
        "resource", "page", "page_size", "total", "rows", "row", "success",
        "reason_code", "detail", "message", "actor", "operation", "result",
        "changes", "ts", "counts", "available", "channel", "requires_reauth",
        "admin_channel", "email", "username", "password", "token", "service",
        "preferred_locale", "expires_at", "player_id", "filter", "sort",
        "include_descriptions", "bounds", "blocked_exits", "creature_count",
        "player_count", "item_count", "factions", "room_type", "engine",
        "timestamp", "references", "samples", "count", "columns",
        # 계약 문서가 표로 설명하는 verb 와 필드
        "move", "enter", "look", "examine", "get", "drop", "use", "equip",
        "unequip", "unequip_all", "give", "put", "take_from", "open",
        "attack", "defend", "flee", "talk", "dialogue_choice", "follow",
        "unfollow", "emote", "who", "players_here", "changename", "read",
        "shop_open", "shop_buy", "shop_sell", "whisper", "goto", "kick",
        "spawn_monster", "spawn_item", "terminate", "create_room",
        "update_room", "create_exit", "validate_world",
        "list_monster_templates", "list_item_templates", "scheduler",
        "change_display_name", "room_info_action",
        # 그 밖의 설명용 표 항목
        "players", "rooms", "room_connections", "monsters", "objects",
        "item_prices", "faction_relations", "password_hash", "en", "ko",
    }
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _type_table_entries(text: str) -> set[str]:
    """첫 칸이 `type` 인 표의 행에서 타입을 뽑는다.

    표를 헤더 줄로 구분하고, 헤더의 첫 칸이 `type` 인 표만 읽는다.
    """
    found: set[str] = set()
    in_type_table = False

    for line in text.splitlines():
        stripped = line.strip()

        if not stripped.startswith("|"):
            # 표가 끝났다
            in_type_table = False
            continue

        cells = [cell.strip() for cell in stripped.strip("|").split("|")]

        if not cells:
            continue

        # 헤더 줄 판정. 첫 칸이 type 이면 이 표를 읽는다
        if cells[0] in ("type", "`type`"):
            in_type_table = True
            continue

        # 구분선은 건너뛴다
        if set(cells[0]) <= {"-", ":"}:
            continue

        if in_type_table:
            match = _TABLE_ROW.match(stripped)
            if match:
                found.add(match.group(1))

    return found


def contract_types() -> tuple[set[str], set[str]]:
    """계약이 정의한 (서버→클라이언트, 클라이언트→서버) 타입.

    파일별로 나눈다. `client-to-server.md` 는 클라이언트 메시지를,
    나머지는 서버 메시지를 정의한다. `admin.md` 는 양쪽을 담는다.
    """
    server: set[str] = set()
    client: set[str] = set()

    for path in sorted(PROTOCOL_DIR.glob("*.md")):
        text = _read(path)
        found = set(_DOC_JSON_TYPE.findall(text)) | _type_table_entries(text)
        found -= NOT_MESSAGE_TYPES

        if path.name == "client-to-server.md":
            client |= found
        elif path.name == "admin.md":
            # 어드민 문서는 요청과 응답을 함께 적는다. `_result` 로 끝나거나
            # 공용 서버 메시지면 응답이다
            for name in found:
                if name.endswith("_result") or name in SHARED_SERVER_TYPES:
                    server.add(name)
                else:
                    client.add(name)
        else:
            server |= found

    return server, client


def emitted_types() -> dict[str, set[str]]:
    """구현이 송신하는 타입과 그 위치."""
    found: dict[str, set[str]] = {}

    for path in sorted(SOURCE_DIR.rglob("*.py")):
        text = _read(path)
        names = set(_SRC_BUILD.findall(text)) | set(_SRC_LITERAL.findall(text))

        for name in names - NOT_MESSAGE_TYPES:
            found.setdefault(name, set()).add(str(path).replace("\\", "/"))

    return found


def handled_types() -> set[str]:
    """구현이 처리하는 클라이언트 메시지 타입."""
    handled: set[str] = set()

    for path in sorted(SOURCE_DIR.rglob("*.py")):
        text = _read(path)
        handled |= set(_SRC_MSG_TYPE_EQ.findall(text))
        handled |= set(_SRC_REGISTER.findall(text))

        # channels.py 의 타입 집합
        if path.name == "channels.py":
            handled |= set(_SRC_TYPE_SET.findall(text))

    return handled - NOT_MESSAGE_TYPES


def main() -> int:
    contract_server, contract_client = contract_types()
    emitted = emitted_types()
    handled = handled_types()

    failures = 0

    print("=" * 72)
    print("계약과 구현의 메시지 타입 정합성")
    print("=" * 72)

    print(f"\n계약: 서버 메시지 {len(contract_server)}종, "
          f"클라이언트 메시지 {len(contract_client)}종")
    print(f"구현: 송신 {len(emitted)}종, 처리 {len(handled)}종")

    # 1. 서버가 보내지만 계약에 없는 타입
    undocumented = sorted(set(emitted) - contract_server)
    print(f"\n[1] 계약에 없는 송신 타입: {len(undocumented)}종")
    if undocumented:
        failures += len(undocumented)
        for name in undocumented:
            where = ", ".join(sorted(emitted[name])[:2])
            print(f"  ✗ {name:<24} {where}")
    else:
        print("  없음")

    # 2. 계약에 있지만 서버가 보내지 않는 타입
    unimplemented = sorted(contract_server - set(emitted))
    print(f"\n[2] 계약에 있으나 구현이 보내지 않는 타입: {len(unimplemented)}종")
    if unimplemented:
        for name in unimplemented:
            print(f"  · {name}")
        print("  (미구현 기능이면 정상. 계약 오탈자면 정정 대상)")
    else:
        print("  없음")

    # 3. 계약의 클라이언트 메시지를 구현이 처리하는지
    unhandled = sorted(contract_client - handled)
    print(f"\n[3] 계약에 있으나 처리되지 않는 클라이언트 메시지: {len(unhandled)}종")
    if unhandled:
        failures += len(unhandled)
        for name in unhandled:
            print(f"  ✗ {name}")
    else:
        print("  없음")

    print("\n" + "=" * 72)
    if failures:
        print(f"판정: 불일치 {failures}건")
    else:
        print("판정: 일치")
    print("=" * 72)

    # 결과를 기계가 읽을 수 있게 남긴다
    report = {
        "contract_server": sorted(contract_server),
        "contract_client": sorted(contract_client),
        "emitted": sorted(emitted),
        "handled": sorted(handled),
        "undocumented": undocumented,
        "unimplemented": unimplemented,
        "unhandled": unhandled,
    }
    Path("logs").mkdir(exist_ok=True)
    Path("logs/protocol_consistency.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("\n상세: logs/protocol_consistency.json")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
