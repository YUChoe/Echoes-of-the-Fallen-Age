#!/usr/bin/env python3
"""
초기 NPC와 상점 시스템 생성 스크립트
"""

import asyncio
import logging
import sys
import os
from uuid import uuid4

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.mud_engine.database.connection import DatabaseManager
from src.mud_engine.database.schema import migrate_database
from src.mud_engine.game.repositories import ModelManager
from src.mud_engine.game.models import NPC, GameObject

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NPCCreator:
    """NPC 생성 클래스"""

    def __init__(self):
        self.db_manager = None
        self.model_manager = None

    async def initialize(self):
        """의존성 초기화"""
        self.db_manager = DatabaseManager()
        await self.db_manager.initialize()

        # 데이터베이스 마이그레이션 실행
        await migrate_database(self.db_manager)

        self.model_manager = ModelManager(self.db_manager)
        logger.info("NPCCreator 초기화 완료")

    async def create_merchant_npc(self, npc_id: str, room_id: str, name_data: dict,
                                description_data: dict, dialogue_data: dict) -> bool:
        """상인 NPC 생성"""
        try:
            # 기존 NPC 확인
            existing_npc = await self.model_manager.npcs.get_by_id(npc_id)
            if existing_npc:
                logger.info(f"NPC {npc_id}가 이미 존재합니다.")
                return False

            # NPC 생성
            npc = NPC(
                id=npc_id,
                name=name_data,
                description=description_data,
                current_room_id=room_id,
                npc_type='merchant',
                dialogue=dialogue_data,
                shop_inventory=[],  # 나중에 아이템 추가
                properties={
                    'buy_rate': 0.5,  # 플레이어로부터 구매 시 원가의 50%
                    'sell_rate': 1.0  # 플레이어에게 판매 시 원가의 100%
                },
                is_active=True
            )

            await self.model_manager.npcs.create(npc.to_dict())
            logger.info(f"상인 NPC {npc_id} 생성 완료")
            return True

        except Exception as e:
            logger.error(f"상인 NPC {npc_id} 생성 실패: {e}", exc_info=True)
            return False

    async def create_shop_item(self, item_id: str, name_data: dict, description_data: dict,
                             price: int, weight: float = 1.0, category: str = 'misc') -> bool:
        """상점 아이템 생성"""
        try:
            # 기존 아이템 확인
            existing_item = await self.model_manager.game_objects.get_by_id(item_id)
            if existing_item:
                logger.info(f"아이템 {item_id}가 이미 존재합니다.")
                return False

            # 아이템 생성 (상점 템플릿용)
            item = GameObject(
                id=item_id,
                name=name_data,
                description=description_data,
                object_type='item',
                location_type='room',
                location_id='shop_template',  # 상점 템플릿 위치
                properties={
                    'price': price,
                    'shop_template': True  # 상점 템플릿 아이템임을 표시
                },
                weight=weight,
                category=category
            )

            await self.model_manager.game_objects.create(item.to_dict())
            logger.info(f"상점 아이템 {item_id} 생성 완료 (가격: {price} gold)")
            return True

        except Exception as e:
            logger.error(f"상점 아이템 {item_id} 생성 실패: {e}", exc_info=True)
            return False

    async def add_item_to_shop(self, npc_id: str, item_id: str) -> bool:
        """NPC 상점에 아이템 추가"""
        try:
            npc = await self.model_manager.npcs.get_by_id(npc_id)
            if not npc:
                logger.error(f"NPC {npc_id}를 찾을 수 없습니다.")
                return False

            if item_id not in npc.shop_inventory:
                npc.add_shop_item(item_id)
                await self.model_manager.npcs.update(npc_id, npc.to_dict())
                logger.info(f"NPC {npc_id}의 상점에 아이템 {item_id} 추가")
                return True
            else:
                logger.info(f"아이템 {item_id}가 이미 NPC {npc_id}의 상점에 있습니다.")
                return False

        except Exception as e:
            logger.error(f"상점에 아이템 추가 실패: {e}", exc_info=True)
            return False

    async def create_initial_world(self):
        """초기 NPC와 상점 시스템 생성"""
        logger.info("초기 NPC와 상점 시스템 생성 시작")

        created_count = {
            'npcs': 0,
            'items': 0,
            'shop_links': 0
        }

        try:
            # 1. 동쪽 시장 상인 NPC 생성
            merchant_created = await self.create_merchant_npc(
                npc_id="npc_merchant_east",
                room_id="room_003",  # 동쪽 시장
                name_data={
                    'en': 'Marcus the Merchant',
                    'ko': '상인 마르쿠스'
                },
                description_data={
                    'en': 'A friendly merchant with a wide selection of goods. His eyes sparkle with the promise of good deals.',
                    'ko': '다양한 상품을 판매하는 친근한 상인입니다. 그의 눈에는 좋은 거래에 대한 기대가 반짝입니다.'
                },
                dialogue_data={
                    'en': [
                        'Welcome to my shop! Take a look at my wares.',
                        'I have the finest goods in town!',
                        'Looking for something specific? Just ask!',
                        'Quality items at fair prices, that\'s my motto.',
                        'Come back anytime, friend!'
                    ],
                    'ko': [
                        '제 상점에 오신 것을 환영합니다! 상품들을 둘러보세요.',
                        '마을에서 가장 좋은 상품들을 가지고 있어요!',
                        '특별히 찾는 것이 있나요? 언제든 물어보세요!',
                        '공정한 가격의 품질 좋은 아이템, 그것이 제 신조입니다.',
                        '언제든 다시 오세요, 친구!'
                    ]
                }
            )
            if merchant_created:
                created_count['npcs'] += 1

            # 2. 기본 상점 아이템들 생성
            shop_items = [
                {
                    'id': 'item_health_potion',
                    'name': {'en': 'Health Potion', 'ko': '체력 물약'},
                    'description': {
                        'en': 'A red potion that restores health when consumed.',
                        'ko': '마시면 체력을 회복시켜주는 빨간 물약입니다.'
                    },
                    'price': 25,
                    'weight': 0.3,
                    'category': 'consumable'
                },
                {
                    'id': 'item_mana_potion',
                    'name': {'en': 'Mana Potion', 'ko': '마나 물약'},
                    'description': {
                        'en': 'A blue potion that restores magical energy.',
                        'ko': '마법 에너지를 회복시켜주는 파란 물약입니다.'
                    },
                    'price': 30,
                    'weight': 0.3,
                    'category': 'consumable'
                },
                {
                    'id': 'item_iron_sword',
                    'name': {'en': 'Iron Sword', 'ko': '철검'},
                    'description': {
                        'en': 'A sturdy iron sword with a sharp blade.',
                        'ko': '날카로운 칼날을 가진 튼튼한 철검입니다.'
                    },
                    'price': 150,
                    'weight': 2.5,
                    'category': 'weapon'
                },
                {
                    'id': 'item_leather_armor',
                    'name': {'en': 'Leather Armor', 'ko': '가죽 갑옷'},
                    'description': {
                        'en': 'Light armor made from tanned leather.',
                        'ko': '무두질한 가죽으로 만든 가벼운 갑옷입니다.'
                    },
                    'price': 100,
                    'weight': 3.0,
                    'category': 'armor'
                },
                {
                    'id': 'item_bread',
                    'name': {'en': 'Fresh Bread', 'ko': '신선한 빵'},
                    'description': {
                        'en': 'A loaf of freshly baked bread.',
                        'ko': '갓 구운 신선한 빵 한 덩어리입니다.'
                    },
                    'price': 5,
                    'weight': 0.5,
                    'category': 'consumable'
                },
                {
                    'id': 'item_torch',
                    'name': {'en': 'Torch', 'ko': '횃불'},
                    'description': {
                        'en': 'A wooden torch that provides light in dark places.',
                        'ko': '어두운 곳에서 빛을 제공하는 나무 횃불입니다.'
                    },
                    'price': 8,
                    'weight': 0.8,
                    'category': 'misc'
                }
            ]

            # 아이템 생성
            for item_data in shop_items:
                item_created = await self.create_shop_item(
                    item_id=item_data['id'],
                    name_data=item_data['name'],
                    description_data=item_data['description'],
                    price=item_data['price'],
                    weight=item_data['weight'],
                    category=item_data['category']
                )
                if item_created:
                    created_count['items'] += 1

                    # 상인의 상점에 아이템 추가
                    shop_link_created = await self.add_item_to_shop("npc_merchant_east", item_data['id'])
                    if shop_link_created:
                        created_count['shop_links'] += 1

            logger.info(f"초기 NPC와 상점 시스템 생성 완료: {created_count}")
            return created_count

        except Exception as e:
            logger.error(f"초기 NPC와 상점 시스템 생성 실패: {e}", exc_info=True)
            return created_count

    async def verify_creation(self):
        """생성 결과 검증"""
        logger.info("NPC와 상점 시스템 검증 시작")

        try:
            # NPC 확인
            merchant = await self.model_manager.npcs.get_by_id("npc_merchant_east")
            if merchant:
                logger.info(f"✓ 상인 NPC 확인: {merchant.get_localized_name('ko')} (방: {merchant.current_room_id})")
                logger.info(f"  상점 아이템 수: {len(merchant.shop_inventory)}")

                # 상점 아이템들 확인
                for item_id in merchant.shop_inventory:
                    item = await self.model_manager.game_objects.get_by_id(item_id)
                    if item:
                        price = item.get_property('price', 0)
                        logger.info(f"  - {item.get_localized_name('ko')}: {price} gold")
            else:
                logger.error("✗ 상인 NPC를 찾을 수 없습니다.")

            # 방에 NPC가 있는지 확인
            npcs_in_east_market = await self.model_manager.npcs.get_npcs_in_room("room_003")
            logger.info(f"동쪽 시장의 NPC 수: {len(npcs_in_east_market)}")

        except Exception as e:
            logger.error(f"검증 중 오류 발생: {e}", exc_info=True)

    async def cleanup(self):
        """리소스 정리"""
        if self.db_manager:
            await self.db_manager.close()
            logger.info("데이터베이스 연결 종료")


async def main():
    """메인 함수"""
    creator = NPCCreator()

    try:
        await creator.initialize()

        # 초기 NPC와 상점 시스템 생성
        result = await creator.create_initial_world()

        # 결과 검증
        await creator.verify_creation()

        print("\n=== 초기 NPC와 상점 시스템 생성 완료 ===")
        print(f"생성된 NPC: {result['npcs']}개")
        print(f"생성된 상점 아이템: {result['items']}개")
        print(f"상점 연결: {result['shop_links']}개")
        print("\n게임에서 다음 명령어를 사용해보세요:")
        print("- talk marcus (상인과 대화)")
        print("- shop (상점 목록 보기)")
        print("- buy bread (빵 구매)")
        print("- sell <아이템> (아이템 판매)")

    except Exception as e:
        logger.error(f"스크립트 실행 중 오류: {e}", exc_info=True)
        return 1
    finally:
        await creator.cleanup()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)