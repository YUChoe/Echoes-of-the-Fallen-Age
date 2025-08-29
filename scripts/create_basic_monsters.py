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
from src.mud_engine.game.repositories import MonsterRepository
from src.mud_engine.game.monster import Monster, MonsterType, MonsterBehavior, MonsterStats, DropItem

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_basic_monsters():
    """기본 몬스터 데이터를 생성합니다."""

    # 데이터베이스 연결
    db_manager = DatabaseManager()
    await db_manager.initialize()

    monster_repo = MonsterRepository(db_manager)

    try:
        # 1. 슬라임 템플릿
        slime_template = Monster(
            id='slime_template',
            name={
                'en': 'Green Slime',
                'ko': '초록 슬라임'
            },
            description={
                'en': 'A small, bouncy green slime. It looks harmless but can be surprisingly resilient.',
                'ko': '작고 통통 튀는 초록색 슬라임입니다. 무해해 보이지만 의외로 끈질깁니다.'
            },
            monster_type=MonsterType.PASSIVE,
            behavior=MonsterBehavior.STATIONARY,
            stats=MonsterStats(
                max_hp=50,
                current_hp=50,
                attack_power=8,
                defense=2,
                speed=5,
                accuracy=70,
                critical_chance=2
            ),
            experience_reward=25,
            gold_reward=5,
            drop_items=[
                DropItem('slime_gel', 0.8, 1, 2),  # 슬라임 젤 80% 확률로 1-2개
                DropItem('healing_potion_small', 0.1, 1, 1)  # 소형 치료 포션 10% 확률
            ],
            respawn_time=180,  # 3분
            aggro_range=0,  # 후공형이므로 어그로 범위 0
            roaming_range=0,  # 고정형
            properties={
                'is_template': True,
                'difficulty': 'easy',
                'habitat': 'forest'
            }
        )

        # 기존 슬라임 템플릿이 있는지 확인
        existing_slime = await monster_repo.get_by_id('slime_template')
        if existing_slime:
            logger.info("슬라임 템플릿이 이미 존재합니다")
        else:
            await monster_repo.create(slime_template.to_dict())
            logger.info("슬라임 템플릿 생성 완료")

        # 2. 고블린 템플릿
        goblin_template = Monster(
            id='goblin_template',
            name={
                'en': 'Wild Goblin',
                'ko': '야생 고블린'
            },
            description={
                'en': 'A small, aggressive goblin with sharp claws and a nasty temper. It attacks on sight.',
                'ko': '날카로운 발톱과 사나운 성격을 가진 작은 고블린입니다. 보이는 즉시 공격합니다.'
            },
            monster_type=MonsterType.AGGRESSIVE,
            behavior=MonsterBehavior.ROAMING,
            stats=MonsterStats(
                max_hp=80,
                current_hp=80,
                attack_power=15,
                defense=5,
                speed=12,
                accuracy=75,
                critical_chance=8
            ),
            experience_reward=50,
            gold_reward=12,
            drop_items=[
                DropItem('goblin_claw', 0.6, 1, 1),  # 고블린 발톱 60% 확률
                DropItem('rusty_dagger', 0.15, 1, 1),  # 녹슨 단검 15% 확률
                DropItem('copper_coin', 0.9, 3, 8)  # 구리 동전 90% 확률로 3-8개
            ],
            respawn_time=300,  # 5분
            aggro_range=1,  # 선공형이므로 어그로 범위 1
            roaming_range=2,  # 로밍 범위 2
            properties={
                'is_template': True,
                'difficulty': 'normal',
                'habitat': 'forest'
            }
        )

        # 기존 고블린 템플릿이 있는지 확인
        existing_goblin = await monster_repo.get_by_id('goblin_template')
        if existing_goblin:
            logger.info("고블린 템플릿이 이미 존재합니다")
        else:
            await monster_repo.create(goblin_template.to_dict())
            logger.info("고블린 템플릿 생성 완료")

        # 3. 늑대 템플릿
        wolf_template = Monster(
            id='wolf_template',
            name={
                'en': 'Forest Wolf',
                'ko': '숲 늑대'
            },
            description={
                'en': 'A fierce forest wolf with glowing yellow eyes. It hunts in packs and is very territorial.',
                'ko': '노란 눈이 빛나는 사나운 숲 늑대입니다. 무리를 지어 사냥하며 영역 의식이 강합니다.'
            },
            monster_type=MonsterType.AGGRESSIVE,
            behavior=MonsterBehavior.TERRITORIAL,
            stats=MonsterStats(
                max_hp=120,
                current_hp=120,
                attack_power=22,
                defense=8,
                speed=18,
                accuracy=85,
                critical_chance=12
            ),
            experience_reward=80,
            gold_reward=20,
            drop_items=[
                DropItem('wolf_pelt', 0.7, 1, 1),  # 늑대 가죽 70% 확률
                DropItem('wolf_fang', 0.4, 1, 2),  # 늑대 송곳니 40% 확률로 1-2개
                DropItem('raw_meat', 0.8, 2, 4)  # 생고기 80% 확률로 2-4개
            ],
            respawn_time=600,  # 10분
            aggro_range=2,  # 넓은 어그로 범위
            roaming_range=3,  # 넓은 로밍 범위
            properties={
                'is_template': True,
                'difficulty': 'hard',
                'habitat': 'forest',
                'pack_hunter': True
            }
        )

        # 기존 늑대 템플릿이 있는지 확인
        existing_wolf = await monster_repo.get_by_id('wolf_template')
        if existing_wolf:
            logger.info("늑대 템플릿이 이미 존재합니다")
        else:
            await monster_repo.create(wolf_template.to_dict())
            logger.info("늑대 템플릿 생성 완료")

        logger.info("모든 기본 몬스터 템플릿 생성 완료")

    except Exception as e:
        logger.error(f"몬스터 생성 실패: {e}")
        raise

    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(create_basic_monsters())