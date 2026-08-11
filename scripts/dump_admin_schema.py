#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""어드민 리소스 8종의 실제 테이블 스키마를 출력한다.

문서가 아니라 DB 파일을 직접 읽는다. 어드민 CRUD 는 컬럼 이름과 기본키를
그대로 노출하므로 추측하면 안 된다.

실행:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/dump_admin_schema.py
"""

import sqlite3
import sys

DB_PATH = "data/mud_engine.db"

TABLES = (
    "players",
    "rooms",
    "room_connections",
    "monsters",
    "game_objects",
    "item_prices",
    "factions",
    "faction_relations",
)


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    existing = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }

    for table in TABLES:
        print("=" * 70)
        if table not in existing:
            print(f"{table}: 테이블 없음")
            continue

        count = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]
        print(f"{table}  (행 {count})")
        print("-" * 70)

        for col in conn.execute(f"PRAGMA table_info({table})"):
            pk = "  PK" if col["pk"] else ""
            notnull = "  NOT NULL" if col["notnull"] else ""
            default = f"  DEFAULT {col['dflt_value']}" if col["dflt_value"] else ""
            print(f"  {col['name']:<28} {col['type']:<12}{pk}{notnull}{default}")

        fks = list(conn.execute(f"PRAGMA foreign_key_list({table})"))
        if fks:
            print("  외래키:")
            for fk in fks:
                print(f"    {fk['from']} -> {fk['table']}.{fk['to']}")

    print("=" * 70)
    print("존재하는 전체 테이블:", sorted(existing))

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
