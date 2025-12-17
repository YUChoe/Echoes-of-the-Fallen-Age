#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
튜토리얼 환경 설정 스크립트
교회, 수도사 NPC, 기본 아이템 등을 생성합니다.
"""

import asyncio
import logging
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mud_engine.database import get_database_manager
from src.mud_engine.game.repositories import RoomRepository, NPCRepository, GameObjectRepository
from src.mud_engine.game.models import Room, NPC, GameObject

logger = logging.getLogger(__name__)


async def setup_tutorial_environment():
    """튜토리얼 환경 설정"""
    logger.info("튜토리얼 환경 설정 시작")

    db_manager = None
    try:
        # 데이터베이스 매니저 초기화
        db_manager = await get_database_manager()

        # 리포지토리 초기화
        room_repo = RoomRepository(db_manager)
        npc_repo = NPCRepository(db_manager)
        object_repo = GameObjectRepository(db_manager)

        # 1. 교회 방 생성 (1, 0 좌표)
        church_room = Room(
            id="church_1_0",
            description={
                "en": "A peaceful church with stained glass windows. A monk stands near the altar.",
                "ko": "스테인드글라스 창문이 있는 평화로운 교회입니다. 제단 근처에 수도사가 서 있습니다."
            },
            exits={"west": "town_square"},
            x=1,
            y=0
        )

        # 교회 방이 이미 존재하는지 확인
        existing_church = await room_repo.get_by_id("church_1_0")
        if not existing_church:
            await room_repo.create(church_room.to_dict())
            logger.info("교회 방 생성됨: church_1_0")
        else:
            logger.info("교회 방이 이미 존재함: church_1_0")

        # 2. 마을 광장에서 교회로 가는 출구 추가
        town_square = await room_repo.get_by_id("town_square")
        if town_square:
            exits = town_square.exits if isinstance(town_square.exits, dict) else {}
            exits["east"] = "church_1_0"
            await room_repo.update("town_square", {"exits": exits})
            logger.info("마을 광장에 교회로 가는 출구 추가됨")

        # 3. 교회 수도사 NPC 생성
        church_monk = NPC(
            id="church_monk",
            name={"en": "Church Monk", "ko": "교회 수도사"},
            description={
                "en": "A wise monk in brown robes. He seems to have something important to tell new adventurers.",
                "ko": "갈색 로브를 입은 지혜로운 수도사입니다. 새로운 모험가들에게 중요한 이야기가 있는 것 같습니다."
            },
            current_room_id="church_1_0",
            npc_type="quest_giver",
            dialogue={
                "en": [
                    "Welcome to the church, young adventurer.",
                    "I can provide you with basic equipment to start your journey.",
                    "But first, you must prove your dedication by collecting 10 Essence of Life.",
                    "These essences can be found by defeating monsters in the wilderness.",
                    "Return to me when you have collected them all."
                ],
                "ko": [
                    "교회에 오신 것을 환영합니다, 젊은 모험가여.",
                    "여행을 시작할 수 있도록 기본 장비를 제공해드릴 수 있습니다.",
                    "하지만 먼저 생명의 정수 10개를 수집하여 당신의 헌신을 증명해야 합니다.",
                    "이 정수들은 야생의 몬스터들을 처치하면 얻을 수 있습니다.",
                    "모두 수집하면 저에게 돌아오세요."
                ]
            }
        )

        # 수도사 NPC가 이미 존재하는지 확인
        existing_monk = await npc_repo.get_by_id("church_monk")
        if not existing_monk:
            await npc_repo.create(church_monk.to_dict())
            logger.info("교회 수도사 NPC 생성됨: church_monk")
        else:
            logger.info("교회 수도사 NPC가 이미 존재함: church_monk")

        # 4. 기본 장비 아이템 템플릿 생성
        basic_items = [
            GameObject(
                id="tutorial_club",
                name={"en": "Wooden Club", "ko": "나무 곤봉"},
                description={
                    "en": "A simple wooden club for beginners.",
                    "ko": "초보자를 위한 간단한 나무 곤봉입니다."
                },
                object_type="item",
                equipment_slot="right_hand",
                properties={"stats_bonus": {"ATK": 5}},
                location_type="room",
                location_id="template_storage"
            ),
            GameObject(
                id="tutorial_linen_shirt",
                name={"en": "Linen Shirt", "ko": "리넨 상의"},
                description={
                    "en": "A basic linen shirt for protection.",
                    "ko": "보호를 위한 기본 리넨 상의입니다."
                },
                object_type="item",
                equipment_slot="chest",
                properties={"stats_bonus": {"DEF": 2}},
                location_type="room",
                location_id="template_storage"
            ),
            GameObject(
                id="tutorial_linen_pants",
                name={"en": "Linen Pants", "ko": "리넨 하의"},
                description={
                    "en": "Basic linen pants for adventurers.",
                    "ko": "모험가를 위한 기본 리넨 하의입니다."
                },
                object_type="item",
                equipment_slot="legs",
                properties={"stats_bonus": {"DEF": 1}},
                location_type="room",
                location_id="template_storage"
            )
        ]

        for item in basic_items:
            existing_item = await object_repo.get_by_id(item.id)
            if not existing_item:
                await object_repo.create(item.to_dict())
                logger.info(f"기본 장비 아이템 생성됨: {item.id}")
            else:
                logger.info(f"기본 장비 아이템이 이미 존재함: {item.id}")

        # 5. 생명의 정수 아이템 생성
        essence_item = GameObject(
            id="essence_of_life_template",
            name={"en": "Essence of Life", "ko": "생명의 정수"},
            description={
                "en": "A glowing essence that contains the power of life.",
                "ko": "생명의 힘이 담긴 빛나는 정수입니다."
            },
            object_type="item",
            category="consumable",
            location_type="room",
            location_id="template_storage",
            properties={"stackable": True, "max_stack": 99}
        )

        existing_essence = await object_repo.get_by_id("essence_of_life_template")
        if not existing_essence:
            await object_repo.create(essence_item.to_dict())
            logger.info("생명의 정수 템플릿 생성됨: essence_of_life_template")
        else:
            logger.info("생명의 정수 템플릿이 이미 존재함: essence_of_life_template")

        logger.info("튜토리얼 환경 설정 완료")
        return True

    except Exception as e:
        logger.error(f"튜토리얼 환경 설정 실패: {e}")
        return False
    finally:
        # 데이터베이스 연결 정리
        if db_manager:
            try:
                await db_manager.close()
                logger.info("데이터베이스 연결 종료")
            except Exception as e:
                logger.error(f"데이터베이스 연결 종료 실패: {e}")


async def main():
    """메인 함수"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("튜토리얼 설정 스크립트 시작")

    success = await setup_tutorial_environment()

    if success:
        logger.info("튜토리얼 환경 설정이 성공적으로 완료되었습니다.")
    else:
        logger.error("튜토리얼 환경 설정에 실패했습니다.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())