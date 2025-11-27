#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""테스트용 몬스터 생성 스크립트"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mud_engine.database.connection import DatabaseManager
from src.mud_engine.game.monster import Monster, MonsterType, MonsterBehavior, MonsterStats, DropItem


async def create_test_monster():
    """테스트용 고블린 몬스터 생성"""
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    try:
        # 기존 테스트 몬스터 확인
        cursor = await db_manager.execute(
            "SELECT id FROM monsters WHERE id = ?",
            ("test_goblin_001",)
        )
        existing = await cursor.fetchone()
        
        if existing:
            print("✅ 테스트 몬스터가 이미 존재합니다: test_goblin_001")
            
            # 몬스터 정보 조회
            cursor = await db_manager.execute(
                "SELECT * FROM monsters WHERE id = ?",
                ("test_goblin_001",)
            )
            monster_data = await cursor.fetchone()
            
            if monster_data:
                print(f"\n📊 몬스터 정보:")
                print(f"  - ID: {monster_data[0]}")
                print(f"  - 이름(한글): {monster_data[2]}")
                print(f"  - 이름(영어): {monster_data[1]}")
                print(f"  - 타입: {monster_data[5]}")
                print(f"  - 현재 방: {monster_data[11]}")
            
            return
        
        # 숲 방 ID 확인
        cursor = await db_manager.execute(
            "SELECT id FROM rooms WHERE id LIKE 'forest%' LIMIT 1"
        )
        forest_room = await cursor.fetchone()
        
        if not forest_room:
            print("❌ 숲 방을 찾을 수 없습니다.")
            return
        
        forest_room_id = forest_room[0]
        print(f"🌲 숲 방 발견: {forest_room_id}")
        
        # 테스트용 고블린 생성
        goblin = Monster(
            id="test_goblin_001",
            name={
                'en': 'Goblin Warrior',
                'ko': '고블린 전사'
            },
            description={
                'en': 'A small but fierce goblin warrior with a rusty sword.',
                'ko': '녹슨 검을 든 작지만 사나운 고블린 전사입니다.'
            },
            monster_type=MonsterType.AGGRESSIVE,  # 선공형
            behavior=MonsterBehavior.STATIONARY,  # 고정형
            stats=MonsterStats(
                max_hp=30,
                current_hp=30,
                attack_power=8,
                defense=3,
                speed=12,  # 민첩 (턴 순서 결정)
                accuracy=75,
                critical_chance=10
            ),
            experience_reward=50,
            gold_reward=10,
            drop_items=[
                DropItem(
                    item_id="rusty_sword",
                    drop_chance=0.3,  # 30% 확률
                    min_quantity=1,
                    max_quantity=1
                )
            ],
            spawn_room_id=forest_room_id,
            current_room_id=forest_room_id,
            respawn_time=300,  # 5분
            is_alive=True,
            aggro_range=1,
            roaming_range=0,
            properties={'level': 2}
        )
        
        # 데이터베이스에 저장
        goblin_dict = goblin.to_dict()
        
        await db_manager.execute(
            """
            INSERT INTO monsters (
                id, name_en, name_ko, description_en, description_ko,
                monster_type, behavior, stats, experience_reward, gold_reward,
                drop_items, spawn_room_id, current_room_id, respawn_time,
                is_alive, aggro_range, roaming_range, properties, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                goblin_dict['id'],
                goblin_dict['name_en'],
                goblin_dict['name_ko'],
                goblin_dict.get('description_en', ''),
                goblin_dict.get('description_ko', ''),
                goblin_dict['monster_type'],
                goblin_dict['behavior'],
                goblin_dict['stats'],
                goblin_dict['experience_reward'],
                goblin_dict['gold_reward'],
                goblin_dict['drop_items'],
                goblin_dict['spawn_room_id'],
                goblin_dict['current_room_id'],
                goblin_dict['respawn_time'],
                1 if goblin_dict['is_alive'] else 0,
                goblin_dict['aggro_range'],
                goblin_dict['roaming_range'],
                goblin_dict['properties'],
                goblin_dict['created_at'] if isinstance(goblin_dict['created_at'], str) else goblin_dict['created_at'].isoformat()
            )
        )
        
        await db_manager.commit()
        
        print(f"\n✅ 테스트 몬스터 생성 완료!")
        print(f"  - ID: {goblin.id}")
        print(f"  - 이름: {goblin.get_localized_name('ko')} ({goblin.get_localized_name('en')})")
        print(f"  - 타입: {goblin.monster_type.value} (선공형)")
        print(f"  - 위치: {forest_room_id}")
        print(f"  - HP: {goblin.stats.current_hp}/{goblin.stats.max_hp}")
        print(f"  - 공격력: {goblin.stats.attack_power}")
        print(f"  - 방어력: {goblin.stats.defense}")
        print(f"  - 민첩: {goblin.stats.speed}")
        print(f"\n🎮 테스트 방법:")
        print(f"  1. 서버 실행: source mud_engine_env/Scripts/activate && PYTHONPATH=. python -m src.mud_engine.main")
        print(f"  2. Telnet 접속: telnet localhost 4000")
        print(f"  3. 로그인 후 숲으로 이동")
        print(f"  4. 'attack goblin' 명령어로 전투 시작")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(create_test_monster())
