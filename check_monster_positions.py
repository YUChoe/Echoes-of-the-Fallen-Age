import sqlite3

conn = sqlite3.connect('data/mud_engine.db')
cursor = conn.cursor()

# 살아있는 쥐들의 위치
cursor.execute("SELECT id, current_room_id FROM monsters WHERE name_en='Small Rat' AND is_alive=1 LIMIT 5")
results = cursor.fetchall()

print('살아있는 쥐들의 위치:')
for r in results:
    print(f'  {r[0][:8]}... in {r[1]}')

conn.close()
