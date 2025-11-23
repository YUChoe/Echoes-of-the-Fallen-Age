#!/usr/bin/env python3
"""
전투 테스트 환경 구축 스크립트
- 서쪽 게이트 밖 테스트 지역 생성
- 공격적인 고블린 배치
- 플레이어 입장 시 자동 전투 시작 테스트
"""

import asyncio
import sys
import os
import logging

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.mud_engine.database.connection import DatabaseManager
from src.mud_engine.game.models import Room
from src.mud_engine.game.repositories import RoomRepository, MonsterRepository
from src.mud_engine.game.monster import Monster, MonsterType, MonsterBehavior, MonsterStats, DropItem

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CombatTestAreaCreator:
    """전투 테스트 지역 생성 클래스"""

    def __init__(self):
        self.db_manager = None
        self.room_repo = None
        self.monster_repo = None

    async def initialize(self):
        """데이터베이스 매니저 초기화"""
        self.db_manager = DatabaseManager()
        await self.db_manager.initialize()
        self.room_repo = RoomRepository(self.db_manager)
        self.monster_repo = MonsterRepository(self.db_manager)

    async def create_test_area_outside_gate(self):
        """서쪽 게이트 밖 테스트 지역 생성"""
        logger.info("서쪽 게이트 밖 테스트 지역 생성 중...")

        # 테스트 지역 방 ID
        test_area_id = "test_combat_area"

        # 기존 테스트 지역 확인
        existing_area = await self.room_repo.get_by_id(test_area_id)
        if existing_area:
            logger.info("테스트 지역이 이미 존재합니다.")
        else:
            # 테스트 지역 방 생성
            test_area = Room(
                id=test_area_id,
                name={
                    "en": "Goblin Ambush Point",
                    "ko": "고블린 매복 지점"
                },
                description={
                    "en": "A dangerous clearing just outside the west gate. The ground is littered with bones and broken weapons. Several aggressive goblins lurk here, ready to attack any intruders.",
                    "ko": "서쪽 성문 바로 밖의 위험한 공터입니다. 땅에는 뼈와 부서진 무기들이 흩어져 있습니다. 여러 마리의 공격적인 고블린들이 이곳에 숨어 있으며, 침입자를 공격할 준비가 되어 있습니다."
                },
                exits={
                    "east": "room_gate_west"  # 성문으로 돌아가는 출구
                }
            )

            # 데이터베이스에 저장
            await self.room_repo.create(test_area.to_dict())
            logger.info(f"테스트 지역 생성 완료: {test_area_id}")

        # 서쪽 성문에 테스트 지역으로 가는 출구 추가
        gate = await self.room_repo.get_by_id("room_gate_west")
        if gate:
            import json
            exits = gate.exits if isinstance(gate.exits, dict) else json.loads(gate.exits)
            if "west" not in exits or exits["west"] != test_area_id:
                exits["west"] = test_area_id
                await self.room_repo.update("room_gate_west", {"exits": exits})
                logger.info("서쪽 성문에 테스트 지역 출구 추가 완료")

        logger.info("서쪽 게이트 밖 테스트 지역 생성 완료")

    async def create_aggressive_goblins(self):
        """공격적인 고블린 배치"""
        logger.info("공격적인 고블린 배치 중...")

        # 테스트 지역에 배치할 고블린 인스턴스들
        goblin_instances = [
            {
                "id": "goblin_test_1",
                "name_suffix": "Alpha",
                "name_suffix_ko": "알파"
            },
            {
                "id": "goblin_test_2",
                "name_suffix": "Beta",
                "name_suffix_ko": "베타"
            },
            {
                "id": "goblin_test_3",
                "name_suffix": "Gamma",
                "name_suffix_ko": "감마"
            }
        ]

        created_count = 0
        for goblin_data in goblin_instances:
            # 기존 고블린 확인
            existing_goblin = await self.monster_repo.get_by_id(goblin_data["id"])
            if existing_goblin:
                logger.info(f"고블린 {goblin_data['id']}이(가) 이미 존재합니다")
                continue

            # 공격적인 고블린 생성
            goblin = Monster(
                id=goblin_data["id"],
                name={
                    'en': f"Aggressive Goblin {goblin_data['name_suffix']}",
                    'ko': f"공격적인 고블린 {goblin_data['name_suffix_ko']}"
                },
                description={
                    'en': f"A particularly vicious goblin with bloodshot eyes and sharp claws. It attacks anyone who enters its territory without hesitation.",
                    'ko': f"충혈된 눈과 날카로운 발톱을 가진 특히 사나운 고블린입니다. 자신의 영역에 들어오는 모든 이를 주저 없이 공격합니다."
                },
                monster_type=MonsterType.AGGRESSIVE,  # 공격적 타입
                behavior=MonsterBehavior.STATIONARY,  # 고정형 (테스트 지역에 고정)
                stats=MonsterStats(
                    max_hp=100,
                    current_hp=100,
                    attack_power=18,
                    defense=6,
                    speed=14,
                    accuracy=78,
                    critical_chance=10
                ),
                experience_reward=60,
                gold_reward=15,
                drop_items=[
                    DropItem('goblin_claw', 0.7, 1, 2),
                    DropItem('rusty_dagger', 0.2, 1, 1),
                    DropItem('copper_coin', 0.95, 5, 12)
                ],
                respawn_time=300,  # 5분
                aggro_range=1,  # 선공형이므로 어그로 범위 1
                roaming_range=0,  # 고정형이므로 로밍 안함
                current_room_id="test_combat_area",  # 테스트 지역에 배치
                properties={
                    'is_test_monster': True,
                    'difficulty': 'normal',
                    'habitat': 'test_area',
                    'aggressive_on_sight': True
                }
            )

            # 데이터베이스에 저장
            await self.monster_repo.create(goblin.to_dict())
            created_count += 1
            logger.info(f"공격적인 고블린 생성 완료: {goblin_data['id']}")

        logger.info(f"새로 생성된 공격적인 고블린: {created_count}개")
        logger.info("공격적인 고블린 배치 완료")

    async def verify_test_area(self):
        """테스트 지역 검증"""
        logger.info("\n=== 전투 테스트 환경 검증 ===")

        # 테스트 지역 확인
        test_area = await self.room_repo.get_by_id("test_combat_area")
        if test_area:
            logger.info("✓ 테스트 지역 생성 확인")
        else:
            logger.error("✗ 테스트 지역 생성 실패")
            return

        # 서쪽 성문 출구 확인
        gate = await self.room_repo.get_by_id("room_gate_west")
        if gate:
            import json
            exits = gate.exits if isinstance(gate.exits, dict) else json.loads(gate.exits)
            if 'west' in exits and exits['west'] == 'test_combat_area':
                logger.info("✓ 서쪽 성문에서 테스트 지역으로 가는 출구 확인")
            else:
                logger.error("✗ 서쪽 성문 출구 설정 실패")

        # 고블린 배치 확인
        goblin_count = 0
        for i in range(1, 4):
            goblin_id = f"goblin_test_{i}"
            goblin = await self.monster_repo.get_by_id(goblin_id)
            if goblin:
                goblin_count += 1
                # 공격적 타입 확인
                if goblin.monster_type == MonsterType.AGGRESSIVE:
                    logger.info(f"✓ 공격적인 고블린 {goblin_id} 확인 (타입: AGGRESSIVE)")
                else:
                    logger.warning(f"⚠ 고블린 {goblin_id}의 타입이 AGGRESSIVE가 아닙니다")

                # 위치 확인
                if goblin.current_room_id == "test_combat_area":
                    logger.info(f"✓ 고블린 {goblin_id} 위치 확인 (test_combat_area)")
                else:
                    logger.warning(f"⚠ 고블린 {goblin_id}의 위치가 올바르지 않습니다")

        logger.info(f"✓ 공격적인 고블린 배치 확인: {goblin_count}/3개")

        logger.info("\n=== 테스트 방법 ===")
        logger.info("1. 게임에 로그인합니다")
        logger.info("2. 마을 광장(room_001)에서 'west' 명령으로 서쪽 성문으로 이동합니다")
        logger.info("3. 서쪽 성문(room_gate_west)에서 'west' 명령으로 테스트 지역으로 이동합니다")
        logger.info("4. 테스트 지역(test_combat_area)에 입장하면 공격적인 고블린들이 자동으로 전투를 시작합니다")
        logger.info("5. 전투 시스템이 정상적으로 작동하는지 확인합니다")

    async def close(self):
        """리소스 정리"""
        if self.db_manager:
            await self.db_manager.close()


async def main():
    """메인 실행 함수"""
    logger.info("=== 전투 테스트 환경 구축 시작 ===")

    creator = CombatTestAreaCreator()

    try:
        await creator.initialize()

        # 1. 서쪽 게이트 밖 테스트 지역 생성
        await creator.create_test_area_outside_gate()

        # 2. 공격적인 고블린 배치
        await creator.create_aggressive_goblins()

        # 3. 테스트 환경 검증
        await creator.verify_test_area()

        logger.info("\n=== 전투 테스트 환경 구축 완료 ===")

    except Exception as e:
        logger.error(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await creator.close()


if __name__ == "__main__":
    asyncio.run(main())
