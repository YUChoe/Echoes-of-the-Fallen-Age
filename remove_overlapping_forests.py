#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""평원과 겹치는 숲 방 삭제 스크립트"""

import sqlite3

conn = sqlite3.connect('data/mud_engine.db')
cursor = conn.cursor()

# 평원과 숲이 겹치는 좌표 찾기
cursor.execute("""
    SELECT f.id, f.name_ko, f.x, f.y, p.id as plains_id
    FROM rooms f
    JOIN rooms p ON f.x = p.x AND f.y = p.y
    WHERE f.id LIKE 'forest_%' AND p.id LIKE 'plains_%'
    ORDER BY f.x, f.y
""")

overlapping = cursor.fetchall()

print(f"평원과 겹치는 숲 방: {len(overlapping)}개")
print("="*80)

for room in overlapping:
    print(f"  삭제 예정: {room[0]} ({room[1]}) at ({room[2]}, {room[3]}) - 평원: {room[4]}")

if overlapping:
    print("\n삭제 진행 중...")
    for room in overlapping:
        forest_id = room[0]
        
        # 방 삭제 (exits는 JSON 필드로 rooms 테이블에 포함되어 있음)
        cursor.execute("DELETE FROM rooms WHERE id = ?", (forest_id,))
        
        print(f"  ✅ 삭제 완료: {forest_id}")
    
    conn.commit()
    print(f"\n✅ 총 {len(overlapping)}개의 숲 방이 삭제되었습니다.")
else:
    print("\n겹치는 방이 없습니다.")

conn.close()
