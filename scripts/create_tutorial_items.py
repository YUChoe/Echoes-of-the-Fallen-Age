#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""튜토리얼 아이템 생성 스크립트"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mud_engine.database.connection import DatabaseManager
from src.mud_engine.game.repositories import GameObjectRepository


async def create_tutorial_items():
    """튜토리얼 아이템들 생성"""
    db_manager = DatabaseManager()
    await db_manager.initialize()

    object_repo = GameObjectRepository(db_manager)

    # 생성할 아이템 목록
    tutorial_items = [
        # 생명의 정수 (퀘스트 아이템)
        {
            "id": "essence_of_life",
            "name_en": "Essence of Life",
            "name_ko": "생명의 정수",
            "description_en": "A glowing essence that contains the power of life. Required for the monk's quest.",
            "description_ko": "생명의 힘이 담긴 빛나는 정수입니다. 수도사의 퀘스트에 필요합니다.",
            "object_type": "item",
            "location_type": "template",
            "location_id": "template",
            "properties": '{"price": 0, "stackable": true, "quest_item": true}',
            "weight": 0.1,
            "category": "quest"
        },

        # 튜토리얼 나무 곤봉
        {
            "id": "tutorial_club",
            "name_en": "Wooden Club",
            "name_ko": "나무 곤봉",
            "description_en": "A simple wooden club. Perfect for beginners.",
            "description_ko": "간단한 나무 곤봉입니다. 초보자에게 적합합니다.",
            "object_type": "item",
            "location_type": "template",
            "location_id": "template",
            "properties": '{"damage": 5, "durability": 100, "price": 10}',
            "weight": 2.0,
            "category": "weapon",
            "equipment_slot": "weapon"
        },

        # 튜토리얼 리넨 상의
        {
            "id": "tutorial_linen_shirt",
            "name_en": "Linen Shirt",
            "name_ko": "리넨 상의",
            "description_en": "A basic linen shirt that provides minimal protection.",
            "description_ko": "최소한의 보호를 제공하는 기본 리넨 상의입니다.",
            "object_type": "item",
            "location_type": "template",
            "location_id": "template",
            "properties": '{"defense": 2, "durability": 50, "price": 5}',
            "weight": 1.0,
            "category": "armor",
            "equipment_slot": "chest"
        },

        # 튜토리얼 리넨 하의
        {
            "id": "tutorial_linen_pants",
            "name_en": "Linen Pants",
            "name_ko": "리넨 하의",
            "description_en": "Basic linen pants for everyday wear.",
            "description_ko": "일상복으로 입는 기본 리넨 하의입니다.",
            "object_type": "item",
            "location_type": "template",
            "location_id": "template",
            "properties": '{"defense": 1, "durability": 50, "price": 3}',
            "weight": 0.8,
            "category": "armor",
            "equipment_slot": "legs"
        }
    ]

    # 기존 아이템 확인 및 생성
    for item_data in tutorial_items:
        existing = await object_repo.get_by_id(item_data["id"])

        if existing:
            print(f"아이템 '{item_data['name_ko']}' 이미 존재")
        else:
            await object_repo.create(item_data)
            print(f"아이템 '{item_data['name_ko']}' 생성 완료")

    print(f"\n총 {len(tutorial_items)}개의 튜토리얼 아이템 처리 완료")

    await db_manager.close()


if __name__ == "__main__":
    asyncio.run(create_tutorial_items())
    sys.exit(0)