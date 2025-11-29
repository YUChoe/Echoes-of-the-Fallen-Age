#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""종족(Faction) 시스템 추가 마이그레이션 스크립트"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.mud_engine.database.connection import DatabaseManager


async def backup_database():
    """데이터베이스 백업"""
    import shutil
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"data/mud_engine.db.backup_{timestamp}"
    shutil.copy2("data/mud_engine.db", backup_file)
    print(f"✅ 백업 생성: {backup_file}")
    return backup_file


async def create_faction_tables(db_manager: DatabaseManager):
    """종족 관련 테이블 생성"""
    print("\n=== 종족 테이블 생성 ===")
    
    # factions 테이블 생성
    await db_manager.execute("""
        CREATE TABLE IF NOT EXISTS factions (
            id TEXT PRIMARY KEY,
            name_en TEXT NOT NULL,
            name_ko TEXT NOT NULL,
            description_en TEXT,
            description_ko TEXT,
            default_stance TEXT DEFAULT 'NEUTRAL',
            properties TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ factions 테이블 생성 완료")
    
    # faction_relations 테이블 생성
    await db_manager.execute("""
        CREATE TABLE IF NOT EXISTS faction_relations (
            faction_a_id TEXT NOT NULL,
            faction_b_id TEXT NOT NULL,
            relation_value INTEGER DEFAULT 0,
            relation_status TEXT DEFAULT 'NEUTRAL',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (faction_a_id, faction_b_id),
            FOREIGN KEY (faction_a_id) REFERENCES factions(id),
            FOREIGN KEY (faction_b_id) REFERENCES factions(id)
        )
    """)
    print("✅ faction_relations 테이블 생성 완료")


async def add_faction_columns(db_manager: DatabaseManager):
    """기존 테이블에 faction_id 컬럼 추가"""
    print("\n=== faction_id 컬럼 추가 ===")
    
    # monsters 테이블에 faction_id 추가
    try:
        await db_manager.execute("""
            ALTER TABLE monsters ADD COLUMN faction_id TEXT DEFAULT NULL
        """)
        print("✅ monsters 테이블에 faction_id 추가")
    except Exception as e:
        print(f"⚠️  monsters.faction_id 이미 존재하거나 추가 실패: {e}")
    
    # npcs 테이블에 faction_id 추가
    try:
        await db_manager.execute("""
            ALTER TABLE npcs ADD COLUMN faction_id TEXT DEFAULT NULL
        """)
        print("✅ npcs 테이블에 faction_id 추가")
    except Exception as e:
        print(f"⚠️  npcs.faction_id 이미 존재하거나 추가 실패: {e}")
    
    # players 테이블에 faction_id 추가
    try:
        await db_manager.execute("""
            ALTER TABLE players ADD COLUMN faction_id TEXT DEFAULT 'ash_knights'
        """)
        print("✅ players 테이블에 faction_id 추가")
    except Exception as e:
        print(f"⚠️  players.faction_id 이미 존재하거나 추가 실패: {e}")


async def insert_default_factions(db_manager: DatabaseManager):
    """기본 종족 데이터 삽입"""
    print("\n=== 기본 종족 데이터 삽입 ===")
    
    factions = [
        {
            'id': 'ash_knights',
            'name_en': 'Ash Knights',
            'name_ko': '잿빛 기사단',
            'description_en': 'The remnants of the fallen empire, trying to maintain order.',
            'description_ko': '몰락한 제국의 잔존 세력으로, 질서를 유지하려 노력한다.',
            'default_stance': 'FRIENDLY'
        },
        {
            'id': 'goblins',
            'name_en': 'Goblins',
            'name_ko': '고블린',
            'description_en': 'Savage creatures that raid settlements.',
            'description_ko': '정착지를 습격하는 야만적인 생물.',
            'default_stance': 'HOSTILE'
        },
        {
            'id': 'animals',
            'name_en': 'Animals',
            'name_ko': '동물',
            'description_en': 'Wild creatures of the land.',
            'description_ko': '대륙의 야생 동물.',
            'default_stance': 'NEUTRAL'
        }
    ]
    
    for faction in factions:
        try:
            await db_manager.execute("""
                INSERT INTO factions (id, name_en, name_ko, description_en, description_ko, default_stance)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                faction['id'],
                faction['name_en'],
                faction['name_ko'],
                faction['description_en'],
                faction['description_ko'],
                faction['default_stance']
            ))
            print(f"✅ 종족 추가: {faction['name_ko']} ({faction['id']})")
        except Exception as e:
            print(f"⚠️  종족 {faction['id']} 이미 존재하거나 추가 실패: {e}")


async def insert_default_relations(db_manager: DatabaseManager):
    """기본 종족 관계 데이터 삽입"""
    print("\n=== 기본 종족 관계 설정 ===")
    
    # 관계 값: -100 ~ 100
    # -100 ~ -50: HOSTILE (적대)
    # -49 ~ -1: UNFRIENDLY (비우호)
    # 0: NEUTRAL (중립)
    # 1 ~ 49: FRIENDLY (우호)
    # 50 ~ 100: ALLIED (동맹)
    
    relations = [
        # 잿빛 기사단 vs 고블린: 적대
        ('ash_knights', 'goblins', -80, 'HOSTILE'),
        ('goblins', 'ash_knights', -80, 'HOSTILE'),
        
        # 잿빛 기사단 vs 동물: 중립
        ('ash_knights', 'animals', 0, 'NEUTRAL'),
        ('animals', 'ash_knights', 0, 'NEUTRAL'),
        
        # 고블린 vs 동물: 비우호
        ('goblins', 'animals', -20, 'UNFRIENDLY'),
        ('animals', 'goblins', -20, 'UNFRIENDLY'),
    ]
    
    for faction_a, faction_b, value, status in relations:
        try:
            await db_manager.execute("""
                INSERT INTO faction_relations (faction_a_id, faction_b_id, relation_value, relation_status)
                VALUES (?, ?, ?, ?)
            """, (faction_a, faction_b, value, status))
            print(f"✅ 관계 설정: {faction_a} <-> {faction_b}: {status} ({value})")
        except Exception as e:
            print(f"⚠️  관계 {faction_a}-{faction_b} 이미 존재하거나 추가 실패: {e}")


async def update_existing_entities(db_manager: DatabaseManager):
    """기존 엔티티에 종족 할당"""
    print("\n=== 기존 엔티티에 종족 할당 ===")
    
    # 마을 경비병 -> 잿빛 기사단
    cursor = await db_manager.execute("""
        UPDATE monsters 
        SET faction_id = 'ash_knights'
        WHERE name_ko LIKE '%경비병%' OR name_en LIKE '%Guard%'
    """)
    print(f"✅ 경비병 {cursor.rowcount}마리 -> 잿빛 기사단")
    
    # 고블린 -> 고블린 종족
    cursor = await db_manager.execute("""
        UPDATE monsters 
        SET faction_id = 'goblins'
        WHERE name_ko LIKE '%고블린%' OR name_en LIKE '%Goblin%'
    """)
    print(f"✅ 고블린 {cursor.rowcount}마리 -> 고블린 종족")
    
    # 쥐 -> 동물 종족
    cursor = await db_manager.execute("""
        UPDATE monsters 
        SET faction_id = 'animals'
        WHERE name_ko LIKE '%쥐%' OR name_en LIKE '%Rat%'
    """)
    print(f"✅ 쥐 {cursor.rowcount}마리 -> 동물 종족")
    
    # 모든 플레이어 -> 잿빛 기사단 (이미 DEFAULT로 설정됨)
    cursor = await db_manager.execute("""
        UPDATE players 
        SET faction_id = 'ash_knights'
        WHERE faction_id IS NULL
    """)
    print(f"✅ 플레이어 {cursor.rowcount}명 -> 잿빛 기사단")


async def main():
    """메인 실행 함수"""
    print("=== 종족 시스템 마이그레이션 시작 ===\n")
    
    # 백업 생성
    backup_file = await backup_database()
    
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    try:
        # 1. 종족 테이블 생성
        await create_faction_tables(db_manager)
        
        # 2. 기존 테이블에 faction_id 컬럼 추가
        await add_faction_columns(db_manager)
        
        # 3. 기본 종족 데이터 삽입
        await insert_default_factions(db_manager)
        
        # 4. 기본 종족 관계 설정
        await insert_default_relations(db_manager)
        
        # 5. 기존 엔티티에 종족 할당
        await update_existing_entities(db_manager)
        
        print("\n=== 마이그레이션 완료 ===")
        print(f"백업 파일: {backup_file}")
        print("문제 발생 시 백업 파일로 복원하세요.")
        
    except Exception as e:
        print(f"\n❌ 마이그레이션 실패: {e}")
        import traceback
        traceback.print_exc()
        print(f"\n백업 파일로 복원하세요: {backup_file}")
        return 1
    finally:
        await db_manager.close()
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
