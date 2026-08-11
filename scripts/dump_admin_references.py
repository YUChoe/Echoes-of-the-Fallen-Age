#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""어드민 삭제가 끊을 수 있는 참조 관계를 실제 데이터에서 확인한다.

선언된 외래키만으로는 부족하다. `monsters.faction_id` 와
`game_objects.location_id` 처럼 FK 없이 운영되는 참조가 있고,
`room_connections` 는 방 id 가 아니라 좌표로 방을 가리킨다.

실행:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/dump_admin_references.py
"""

import sqlite3
import sys

DB_PATH = "data/mud_engine.db"


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    print("=" * 70)
    print("선언된 외래키")
    print("-" * 70)
    for table in (
        "players",
        "rooms",
        "room_connections",
        "monsters",
        "game_objects",
        "item_prices",
        "factions",
        "faction_relations",
    ):
        for fk in conn.execute(f"PRAGMA foreign_key_list({table})"):
            print(f"  {table}.{fk['from']} -> {fk['table']}.{fk['to']}")

    print()
    print("=" * 70)
    print("game_objects.location_type 분포")
    print("-" * 70)
    for row in conn.execute(
        "SELECT location_type, COUNT(*) AS c FROM game_objects "
        "GROUP BY location_type ORDER BY c DESC"
    ):
        print(f"  {row['location_type']!r:<16} {row['c']}")

    print()
    print("location_id 가 가리키는 곳 (표본)")
    print("-" * 70)
    for row in conn.execute(
        "SELECT DISTINCT location_type FROM game_objects WHERE location_id IS NOT NULL"
    ):
        loc_type = row["location_type"]
        sample = conn.execute(
            "SELECT location_id FROM game_objects "
            "WHERE location_type = ? AND location_id IS NOT NULL LIMIT 1",
            (loc_type,),
        ).fetchone()
        if sample is None:
            continue
        loc_id = sample["location_id"]
        in_rooms = conn.execute(
            "SELECT 1 FROM rooms WHERE id = ?", (loc_id,)
        ).fetchone()
        in_players = conn.execute(
            "SELECT 1 FROM players WHERE id = ?", (loc_id,)
        ).fetchone()
        in_objects = conn.execute(
            "SELECT 1 FROM game_objects WHERE id = ?", (loc_id,)
        ).fetchone()
        hit = []
        if in_rooms:
            hit.append("rooms")
        if in_players:
            hit.append("players")
        if in_objects:
            hit.append("game_objects")
        print(f"  {loc_type!r:<16} {loc_id[:12]}... -> {hit or ['없음']}")

    print()
    print("=" * 70)
    print("monsters.faction_id 분포")
    print("-" * 70)
    for row in conn.execute(
        "SELECT faction_id, COUNT(*) AS c FROM monsters GROUP BY faction_id"
    ):
        print(f"  {row['faction_id']!r:<16} {row['c']}")

    print()
    print("players.faction_id 분포")
    print("-" * 70)
    for row in conn.execute(
        "SELECT faction_id, COUNT(*) AS c FROM players GROUP BY faction_id"
    ):
        print(f"  {row['faction_id']!r:<16} {row['c']}")

    print()
    print("=" * 70)
    print("room_connections 좌표가 실제 방과 맞는지")
    print("-" * 70)
    for row in conn.execute("SELECT * FROM room_connections LIMIT 10"):
        from_hit = conn.execute(
            "SELECT id FROM rooms WHERE x = ? AND y = ?",
            (row["from_x"], row["from_y"]),
        ).fetchone()
        to_hit = conn.execute(
            "SELECT id FROM rooms WHERE x = ? AND y = ?", (row["to_x"], row["to_y"])
        ).fetchone()
        print(
            f"  ({row['from_x']},{row['from_y']}) -> ({row['to_x']},{row['to_y']})  "
            f"from={'있음' if from_hit else '없음'} to={'있음' if to_hit else '없음'}"
        )

    print()
    print("=" * 70)
    print("좌표 중복 방 (좌표로 참조를 판정할 수 있는지)")
    print("-" * 70)
    dupes = conn.execute(
        "SELECT x, y, COUNT(*) AS c FROM rooms GROUP BY x, y HAVING c > 1"
    ).fetchall()
    print(f"  중복 좌표 {len(dupes)}건")
    for row in dupes[:5]:
        print(f"    ({row['x']},{row['y']}) {row['c']}개")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
