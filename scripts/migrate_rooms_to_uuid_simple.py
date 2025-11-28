#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
방 ID를 UUID로 마이그레이션하는 스크립트 (단순 버전)
"""

import sqlite3
import json
from uuid import uuid4
from datetime import datetime
import shutil

def backup_database(db_path: str) -> str:
    """데이터베이스 백업"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{db_path}.backup_{timestamp}"
    shutil.copy2(db_path, backup_path)
    print(f"✅ 데이터베이스 백업 완료: {backup_path}")
    return backup_path

def main():
    print("=" * 70)
    print("방 ID를 UUID로 마이그레이션 (단순 버전)")
    print("=" * 70)
    print()
    
    db_path = "data/mud_engine.db"
    
    # 백업 생성
    backup_path = backup_database(db_path)
    
    # 데이터베이스 연결
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = OFF")
    cursor = conn.cursor()
    
    try:
        # 1. ID 매핑 생성
        print("\n1️⃣ ID 매핑 생성 중...")
        cursor.execute("SELECT id FROM rooms")
        rooms = cursor.fetchall()
        
        mapping = {}
        for row in rooms:
            old_id = row[0]
            new_id = str(uuid4())
            mapping[old_id] = new_id
        
        print(f"✅ {len(mapping)}개 방 매핑 생성 완료")
        
        # 2. rooms 테이블 마이그레이션
        print("\n2️⃣ rooms 테이블 마이그레이션 중...")
        
        # 모든 방 데이터 조회
        cursor.execute("SELECT * FROM rooms")
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        
        # 임시 테이블 생성
        cursor.execute("DROP TABLE IF EXISTS rooms_new")
        cursor.execute("""
            CREATE TABLE rooms_new (
                id TEXT PRIMARY KEY,
                name_en TEXT NOT NULL,
                name_ko TEXT NOT NULL,
                description_en TEXT,
                description_ko TEXT,
                exits TEXT DEFAULT '{}',
                x INTEGER,
                y INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 데이터 변환 및 삽입
        for row in rows:
            room_data = dict(zip(columns, row))
            old_id = room_data['id']
            new_id = mapping[old_id]
            
            # exits JSON 업데이트
            exits = json.loads(room_data.get('exits', '{}'))
            new_exits = {}
            for direction, target_room_id in exits.items():
                if target_room_id in mapping:
                    new_exits[direction] = mapping[target_room_id]
                else:
                    new_exits[direction] = target_room_id
            
            # 새 테이블에 삽입
            cursor.execute("""
                INSERT INTO rooms_new (
                    id, name_en, name_ko, description_en, description_ko,
                    exits, x, y, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                new_id,
                room_data['name_en'],
                room_data['name_ko'],
                room_data.get('description_en'),
                room_data.get('description_ko'),
                json.dumps(new_exits, ensure_ascii=False),
                room_data.get('x'),
                room_data.get('y'),
                room_data.get('created_at'),
                room_data.get('updated_at')
            ))
        
        # 기존 테이블 삭제 및 새 테이블로 교체
        cursor.execute("DROP TABLE rooms")
        cursor.execute("ALTER TABLE rooms_new RENAME TO rooms")
        
        print(f"✅ rooms 테이블 마이그레이션 완료: {len(rows)}개 방")
        
        # 3. monsters 테이블 마이그레이션
        print("\n3️⃣ monsters 테이블 마이그레이션 중...")
        
        cursor.execute("SELECT id, current_room_id, spawn_room_id FROM monsters")
        monsters = cursor.fetchall()
        
        for monster_id, current_room_id, spawn_room_id in monsters:
            new_current = mapping.get(current_room_id) if current_room_id else None
            new_spawn = mapping.get(spawn_room_id) if spawn_room_id else None
            
            cursor.execute("""
                UPDATE monsters
                SET current_room_id = ?, spawn_room_id = ?
                WHERE id = ?
            """, (new_current, new_spawn, monster_id))
        
        print(f"✅ monsters 테이블 마이그레이션 완료: {len(monsters)}마리")
        
        # 커밋
        conn.commit()
        
        # 4. 검증
        print("\n4️⃣ 마이그레이션 검증 중...")
        
        cursor.execute("SELECT COUNT(*) FROM rooms")
        room_count = cursor.fetchone()[0]
        print(f"  ✓ rooms: {room_count}개")
        
        cursor.execute("SELECT id FROM rooms LIMIT 3")
        sample_ids = cursor.fetchall()
        print(f"  ✓ 샘플 UUID:")
        for row in sample_ids:
            print(f"    - {row[0]}")
        
        cursor.execute("""
            SELECT COUNT(*) FROM monsters 
            WHERE current_room_id IS NOT NULL
        """)
        monster_count = cursor.fetchone()[0]
        print(f"  ✓ monsters with room: {monster_count}마리")
        
        print("\n" + "=" * 70)
        print("✅ 마이그레이션 완료!")
        print("=" * 70)
        print(f"\n백업 파일: {backup_path}")
        
    except Exception as e:
        print(f"\n❌ 마이그레이션 실패: {e}")
        conn.rollback()
        print(f"\n백업에서 복원하려면:")
        print(f"  cp {backup_path} {db_path}")
        raise
    
    finally:
        cursor.execute("PRAGMA foreign_keys = ON")
        conn.close()

if __name__ == "__main__":
    main()
