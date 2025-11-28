#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
방 ID를 UUID로 마이그레이션하는 스크립트

주의: 이 스크립트는 데이터베이스를 영구적으로 변경합니다.
실행 전에 반드시 백업을 생성하세요!
"""

import asyncio
import sys
import json
from pathlib import Path
from uuid import uuid4
from datetime import datetime
import shutil

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mud_engine.database.connection import DatabaseManager


async def backup_database(db_path: str) -> str:
    """데이터베이스 백업"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{db_path}.backup_{timestamp}"
    shutil.copy2(db_path, backup_path)
    print(f"✅ 데이터베이스 백업 완료: {backup_path}")
    return backup_path


async def create_id_mapping(db_manager: DatabaseManager) -> dict:
    """기존 room_id -> 새 UUID 매핑 생성"""
    cursor = await db_manager.execute("SELECT id FROM rooms")
    rows = await cursor.fetchall()
    
    mapping = {}
    for row in rows:
        old_id = row[0]
        new_id = str(uuid4())
        mapping[old_id] = new_id
    
    print(f"✅ ID 매핑 생성 완료: {len(mapping)}개 방")
    
    # 샘플 매핑 출력
    sample_keys = list(mapping.keys())[:5]
    print(f"  샘플 매핑:")
    for key in sample_keys:
        print(f"    {key} -> {mapping[key][:8]}...")
    
    return mapping


async def migrate_rooms_table(db_manager: DatabaseManager, mapping: dict) -> None:
    """rooms 테이블의 ID와 exits 업데이트"""
    print("\n1️⃣ rooms 테이블 마이그레이션 중...")
    
    # 모든 방 데이터 조회
    cursor = await db_manager.execute("SELECT * FROM rooms")
    columns = [description[0] for description in cursor.description]
    rows = await cursor.fetchall()
    
    # 임시 테이블 생성
    await db_manager.execute("DROP TABLE IF EXISTS rooms_new")
    await db_manager.execute("""
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
                print(f"  ⚠️ 경고: 출구 대상 방을 찾을 수 없음: {target_room_id}")
                new_exits[direction] = target_room_id
        
        # 새 테이블에 삽입
        await db_manager.execute("""
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
    await db_manager.execute("DROP TABLE rooms")
    await db_manager.execute("ALTER TABLE rooms_new RENAME TO rooms")
    
    print(f"✅ rooms 테이블 마이그레이션 완료: {len(rows)}개 방")


async def migrate_monsters_table(db_manager: DatabaseManager, mapping: dict) -> None:
    """monsters 테이블의 room_id 필드 업데이트"""
    print("\n2️⃣ monsters 테이블 마이그레이션 중...")
    
    cursor = await db_manager.execute("SELECT id, current_room_id, spawn_room_id FROM monsters")
    rows = await cursor.fetchall()
    
    updated_count = 0
    not_found_count = 0
    for row in rows:
        monster_id, current_room_id, spawn_room_id = row
        
        # current_room_id 매핑
        if current_room_id:
            if current_room_id in mapping:
                new_current_room_id = mapping[current_room_id]
            else:
                print(f"  ⚠️ 경고: 몬스터 {monster_id[:8]}...의 current_room_id '{current_room_id}'를 매핑에서 찾을 수 없음")
                new_current_room_id = current_room_id  # 원본 유지
                not_found_count += 1
        else:
            new_current_room_id = None
        
        # spawn_room_id 매핑
        if spawn_room_id:
            if spawn_room_id in mapping:
                new_spawn_room_id = mapping[spawn_room_id]
            else:
                print(f"  ⚠️ 경고: 몬스터 {monster_id[:8]}...의 spawn_room_id '{spawn_room_id}'를 매핑에서 찾을 수 없음")
                new_spawn_room_id = spawn_room_id  # 원본 유지
                not_found_count += 1
        else:
            new_spawn_room_id = None
        
        await db_manager.execute("""
            UPDATE monsters
            SET current_room_id = ?, spawn_room_id = ?
            WHERE id = ?
        """, (new_current_room_id, new_spawn_room_id, monster_id))
        
        updated_count += 1
    
    if not_found_count > 0:
        print(f"  ⚠️ {not_found_count}개의 매핑되지 않은 room_id 발견")
    print(f"✅ monsters 테이블 마이그레이션 완료: {updated_count}마리")


async def migrate_players_table(db_manager: DatabaseManager, mapping: dict) -> None:
    """players 테이블의 current_room_id 필드 업데이트"""
    print("\n3️⃣ players 테이블 마이그레이션 중...")
    
    # players 테이블에 current_room_id 컬럼이 있는지 확인
    cursor = await db_manager.execute("PRAGMA table_info(players)")
    columns = await cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    if 'current_room_id' not in column_names:
        print("  ℹ️ players 테이블에 current_room_id 컬럼이 없습니다. 건너뜁니다.")
        return
    
    cursor = await db_manager.execute("SELECT id, current_room_id FROM players")
    rows = await cursor.fetchall()
    
    updated_count = 0
    for row in rows:
        player_id, current_room_id = row
        
        if current_room_id and current_room_id in mapping:
            new_room_id = mapping[current_room_id]
            await db_manager.execute("""
                UPDATE players
                SET current_room_id = ?
                WHERE id = ?
            """, (new_room_id, player_id))
            updated_count += 1
    
    print(f"✅ players 테이블 마이그레이션 완료: {updated_count}명")


async def verify_migration(db_manager: DatabaseManager) -> None:
    """마이그레이션 검증"""
    print("\n4️⃣ 마이그레이션 검증 중...")
    
    # rooms 테이블 확인
    cursor = await db_manager.execute("SELECT COUNT(*) FROM rooms")
    room_count = (await cursor.fetchone())[0]
    print(f"  ✓ rooms: {room_count}개")
    
    # UUID 형식 확인
    cursor = await db_manager.execute("SELECT id FROM rooms LIMIT 5")
    sample_ids = await cursor.fetchall()
    print(f"  ✓ 샘플 UUID:")
    for row in sample_ids:
        print(f"    - {row[0]}")
    
    # monsters 테이블 확인
    cursor = await db_manager.execute("""
        SELECT COUNT(*) FROM monsters 
        WHERE current_room_id IS NOT NULL
    """)
    monster_count = (await cursor.fetchone())[0]
    print(f"  ✓ monsters with room: {monster_count}마리")
    
    # 고아 레코드 확인 (존재하지 않는 room_id 참조)
    cursor = await db_manager.execute("""
        SELECT COUNT(*) FROM monsters m
        WHERE m.current_room_id IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM rooms r WHERE r.id = m.current_room_id
        )
    """)
    orphan_count = (await cursor.fetchone())[0]
    if orphan_count > 0:
        print(f"  ⚠️ 경고: {orphan_count}개의 고아 몬스터 발견")
    else:
        print(f"  ✓ 고아 레코드 없음")
    
    print("\n✅ 마이그레이션 검증 완료")


async def main():
    """메인 함수"""
    print("=" * 70)
    print("방 ID를 UUID로 마이그레이션")
    print("=" * 70)
    print()
    print("⚠️  경고: 이 작업은 데이터베이스를 영구적으로 변경합니다!")
    print("⚠️  실행 전에 백업이 자동으로 생성됩니다.")
    print()
    
    # 자동 실행 (스크립트 실행 시 자동으로 진행)
    print("자동 실행 모드: 마이그레이션을 시작합니다...")
    print()
    
    db_path = "data/mud_engine.db"
    
    # 백업 생성
    backup_path = await backup_database(db_path)
    
    # 데이터베이스 연결
    db_manager = DatabaseManager(db_path)
    await db_manager.initialize()
    
    try:
        # 외래 키 제약 조건 비활성화
        await db_manager.execute("PRAGMA foreign_keys = OFF")
        print("외래 키 제약 조건 비활성화")
        
        # ID 매핑 생성
        mapping = await create_id_mapping(db_manager)
        
        # 마이그레이션 실행
        await migrate_rooms_table(db_manager, mapping)
        await migrate_monsters_table(db_manager, mapping)
        await migrate_players_table(db_manager, mapping)
        
        # 외래 키 제약 조건 재활성화
        await db_manager.execute("PRAGMA foreign_keys = ON")
        print("외래 키 제약 조건 재활성화")
        
        # 검증
        await verify_migration(db_manager)
        
        print("\n" + "=" * 70)
        print("✅ 마이그레이션 완료!")
        print("=" * 70)
        print(f"\n백업 파일: {backup_path}")
        print("\n서버를 재시작하여 변경사항을 적용하세요.")
        
    except Exception as e:
        print(f"\n❌ 마이그레이션 실패: {e}")
        print(f"\n백업에서 복원하려면 다음 명령을 실행하세요:")
        print(f"  cp {backup_path} {db_path}")
        raise
    
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
