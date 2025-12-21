#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""테스트용 몬스터 생성 스크립트"""

import asyncio
import sys
from src.mud_engine.database import get_database_manager
from src.mud_engine.game.monster import Monster, MonsterStats, MonsterBehavior


async def main():
    """메인 함수"""
    print("=== 테스트 몬스터 생성 ===\n")

    db_manager = None
    try:
        db_manager = await get_database_manager()

        # 테스트 몬스터 데이터
        monster_data = {
            'id': 'test_rat_001',
            'name_en': 'Test Rat',
            'name_ko': '테스트 쥐',
            'description_en': 'A small test rat for combat testing.',
            'description_ko': '전투 테스트용 작은 쥐입니다.',
            'stats': {
                'strength': 8,
                'dexterity': 12,
                'constitution': 10,
                'intelligence': 3,
                'wisdom': 11,
                'charisma': 4,
                'level': 1,
                'current_hp': 25
            },
            'behavior': 'AGGRESSIVE',
            'experience_reward': 25,
            'gold_reward': 5,
            'drop_items': [],
            'x': 2,
            'y': -5,
            'is_alive': True
        }

        # 기존 몬스터 확인
        cursor = await db_manager.execute(
            "SELECT id FROM monsters WHERE id = ?",
            (monster_data['id'],)
        )
        existing = await cursor.fetchone()

        if existing:
            print(f"몬스터 {monster_data['id']} 이미 존재함")
            # 기존 몬스터 삭제
            await db_manager.execute(
                "DELETE FROM monsters WHERE id = ?",
                (monster_data['id'],)
            )
            print(f"기존 몬스터 {monster_data['id']} 삭제됨")

        # 새 몬스터 생성
        import json
        await db_manager.execute("""
            INSERT INTO monsters (
                id, name_en, name_ko, description_en, description_ko,
                monster_type, behavior, stats, experience_reward, gold_reward,
                drop_items, x, y, is_alive, faction_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            monster_data['id'],
            monster_data['name_en'],
            monster_data['name_ko'],
            monster_data['description_en'],
            monster_data['description_ko'],
            'aggressive',
            monster_data['behavior'],
            json.dumps(monster_data['stats']),
            monster_data['experience_reward'],
            monster_data['gold_reward'],
            json.dumps(monster_data['drop_items']),
            monster_data['x'],
            monster_data['y'],
            monster_data['is_alive'],
            'animals'
        ))

        print(f"✅ 테스트 몬스터 생성 완료: {monster_data['name_ko']} ({monster_data['id']})")
        print(f"   위치: ({monster_data['x']}, {monster_data['y']})")
        print(f"   HP: {monster_data['stats']['current_hp']}")
        print(f"   레벨: {monster_data['stats']['level']}")

        return 0

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if db_manager:
            try:
                await db_manager.close()
            except Exception:
                pass


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)