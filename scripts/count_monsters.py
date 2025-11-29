#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""몬스터 수 확인 스크립트"""

import sqlite3
import json

conn = sqlite3.connect('data/mud_engine.db')
cursor = conn.cursor()

# 전체 몬스터 조회
cursor.execute("""
    SELECT name_ko, current_room_id, properties 
    FROM monsters 
    WHERE is_alive = 1
    ORDER BY current_room_id
""")

monsters = cursor.fetchall()

# 전체 몬스터 종류별 카운트
total_counts = {}
# 방별 몬스터 카운트
room_monsters = {}

for name, room_id, properties_str in monsters:
    # 전체 카운트
    total_counts[name] = total_counts.get(name, 0) + 1
    
    # 방별 카운트
    if room_id not in room_monsters:
        room_monsters[room_id] = {}
    room_monsters[room_id][name] = room_monsters[room_id].get(name, 0) + 1

# 전체 요약 출력
print("=" * 60)
print("전체 몬스터 요약")
print("=" * 60)
for name, count in sorted(total_counts.items()):
    print(f"  {name}: {count}마리")
print(f"  총: {len(monsters)}마리")

# 방별 상세 출력
print("\n" + "=" * 60)
print("방별 몬스터 분포")
print("=" * 60)

# 방 이름 조회 (None 제외하고 정렬)
room_ids = [rid for rid in room_monsters.keys() if rid is not None]
room_ids.sort()

# None인 방이 있으면 마지막에 추가
if None in room_monsters:
    room_ids.append(None)

for room_id in room_ids:
    if room_id is None:
        room_name = "위치 없음"
        coord_str = ""
    else:
        cursor.execute("""
            SELECT name_ko, x, y FROM rooms WHERE id = ?
        """, (room_id,))
        room_info = cursor.fetchone()
        
        if room_info:
            room_name, x, y = room_info
            coord_str = f"({x}, {y})" if x is not None and y is not None else ""
        else:
            room_name = room_id
            coord_str = ""
    
    monsters_in_room = room_monsters[room_id]
    total_in_room = sum(monsters_in_room.values())
    
    print(f"\n📍 {room_name} {coord_str}")
    for monster_name, count in sorted(monsters_in_room.items()):
        print(f"   - {monster_name}: {count}마리")
    print(f"   소계: {total_in_room}마리")

conn.close()
