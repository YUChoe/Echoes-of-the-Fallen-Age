#!/usr/bin/env python3
"""
기본 몬스터 데이터 생성 스크립트
"""

import asyncio
import logging
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.mud_engine.database.connection import DatabaseManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_basic_monsters():
    """기본 몬스터 데이터 생성"""

    # 데이터베이스 연결
    db_manager = DatabaseManager()
    await db_manager.initialize()

    try:
        # 필요한 클래스들을 함수 내에서 import하여 순환 import 방지
        from src.mud_engine.game.monster import Monster, MonsterType, MonsterBehavior, MonsterStats, DropItem
        from src.mud_engine.game.repositories import MonsterRepository

        monster_repo = MonsterRepository(db_manager)
        # 기본 몬스터 데이터 정의
        monsters_data = [
            {
                'id': 'monster_slime_001',
                'name': {'en': 'Green Slime', 'ko': '초록 슬라임'},
                'description': {
                    'en': 'A small, gelatinous creature that bounces around harmlessly.',
                    'ko': '작고 젤리 같은 생물로 무해하게 통통 튀어다닙니다.'
                },
                'monster_type': MonsterType.PASSIVE,
                'behavior': MonsterBehavior.STATIONARY,
                'stats': MonsterStats(
                    max_hp=30,
                    current_hp=30,
                    attack_power=5,
                    defense=2,
                    speed=5,
                    accuracy=70,
                    critical_chance=2
                ),
                'experience_reward': 25,
                'gold_reward': 5,
                'drop_items': [
                    DropItem('item_slime_gel', 0.8, 1, 2),  # 80% 확률로 슬라임 젤 1-2개
                    DropItem('item_small_potion', 0.2, 1, 1)  # 20% 확률로 작은 포션 1개
                ],
                'respawn_time': 180,  # 3분
                'aggro_range': 0,
                'roaming_range': 0
            },
            {
                'id': 'monster_goblin_001',
                'name': {'en': 'Goblin Warrior', 'ko': '고블린 전사'},
                'description': {
                    'en': 'A small but fierce goblin armed with a rusty dagger.',
                    'ko': '작지만 사나운 고블린으로 녹슨 단검을 들고 있습니다.'
                },
                'monster_type': MonsterType.AGGRESSIVE,
                'behavior': MonsterBehavior.ROAMING,
                'stats': MonsterStats(
                    max_hp=60,
                    current_hp=60,
                    attack_power=12,
                    defense=5,
                    speed=15,
                    accuracy=75,
                    critical_chance=8
                ),
                'experience_reward': 50,
                'gold_reward': 15,
                'drop_items': [
                    DropItem('item_rusty_dagger', 0.3, 1, 1),  # 30% 확률로 녹슨 단검
                    DropItem('item_goblin_ear', 0.9, 1, 1),   # 90% 확률로 고블린 귀
                    DropItem('item_small_potion', 0.4, 1, 1)  # 40% 확률로 작은 포션
                ],
                'respawn_time': 300,  # 5분
                'aggro_range': 1,
                'roaming_range': 2
            },
            {
                'id': 'monster_wolf_001',
                'name': {'en': 'Forest Wolf', 'ko': '숲늑대'},
                'description': {
                    'en': 'A wild wolf with sharp fangs and keen senses.',
                    'ko': '날카로운 송곳니와 예리한 감각을 가진 야생 늑대입니다.'
                },
                'monster_type': MonsterType.AGGRESSIVE,
                'behavior': MonsterBehavior.TERRITORIAL,
                'stats': MonsterStats(
                    max_hp=80,
                    current_hp=80,
                    attack_power=18,
                    defense=8,
                    speed=20,
                    accuracy=85,
                    critical_chance=12
                ),
                'experience_reward': 75,
                'gold_reward': 20,
                'drop_items': [
                    DropItem('item_wolf_pelt', 0.7, 1, 1),    # 70% 확률로 늑대 가죽
                    DropItem('item_wolf_fang', 0.5, 1, 2),   # 50% 확률로 늑대 송곳니 1-2개
                    DropItem('item_meat', 0.8, 2, 4)         # 80% 확률로 고기 2-4개
                ],
                'respawn_time': 600,  # 10분
                'aggro_range': 1,
                'roaming_range': 3
            },
            {
                'id': 'monster_rabbit_001',
                'name': {'en': 'Forest Rabbit', 'ko': '숲토끼'},
                'description': {
                    'en': 'A cute, fluffy rabbit that hops around the forest.',
                    'ko': '숲을 뛰어다니는 귀엽고 털복숭이인 토끼입니다.'
                },
                'monster_type': MonsterType.NEUTRAL,
                'behavior': MonsterBehavior.ROAMING,
                'stats': MonsterStats(
                    max_hp=15,
                    current_hp=15,
                    attack_power=2,
                    defense=1,
                    speed=25,
                    accuracy=60,
                    critical_chance=1
                ),
                'experience_reward': 10,
                'gold_reward': 2,
                'drop_items': [
                    DropItem('item_rabbit_fur', 0.6, 1, 1),   # 60% 확률로 토끼 털
                    DropItem('item_carrot', 0.3, 1, 1)       # 30% 확률로 당근
                ],
                'respawn_time': 120,  # 2분
                'aggro_range': 0,
                'roaming_range': 2
            },
            {
                'id': 'monster_orc_001',
                'name': {'en': 'Orc Brute', 'ko': '오크 야만전사'},
                'description': {
                    'en': 'A large, brutish orc wielding a massive club.',
                    'ko': '거대한 곤봉을 휘두르는 크고 야만적인 오크입니다.'
                },
                'monster_type': MonsterType.AGGRESSIVE,
                'behavior': MonsterBehavior.TERRITORIAL,
                'stats': MonsterStats(
                    max_hp=150,
                    current_hp=150,
                    attack_power=25,
                    defense=12,
                    speed=8,
                    accuracy=70,
                    critical_chance=15
                ),
                'experience_reward': 120,
                'gold_reward': 35,
                'drop_items': [
                    DropItem('item_orc_club', 0.4, 1, 1),    # 40% 확률로 오크 곤봉
                    DropItem('item_orc_tooth', 0.8, 1, 2),  # 80% 확률로 오크 이빨 1-2개
                    DropItem('item_health_potion', 0.3, 1, 1) # 30% 확률로 체력 포션
                ],
                'respawn_time': 900,  # 15분
                'aggro_range': 1,
                'roaming_range': 2
            }
        ]

        # 몬스터 생성
        created_count = 0
        for monster_data in monsters_data:
            # 이미 존재하는지 확인
            existing = await monster_repo.get_by_id(monster_data['id'])
            if existing:
                logger.info(f"몬스터 {monster_data['id']} 이미 존재함")
                continue

            # Monster 객체 생성
            monster = Monster(**monster_data)

            # 데이터베이스에 저장
            success = await monster_repo.create(monster)
            if success:
                created_count += 1
                logger.info(f"몬스터 생성 완료: {monster.get_localized_name('ko')} ({monster.id})")
            else:
                logger.error(f"몬스터 생성 실패: {monster.id}")

        logger.info(f"기본 몬스터 생성 완료: {created_count}마리")

        # 생성된 몬스터 목록 확인
        all_monsters = await monster_repo.get_all()
        logger.info(f"전체 몬스터 수: {len(all_monsters)}마리")

        for monster in all_monsters:
            logger.info(f"- {monster.get_localized_name('ko')} ({monster.monster_type.value}, {monster.behavior.value})")

    except Exception as e:
        logger.error(f"몬스터 생성 중 오류 발생: {e}")
        raise

    finally:
        await db_manager.close()


async def main():
    """메인 함수"""
    logger.info("기본 몬스터 데이터 생성 시작")

    try:
        await create_basic_monsters()
        logger.info("기본 몬스터 데이터 생성 완료")

    except Exception as e:
        logger.error(f"스크립트 실행 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())