#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""성 열쇠 아이템 생성 스크립트"""

import asyncio
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mud_engine.database.connection import DatabaseManager


async def create_castle_key():
    """성 열쇠 아이템 생성"""
    print("=== 성 열쇠 아이템 생성 ===\n")

    db_manager = None
    try:
        db_manager = DatabaseManager()
        await db_manager.initialize()

        # 기존 성 열쇠 확인
        cursor = await db_manager.execute(
            "SELECT * FROM game_objects WHERE id = ?", ("castle_key",)
        )
        existing_key = await cursor.fetchone()

        if existing_key:
            print("✅ 성 열쇠가 이미 존재합니다.")
            return 0

        # 성 열쇠 아이템 데이터
        castle_key_data = {
            "id": "castle_key",
            "name_en": "Castle Key",
            "name_ko": "성 열쇠",
            "description_en": "A mystical golden key that glows with ancient magic. It bears the seal of the fallen empire and can open the path to the castle.",
            "description_ko": "고대 마법으로 빛나는 신비한 황금 열쇠입니다. 몰락한 제국의 인장이 새겨져 있으며 성으로 가는 길을 열 수 있습니다.",
            "object_type": "key",
            "location_type": "template",
            "location_id": None,
            "weight": 0.1,
            "category": "key",
            "equipment_slot": None,
            "is_equipped": False,
            "properties": json.dumps({
                "key_type": "castle_entrance",
                "magic_level": 3,
                "rarity": "rare",
                "value": 1000,
                "stackable": False,
                "usable": True,
                "durability": -1,  # 무한 내구도
                "special_effects": {
                    "glowing": True,
                    "magical_aura": True
                },
                "usage": {
                    "target": "castle_gate",
                    "effect": "unlock_path",
                    "consumed_on_use": False
                },
                "lore": {
                    "en": "Forged in the final days of the empire, this key was meant to protect the castle's secrets.",
                    "ko": "제국의 마지막 날에 만들어진 이 열쇠는 성의 비밀을 보호하기 위한 것이었습니다."
                }
            }, ensure_ascii=False)
        }

        # 아이템 생성
        await db_manager.execute("""
            INSERT INTO game_objects (
                id, name_en, name_ko, description_en, description_ko,
                object_type, location_type, location_id, weight, category,
                equipment_slot, is_equipped, properties
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            castle_key_data["id"],
            castle_key_data["name_en"],
            castle_key_data["name_ko"],
            castle_key_data["description_en"],
            castle_key_data["description_ko"],
            castle_key_data["object_type"],
            castle_key_data["location_type"],
            castle_key_data["location_id"],
            castle_key_data["weight"],
            castle_key_data["category"],
            castle_key_data["equipment_slot"],
            castle_key_data["is_equipped"],
            castle_key_data["properties"]
        ))

        print(f"✅ 성 열쇠 아이템 생성 완료: {castle_key_data['name_ko']} ({castle_key_data['id']})")
        print(f"   타입: {castle_key_data['object_type']}")
        print(f"   카테고리: {castle_key_data['category']}")
        print(f"   무게: {castle_key_data['weight']} kg")

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
    exit_code = asyncio.run(create_castle_key())
    sys.exit(exit_code)