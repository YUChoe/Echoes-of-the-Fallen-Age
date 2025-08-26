#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
고급 인벤토리 시스템 마이그레이션 스크립트
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.mud_engine.database.connection import DatabaseManager
from src.mud_engine.database.schema import migrate_database
from src.mud_engine.game.models import GameObject

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_sample_items(db_manager: DatabaseManager) -> None:
    """테스트용 아이템들을 생성합니다."""

    sample_items = [
        # 무기류
        {
            'id': 'sword_001',
            'name_en': 'Iron Sword',
            'name_ko': '철검',
            'description_en': 'A sturdy iron sword with a sharp blade.',
            'description_ko': '날카로운 칼날을 가진 튼튼한 철검입니다.',
            'object_type': 'weapon',
            'location_type': 'room',
            'location_id': 'room_001',
            'properties': '{"damage": 15, "durability": 100}',
            'weight': 2.5,
            'category': 'weapon',
            'equipment_slot': 'weapon',
            'is_equipped': False
        },
        {
            'id': 'dagger_001',
            'name_en': 'Steel Dagger',
            'name_ko': '강철 단검',
            'description_en': 'A lightweight steel dagger, perfect for quick strikes.',
            'description_ko': '빠른 공격에 적합한 가벼운 강철 단검입니다.',
            'object_type': 'weapon',
            'location_type': 'room',
            'location_id': 'room_002',
            'properties': '{"damage": 8, "speed": 1.5, "durability": 80}',
            'weight': 0.8,
            'category': 'weapon',
            'equipment_slot': 'weapon',
            'is_equipped': False
        },

        # 방어구류
        {
            'id': 'leather_armor_001',
            'name_en': 'Leather Armor',
            'name_ko': '가죽 갑옷',
            'description_en': 'Basic leather armor that provides decent protection.',
            'description_ko': '적당한 보호력을 제공하는 기본적인 가죽 갑옷입니다.',
            'object_type': 'armor',
            'location_type': 'room',
            'location_id': 'room_003',
            'properties': '{"defense": 5, "durability": 60}',
            'weight': 3.0,
            'category': 'armor',
            'equipment_slot': 'armor',
            'is_equipped': False
        },
        {
            'id': 'chain_mail_001',
            'name_en': 'Chain Mail',
            'name_ko': '사슬 갑옷',
            'description_en': 'Heavy chain mail that offers excellent protection.',
            'description_ko': '뛰어난 보호력을 제공하는 무거운 사슬 갑옷입니다.',
            'object_type': 'armor',
            'location_type': 'room',
            'location_id': 'room_001',
            'properties': '{"defense": 12, "durability": 120}',
            'weight': 8.0,
            'category': 'armor',
            'equipment_slot': 'armor',
            'is_equipped': False
        },

        # 소모품류
        {
            'id': 'health_potion_001',
            'name_en': 'Health Potion',
            'name_ko': '체력 물약',
            'description_en': 'A red potion that restores health when consumed.',
            'description_ko': '마시면 체력을 회복시켜주는 빨간 물약입니다.',
            'object_type': 'consumable',
            'location_type': 'room',
            'location_id': 'room_002',
            'properties': '{"heal_amount": 50}',
            'weight': 0.2,
            'category': 'consumable',
            'equipment_slot': None,
            'is_equipped': False
        },
        {
            'id': 'mana_potion_001',
            'name_en': 'Mana Potion',
            'name_ko': '마나 물약',
            'description_en': 'A blue potion that restores mana when consumed.',
            'description_ko': '마시면 마나를 회복시켜주는 파란 물약입니다.',
            'object_type': 'consumable',
            'location_type': 'room',
            'location_id': 'room_003',
            'properties': '{"mana_amount": 30}',
            'weight': 0.2,
            'category': 'consumable',
            'equipment_slot': None,
            'is_equipped': False
        },

        # 액세서리류
        {
            'id': 'silver_ring_001',
            'name_en': 'Silver Ring',
            'name_ko': '은반지',
            'description_en': 'A beautiful silver ring with intricate engravings.',
            'description_ko': '정교한 조각이 새겨진 아름다운 은반지입니다.',
            'object_type': 'item',
            'location_type': 'room',
            'location_id': 'room_001',
            'properties': '{"magic_resistance": 5}',
            'weight': 0.1,
            'category': 'misc',
            'equipment_slot': 'accessory',
            'is_equipped': False
        },

        # 기타 아이템
        {
            'id': 'bread_001',
            'name_en': 'Bread',
            'name_ko': '빵',
            'description_en': 'A loaf of fresh bread that looks delicious.',
            'description_ko': '맛있어 보이는 신선한 빵 한 덩어리입니다.',
            'object_type': 'consumable',
            'location_type': 'room',
            'location_id': 'room_002',
            'properties': '{"heal_amount": 10}',
            'weight': 0.5,
            'category': 'consumable',
            'equipment_slot': None,
            'is_equipped': False
        },
        {
            'id': 'old_book_001',
            'name_en': 'Old Book',
            'name_ko': '오래된 책',
            'description_en': 'An ancient book filled with mysterious knowledge.',
            'description_ko': '신비로운 지식이 담긴 고대의 책입니다.',
            'object_type': 'item',
            'location_type': 'room',
            'location_id': 'room_003',
            'properties': '{"knowledge": "ancient_lore"}',
            'weight': 1.2,
            'category': 'misc',
            'equipment_slot': None,
            'is_equipped': False
        }
    ]

    logger.info("테스트용 아이템들을 생성합니다...")

    for item_data in sample_items:
        try:
            # 이미 존재하는지 확인
            cursor = await db_manager.execute(
                "SELECT id FROM game_objects WHERE id = ?",
                (item_data['id'],)
            )
            existing = await cursor.fetchone()

            if existing:
                logger.info(f"아이템 {item_data['id']}는 이미 존재합니다. 건너뜁니다.")
                continue

            # 아이템 생성
            await db_manager.execute("""
                INSERT INTO game_objects (
                    id, name_en, name_ko, description_en, description_ko,
                    object_type, location_type, location_id, properties,
                    weight, category, equipment_slot, is_equipped, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item_data['id'],
                item_data['name_en'],
                item_data['name_ko'],
                item_data['description_en'],
                item_data['description_ko'],
                item_data['object_type'],
                item_data['location_type'],
                item_data['location_id'],
                item_data['properties'],
                item_data['weight'],
                item_data['category'],
                item_data['equipment_slot'],
                item_data['is_equipped'],
                datetime.now().isoformat()
            ))

            logger.info(f"아이템 생성됨: {item_data['name_ko']} ({item_data['id']})")

        except Exception as e:
            logger.error(f"아이템 생성 실패 ({item_data['id']}): {e}")

    await db_manager.commit()
    logger.info("테스트용 아이템 생성 완료")


async def main():
    """메인 마이그레이션 함수"""
    logger.info("고급 인벤토리 시스템 마이그레이션 시작")

    db_manager = None
    try:
        # 데이터베이스 연결
        db_manager = DatabaseManager()
        await db_manager.initialize()

        # 스키마 마이그레이션 실행
        logger.info("데이터베이스 스키마 마이그레이션 실행 중...")
        await migrate_database(db_manager)

        # 테스트용 아이템들 생성
        await create_sample_items(db_manager)

        logger.info("고급 인벤토리 시스템 마이그레이션 완료")

    except Exception as e:
        logger.error(f"마이그레이션 실패: {e}", exc_info=True)
        if db_manager:
            await db_manager.rollback()
        sys.exit(1)

    finally:
        if db_manager:
            await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())