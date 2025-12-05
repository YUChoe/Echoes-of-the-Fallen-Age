#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rooms 테이블에서 name_en, name_ko 칼럼 제거 마이그레이션"""

import sqlite3
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def migrate_remove_room_name_columns():
    """rooms 테이블에서 name_en, name_ko 칼럼 제거"""
    
    db_path = 'data/mud_engine.db'
    
    print("=== rooms 테이블 name 칼럼 제거 마이그레이션 ===\n")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. 현재 스키마 확인
        print("1. 현재 rooms 테이블 스키마:")
        cursor.execute("PRAGMA table_info(rooms)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"   {col}")
        print()
        
        # 2. 임시 테이블 생성 (name_en, name_ko 제외)
        print("2. 임시 테이블 생성 중...")
        cursor.execute("""
            CREATE TABLE rooms_new (
                id TEXT PRIMARY KEY,
                description_en TEXT,
                description_ko TEXT,
                exits TEXT DEFAULT '{}',
                x INTEGER,
                y INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   ✅ 임시 테이블 생성 완료\n")
        
        # 3. 데이터 복사 (name_en, name_ko 제외)
        print("3. 데이터 복사 중...")
        cursor.execute("""
            INSERT INTO rooms_new (id, description_en, description_ko, exits, x, y, created_at, updated_at)
            SELECT id, description_en, description_ko, exits, x, y, created_at, updated_at
            FROM rooms
        """)
        affected_rows = cursor.rowcount
        print(f"   ✅ {affected_rows}개 행 복사 완료\n")
        
        # 4. 기존 테이블 삭제
        print("4. 기존 테이블 삭제 중...")
        cursor.execute("DROP TABLE rooms")
        print("   ✅ 기존 테이블 삭제 완료\n")
        
        # 5. 임시 테이블 이름 변경
        print("5. 임시 테이블 이름 변경 중...")
        cursor.execute("ALTER TABLE rooms_new RENAME TO rooms")
        print("   ✅ 테이블 이름 변경 완료\n")
        
        # 6. 인덱스 재생성
        print("6. 인덱스 재생성 중...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rooms_coordinates ON rooms(x, y)")
        print("   ✅ 인덱스 재생성 완료\n")
        
        # 7. 새 스키마 확인
        print("7. 새 rooms 테이블 스키마:")
        cursor.execute("PRAGMA table_info(rooms)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"   {col}")
        print()
        
        # 8. 커밋
        conn.commit()
        print("✅ 마이그레이션 완료!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 마이그레이션 실패: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_remove_room_name_columns()
