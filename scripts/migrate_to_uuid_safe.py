#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
방 ID를 UUID로 안전하게 마이그레이션하는 스크립트
"""

import sqlite3
import json
from uuid import uuid4
from datetime import datetime
import shutil
import sys

def backup_database(db_path: str) -> str:
    """데이터베이스 백업"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{db_path}.backup_{timestamp}"
    shutil.copy2(db_path, backup_path)
    print(f"✅ 백업 완료: {backup_path}")
    return backup_path

def verify_database(conn):
    """데이터베이스 무결성 검증"""
    cursor = conn.cursor()
    cursor.execute("PRAGMA integrity_check")
    results = cursor.fetchall()
    
    # "ok" 또는 "never used" 페이지만 있으면 정상
    for result in results:
        msg = result[0]
        if msg != "ok" and "never used" not in msg:
            raise Exception(f"DB 무결성 검사 실패: {msg}")
    
    print("✅ DB 무결성 검증 완료")

def create_mapping(conn):
    """ID 매핑 생성"""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM rooms")
    rooms = cursor.fetchall()
    
    mapping = {}
    for row in rooms:
        old_id = row[0]
        new_id = str(uuid4())
        mapping[old_id] = new_id
    
    print(f"✅ {len(mapping)}개 방 ID 매핑 생성")
    
    # 샘플 출력
    sample = list(mapping.items())[:3]
    for old, new in sample:
        print(f"  {old} -> {new[:8]}...")
    
    return mapping

def migrate_rooms(conn, mapping):
    """rooms 테이블 마이그레이션"""
    cursor = conn.cursor()
    
    # 기존 데이터 조회
    cursor.execute("SELECT * FROM rooms")
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    
    print(f"  조회된 방: {len(rows)}개")
    
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
        data = dict(zip(columns, row))
        old_id = data['id']
        new_id = mapping[old_id]
        
        # exits 업데이트
        exits = json.loads(data.get('exits', '{}'))
        new_exits = {}
        for direction, target_id in exits.items():
            new_exits[direction] = mapping.get(target_id, target_id)
        
        cursor.execute("""
            INSERT INTO rooms_new (
                id, name_en, name_ko, description_en, description_ko,
                exits, x, y, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            new_id,
            data['name_en'],
            data['name_ko'],
            data.get('description_en'),
            data.get('description_ko'),
            json.dumps(new_exits, ensure_ascii=False),
            data.get('x'),
            data.get('y'),
            data.get('created_at'),
            data.get('updated_at')
        ))
    
    # 테이블 교체
    cursor.execute("DROP TABLE rooms")
    cursor.execute("ALTER TABLE rooms_new RENAME TO rooms")
    
    print(f"✅ rooms 테이블 마이그레이션 완료")

def migrate_monsters(conn, mapping):
    """monsters 테이블 마이그레이션"""
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, current_room_id, spawn_room_id FROM monsters")
    monsters = cursor.fetchall()
    
    updated = 0
    for monster_id, current_room_id, spawn_room_id in monsters:
        new_current = mapping.get(current_room_id) if current_room_id else None
        new_spawn = mapping.get(spawn_room_id) if spawn_room_id else None
        
        cursor.execute("""
            UPDATE monsters
            SET current_room_id = ?, spawn_room_id = ?
            WHERE id = ?
        """, (new_current, new_spawn, monster_id))
        
        if new_current or new_spawn:
            updated += 1
    
    print(f"✅ monsters 테이블 마이그레이션 완료 ({updated}마리 업데이트)")

def verify_migration(conn):
    """마이그레이션 검증"""
    cursor = conn.cursor()
    
    # rooms 확인
    cursor.execute("SELECT COUNT(*) FROM rooms")
    room_count = cursor.fetchone()[0]
    print(f"  ✓ rooms: {room_count}개")
    
    # UUID 형식 확인
    cursor.execute("SELECT id FROM rooms LIMIT 3")
    sample_ids = cursor.fetchall()
    print(f"  ✓ 샘플 UUID:")
    for row in sample_ids:
        print(f"    {row[0]}")
    
    # monsters 확인
    cursor.execute("SELECT COUNT(*) FROM monsters WHERE current_room_id IS NOT NULL")
    monster_count = cursor.fetchone()[0]
    print(f"  ✓ monsters with room: {monster_count}마리")
    
    # 고아 레코드 확인
    cursor.execute("""
        SELECT COUNT(*) FROM monsters m
        WHERE m.current_room_id IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM rooms r WHERE r.id = m.current_room_id)
    """)
    orphan_count = cursor.fetchone()[0]
    if orphan_count > 0:
        raise Exception(f"고아 레코드 발견: {orphan_count}개")
    print(f"  ✓ 고아 레코드 없음")

def main():
    print("=" * 70)
    print("방 ID를 UUID로 안전하게 마이그레이션")
    print("=" * 70)
    print()
    
    db_path = "data/mud_engine.db"
    
    # 백업
    backup_path = backup_database(db_path)
    
    # 연결
    conn = sqlite3.connect(db_path)
    conn.isolation_level = None  # autocommit 비활성화
    
    try:
        # 무결성 검증
        print("\n1️⃣ DB 무결성 검증 중...")
        verify_database(conn)
        
        # 트랜잭션 시작
        conn.execute("BEGIN TRANSACTION")
        
        # 외래 키 비활성화
        conn.execute("PRAGMA foreign_keys = OFF")
        
        # ID 매핑 생성
        print("\n2️⃣ ID 매핑 생성 중...")
        mapping = create_mapping(conn)
        
        # rooms 마이그레이션
        print("\n3️⃣ rooms 테이블 마이그레이션 중...")
        migrate_rooms(conn, mapping)
        
        # monsters 마이그레이션
        print("\n4️⃣ monsters 테이블 마이그레이션 중...")
        migrate_monsters(conn, mapping)
        
        # 검증
        print("\n5️⃣ 마이그레이션 검증 중...")
        verify_migration(conn)
        
        # 커밋
        conn.execute("COMMIT")
        
        # 외래 키 재활성화
        conn.execute("PRAGMA foreign_keys = ON")
        
        print("\n" + "=" * 70)
        print("✅ 마이그레이션 성공!")
        print("=" * 70)
        print(f"\n백업 파일: {backup_path}")
        print("\n서버를 재시작하여 변경사항을 적용하세요.")
        
    except Exception as e:
        print(f"\n❌ 마이그레이션 실패: {e}")
        print("롤백 중...")
        try:
            conn.execute("ROLLBACK")
            print("✅ 롤백 완료")
        except:
            pass
        
        print(f"\n백업에서 복원:")
        print(f"  cp {backup_path} {db_path}")
        sys.exit(1)
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()
