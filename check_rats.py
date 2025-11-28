import sqlite3

conn = sqlite3.connect('data/mud_engine.db')
cursor = conn.cursor()

# 좌표 -4, -1에 있는 방 확인
cursor.execute("""
    SELECT id, name_ko, x, y
    FROM rooms
    WHERE x=-4 AND y=-1
""")
room = cursor.fetchone()
print(f"좌표 (-4, -1)의 방: {room}")

# 작은 쥐가 있는 방의 좌표 확인
cursor.execute("""
    SELECT m.current_room_id, r.x, r.y, r.name_ko, r.name_en, 
           GROUP_CONCAT(SUBSTR(m.id, 1, 8)) as rat_ids,
           COUNT(*) as rat_count
    FROM monsters m
    JOIN rooms r ON m.current_room_id = r.id
    WHERE m.name_en='Small Rat' AND m.is_alive=1
    GROUP BY m.current_room_id
    ORDER BY rat_count DESC
    LIMIT 5
""")
results = cursor.fetchall()

print(f'\n작은 쥐가 있는 방들 (쥐가 많은 순):')
print("="*80)
for r in results:
    print(f'  {r[3]} / {r[4]} ({r[0]})')
    print(f'    좌표: ({r[1]}, {r[2]}) - 쥐 {r[6]}마리')
    print(f'    쥐 ID: {r[5]}')
    print()

conn.close()
