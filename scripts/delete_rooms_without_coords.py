#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""좌표 없는 방 삭제 스크립트"""

import sqlite3
import shutil
from datetime import datetime

# 백업 생성
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_file = f"data/mud_engine.db.backup_{timestamp}"
shutil.copy2("data/mud_engine.db", backup_file)
print(f"✅ 백업 생성: {backup_file}")

conn = sqlite3.connect('data/mud_engine.db')
cursor = conn.cursor()

# 1. room_001에 있는 플레이어들을 좌표가 있는 Town Square로 이동
cursor.execute("SELECT id FROM rooms WHERE name_ko='마을 광장' AND x IS NOT NULL AND y IS NOT NULL")
new_room = cursor.fetchone()
if new_room:
    new_room_id = new_room[0]
    cursor.execute("UPDATE players SET last_room_id=? WHERE last_room_id='room_001'", (new_room_id,))
    print(f"✅ room_001의 플레이어 {cursor.rowcount}명을 {new_room_id}로 이동")
else:
    print("❌ 좌표가 있는 Town Square를 찾을 수 없습니다")

# 2. 좌표 없는 방들 삭제
room_ids = ['room_001', 'room_002', 'room_003', 'test_room']

for rid in room_ids:
    cursor.execute("DELETE FROM rooms WHERE id=?", (rid,))
    if cursor.rowcount > 0:
        print(f"✅ 방 삭제: {rid}")
    else:
        print(f"⚠️  방 없음: {rid}")

conn.commit()
conn.close()

print(f"\n✅ 완료. 백업: {backup_file}")
