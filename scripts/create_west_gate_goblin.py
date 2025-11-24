"""서쪽 게이트 밖에 테스트용 고블린 생성 스크립트"""
import asyncio
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.mud_engine.database.connection import DatabaseManager
from src.mud_engine.game.repositories import MonsterRepository


async def create_west_gate_goblin():
    """서쪽 게이트 밖에 테스트용 고블린 생성"""
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    monster_repo = MonsterRepository(db_manager)
    
    # 서쪽 게이트 밖 방 ID 확인
    cursor = await db_manager.execute(
        "SELECT id, name_ko FROM rooms WHERE id = 'west_gate_outside'"
    )
    room = await cursor.fetchone()
    
    if not room:
        print("❌ 서쪽 게이트 밖 방을 찾을 수 없습니다.")
        await db_manager.close()
        return
    
    print(f"✅ 방 확인: {room[0]} - {room[1]}")
    
    # 기존 고블린 확인
    cursor = await db_manager.execute(
        "SELECT id FROM monsters WHERE id = 'west_gate_goblin_1'"
    )
    existing = await cursor.fetchone()
    
    if existing:
        print("⚠️  이미 고블린이 존재합니다. 삭제 후 재생성합니다.")
        await db_manager.execute(
            "DELETE FROM monsters WHERE id = 'west_gate_goblin_1'"
        )
        await db_manager.commit()
    
    # 고블린 생성
    goblin_data = {
        'id': 'west_gate_goblin_1',
        'name_en': 'Aggressive Goblin',
        'name_ko': '공격적인 고블린',
        'description_en': 'A hostile goblin guarding the west gate area.',
        'description_ko': '서쪽 게이트 지역을 지키는 적대적인 고블린입니다.',
        'monster_type': 'aggressive',
        'behavior': 'aggressive',
        'stats': json.dumps({
            'level': 3,
            'hp': 80,
            'max_hp': 80,
            'attack': 12,
            'defense': 5,
            'speed': 8
        }),
        'experience_reward': 75,
        'gold_reward': 20,
        'drop_items': json.dumps([
            {'item_id': 'rusty_sword', 'chance': 0.3},
            {'item_id': 'health_potion', 'chance': 0.5}
        ]),
        'spawn_room_id': 'west_gate_outside',
        'current_room_id': 'west_gate_outside',
        'respawn_time': 300,
        'is_alive': True,
        'aggro_range': 1,
        'roaming_range': 0,
        'properties': json.dumps({
            'attack_messages': [
                '고블린이 날카로운 단검으로 공격합니다!',
                '고블린이 으르렁거리며 덤벼듭니다!'
            ]
        })
    }
    
    await db_manager.execute(
        """
        INSERT INTO monsters (
            id, name_en, name_ko, description_en, description_ko,
            monster_type, behavior, stats, experience_reward, gold_reward,
            drop_items, spawn_room_id, current_room_id, respawn_time,
            is_alive, aggro_range, roaming_range, properties
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            goblin_data['id'],
            goblin_data['name_en'],
            goblin_data['name_ko'],
            goblin_data['description_en'],
            goblin_data['description_ko'],
            goblin_data['monster_type'],
            goblin_data['behavior'],
            goblin_data['stats'],
            goblin_data['experience_reward'],
            goblin_data['gold_reward'],
            goblin_data['drop_items'],
            goblin_data['spawn_room_id'],
            goblin_data['current_room_id'],
            goblin_data['respawn_time'],
            goblin_data['is_alive'],
            goblin_data['aggro_range'],
            goblin_data['roaming_range'],
            goblin_data['properties']
        )
    )
    
    await db_manager.commit()
    
    print(f"✅ 고블린 생성 완료: {goblin_data['id']}")
    print(f"   이름: {goblin_data['name_ko']}")
    print(f"   타입: {goblin_data['monster_type']}")
    print(f"   위치: {goblin_data['current_room_id']}")
    
    # 생성 확인
    cursor = await db_manager.execute(
        "SELECT id, name_ko, monster_type, current_room_id FROM monsters WHERE id = 'west_gate_goblin_1'"
    )
    result = await cursor.fetchone()
    
    if result:
        print(f"\n✅ 생성 확인: {result[0]} | {result[1]} | {result[2]} | {result[3]}")
    
    await db_manager.close()


if __name__ == "__main__":
    asyncio.run(create_west_gate_goblin())
