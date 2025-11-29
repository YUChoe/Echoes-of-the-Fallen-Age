#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""좌표 없는 방의 참조 확인"""

import sqlite3

conn = sqlite3.connect('data/mud_engine.db')
cursor = conn.cursor()

room_ids = ['room_001', 'room_002', 'room_003', 'test_room']

for rid in room_ids:
    cursor.execute('SELECT COUNT(*) FROM monsters WHERE current_room_id=? OR spawn_room_id=?', (rid, rid))
    m = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM npcs WHERE current_room_id=?', (rid,))
    n = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM players WHERE last_room_id=?', (rid,))
    p = cursor.fetchone()[0]
    
    print(f'{rid}: 몬스터={m}, NPC={n}, 플레이어={p}')

conn.close()
