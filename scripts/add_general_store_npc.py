#!/usr/bin/env python3
"""
(1,0) 시장에 잡화상 NPC와 판매 아이템 추가 스크립트
"""
import asyncio
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mud_engine.database.connection import DatabaseManager
from src.mud_engine.game.repositories import NPCRepository, GameObjectRepository
from src.mud_engine.game.models import NPC, GameObject
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """잡화상 NPC와 아이템 추가"""
    db_path = project_root / "data" / "mud_engine.db"
    db_manager = DatabaseManager(str(db_path))
    
    try:
        await db_manager.initialize()
        logger.info("데이터베이스 초기화 성공")
        
        npc_repo = NPCRepository(db_manager)
        item_repo = GameObjectRepository(db_manager)
        
        # (1,0) 시장 방 ID 조회
        cursor = await db_manager.execute(
            "SELECT id FROM rooms WHERE x=1 AND y=0 LIMIT 1"
        )
        room_result = await cursor.fetchone()
        
        if not room_result:
            logger.error("(1,0) 좌표에 방이 존재하지 않습니다")
            return
        
        market_room_id = room_result[0]
        logger.info(f"시장 방 ID: {market_room_id}")

        # 판매할 아이템 생성
        items_to_create = [
            {
                "id": "item_health_potion",
                "name": {"en": "Health Potion", "ko": "체력 물약"},
                "description": {"en": "Restores 50 HP", "ko": "체력 50을 회복합니다"},
                "item_type": "consumable",
                "category": "consumable",
                "properties": {"price": 20, "heal_amount": 50}
            },
            {
                "id": "item_bread",
                "name": {"en": "Bread", "ko": "빵"},
                "description": {"en": "Simple bread that restores 10 HP", "ko": "체력 10을 회복하는 간단한 빵"},
                "item_type": "consumable",
                "category": "consumable",
                "properties": {"price": 5, "heal_amount": 10}
            },
            {
                "id": "item_rope",
                "name": {"en": "Rope", "ko": "밧줄"},
                "description": {"en": "A sturdy rope, useful for various purposes", "ko": "튼튼한 밧줄, 다양한 용도로 사용 가능"},
                "item_type": "item",
                "category": "misc",
                "properties": {"price": 15}
            },
            {
                "id": "item_torch",
                "name": {"en": "Torch", "ko": "횃불"},
                "description": {"en": "Provides light in dark places", "ko": "어두운 곳을 밝혀줍니다"},
                "item_type": "item",
                "category": "misc",
                "properties": {"price": 10}
            },
            {
                "id": "item_backpack",
                "name": {"en": "Backpack", "ko": "배낭"},
                "description": {"en": "Increases carrying capacity", "ko": "소지 용량을 증가시킵니다"},
                "item_type": "item",
                "category": "misc",
                "properties": {"price": 50, "capacity_bonus": 10}
            }
        ]
        
        created_item_ids = []
        
        for item_data in items_to_create:
            # 기존 아이템 확인
            existing_item = await item_repo.get_by_id(item_data["id"])
            
            if existing_item:
                logger.info(f"아이템 '{item_data['name']['ko']}' 이미 존재")
                created_item_ids.append(item_data["id"])
            else:
                # 새 아이템 생성
                new_item = GameObject(
                    id=item_data["id"],
                    name=item_data["name"],
                    description=item_data["description"],
                    object_type=item_data["item_type"],
                    location_type="room",
                    location_id=None,  # 상점 아이템은 특정 위치에 없음
                    category=item_data["category"],
                    properties=item_data["properties"]
                )
                
                await item_repo.create(new_item)
                created_item_ids.append(new_item.id)
                logger.info(f"아이템 '{item_data['name']['ko']}' 생성 완료")

        # 잡화상 NPC 생성
        merchant_id = "npc_general_store_merchant"
        
        # 기존 NPC 확인
        existing_npc = await npc_repo.get_by_id(merchant_id)
        
        if existing_npc:
            logger.info(f"잡화상 NPC '{existing_npc.get_localized_name('ko')}' 이미 존재")
            # 상점 인벤토리 업데이트
            await npc_repo.update(merchant_id, {"shop_inventory": created_item_ids})
            logger.info(f"잡화상 상점 인벤토리 업데이트 완료: {len(created_item_ids)}개 아이템")
        else:
            # 새 NPC 생성
            merchant_npc = NPC(
                id=merchant_id,
                name={"en": "General Store Merchant", "ko": "잡화상"},
                description={
                    "en": "A friendly merchant selling various useful items",
                    "ko": "다양한 유용한 물건을 파는 친절한 상인"
                },
                current_room_id=market_room_id,
                npc_type="merchant",
                dialogue={
                    "en": [
                        "Welcome to my shop! Take a look around.",
                        "I have the finest goods in town!",
                        "Need supplies for your adventure?",
                        "Everything you need, right here!"
                    ],
                    "ko": [
                        "제 가게에 오신 것을 환영합니다! 둘러보세요.",
                        "마을에서 가장 좋은 물건들이 있습니다!",
                        "모험에 필요한 물품이 있으신가요?",
                        "필요한 모든 것이 여기 있습니다!"
                    ]
                },
                shop_inventory=created_item_ids,
                properties={"greeting": "환영합니다!"}
            )
            
            await npc_repo.create(merchant_npc)
            logger.info(f"잡화상 NPC '{merchant_npc.get_localized_name('ko')}' 생성 완료")
            logger.info(f"위치: {market_room_id} (1,0)")
            logger.info(f"판매 아이템: {len(created_item_ids)}개")
        
        logger.info("\n=== 생성 완료 ===")
        logger.info(f"NPC ID: {merchant_id}")
        logger.info(f"위치: (1,0) 시장")
        logger.info(f"판매 아이템 목록:")
        for item_data in items_to_create:
            price = item_data["properties"].get("price", 0)
            logger.info(f"  - {item_data['name']['ko']} ({item_data['name']['en']}): {price} 골드")
        
    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
    finally:
        await db_manager.close()
        logger.info("데이터베이스 연결 종료")


if __name__ == "__main__":
    asyncio.run(main())
