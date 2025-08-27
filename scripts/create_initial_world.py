#!/usr/bin/env python3
"""
초기 월드 구성 스크립트
- 마을 광장 서쪽에 성문 추가
- 8x8 숲 지역 생성
- 방향 연결 시스템 구성
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.mud_engine.database.connection import DatabaseManager
from src.mud_engine.game.models import Room
from src.mud_engine.game.repositories import RoomRepository, GameObjectRepository


class WorldCreator:
    """초기 월드 생성 클래스"""

    def __init__(self):
        self.db_manager = None
        self.room_repo = None
        self.object_repo = None

    async def initialize(self):
        """데이터베이스 매니저 초기화"""
        self.db_manager = DatabaseManager()
        await self.db_manager.initialize()
        self.room_repo = RoomRepository(self.db_manager)
        self.object_repo = GameObjectRepository(self.db_manager)

    async def create_west_gate(self):
        """마을 광장 서쪽에 성문 생성"""
        print("서쪽 성문 생성 중...")

        # 기존 성문 확인
        existing_gate = await self.room_repo.get_by_id("room_gate_west")
        if existing_gate:
            print("서쪽 성문이 이미 존재합니다.")
        else:
            # 성문 방 생성
            gate_room = Room(
                id="room_gate_west",
                name={"en": "West Gate", "ko": "서쪽 성문"},
                description={"en": "A massive stone gate leading west from the town. Ancient runes are carved into the archway, and two guards stand watch.", "ko": "마을에서 서쪽으로 이어지는 거대한 석조 성문입니다. 아치에는 고대 룬이 새겨져 있고, 두 명의 경비병이 지키고 있습니다."},
                exits={"east": "room_001", "west": "forest_0_0"}
            )

            # 데이터베이스에 저장
            await self.room_repo.create(gate_room.to_dict())

        # 마을 광장에 서쪽 출구 추가
        town_square = await self.room_repo.get_by_id("room_001")
        if town_square:
            exits = json.loads(town_square.exits if isinstance(town_square.exits, str) else json.dumps(town_square.exits))
            exits["west"] = "room_gate_west"
            await self.room_repo.update("room_001", {"exits": exits})
            print("마을 광장에 서쪽 출구 추가 완료")

        print("서쪽 성문 생성 완료")

    async def create_forest_region(self):
        """8x8 숲 지역 생성"""
        print("8x8 숲 지역 생성 중...")

        forest_descriptions = [
            {
                "en": "A dense forest with towering oak trees. Sunlight filters through the canopy above.",
                "ko": "우뚝 솟은 참나무들이 빽빽한 숲입니다. 위쪽 나뭇잎 사이로 햇빛이 스며듭니다."
            },
            {
                "en": "A quiet grove surrounded by birch trees. The ground is covered with fallen leaves.",
                "ko": "자작나무들로 둘러싸인 조용한 숲속 공터입니다. 땅은 낙엽으로 덮여 있습니다."
            },
            {
                "en": "A mysterious part of the forest where ancient pine trees grow. The air feels cool and fresh.",
                "ko": "고대 소나무들이 자라는 신비로운 숲의 한 부분입니다. 공기가 시원하고 상쾌합니다."
            },
            {
                "en": "A small clearing in the forest with wildflowers blooming. Butterflies dance in the air.",
                "ko": "야생화가 피어있는 숲속의 작은 공터입니다. 나비들이 공중에서 춤을 춥니다."
            },
            {
                "en": "A darker part of the forest where the trees grow thick. Strange sounds echo from deeper within.",
                "ko": "나무들이 빽빽하게 자란 숲의 어두운 부분입니다. 더 깊은 곳에서 이상한 소리가 울려옵니다."
            },
            {
                "en": "A rocky area in the forest with moss-covered boulders. A small stream trickles nearby.",
                "ko": "이끼로 덮인 바위들이 있는 숲의 바위 지역입니다. 근처에서 작은 개울이 졸졸 흐릅니다."
            },
            {
                "en": "A peaceful spot where old willow trees bend over a small pond. Frogs croak softly.",
                "ko": "오래된 버드나무들이 작은 연못 위로 구부러진 평화로운 장소입니다. 개구리들이 부드럽게 울고 있습니다."
            },
            {
                "en": "A thorny thicket blocks much of the path here. Careful navigation is required.",
                "ko": "가시덤불이 길의 대부분을 막고 있습니다. 조심스러운 이동이 필요합니다."
            }
        ]

        # 8x8 격자로 숲 방들 생성
        created_count = 0
        for x in range(8):
            for y in range(8):
                room_id = f"forest_{x}_{y}"

                # 기존 방 확인
                existing_room = await self.room_repo.get_by_id(room_id)
                if existing_room:
                    continue

                # 설명 선택 (위치에 따라 다양하게)
                desc_index = (x + y) % len(forest_descriptions)
                desc = forest_descriptions[desc_index]

                # 출구 계산
                exits = {}

                # 북쪽 출구 (y > 0)
                if y > 0:
                    exits["north"] = f"forest_{x}_{y-1}"

                # 남쪽 출구 (y < 7)
                if y < 7:
                    exits["south"] = f"forest_{x}_{y+1}"

                # 서쪽 출구 (x > 0)
                if x > 0:
                    exits["west"] = f"forest_{x-1}_{y}"

                # 동쪽 출구 (x < 7)
                if x < 7:
                    exits["east"] = f"forest_{x+1}_{y}"

                # 성문으로의 연결 (0,0 위치)
                if x == 0 and y == 0:
                    exits["east"] = "room_gate_west"

                # 방 생성
                forest_room = Room(
                    id=room_id,
                    name={"en": f"Forest ({x},{y})", "ko": f"숲 ({x},{y})"},
                    description={"en": desc["en"], "ko": desc["ko"]},
                    exits=exits
                )

                # 데이터베이스에 저장
                await self.room_repo.create(forest_room.to_dict())
                created_count += 1

        print(f"새로 생성된 숲 방: {created_count}개")

        print("8x8 숲 지역 생성 완료")

    async def create_forest_objects(self):
        """숲 지역에 기본 게임 객체 배치"""
        print("숲 지역 게임 객체 배치 중...")

        forest_objects = [
            {
                "id": "obj_oak_branch",
                "name_en": "Oak Branch",
                "name_ko": "참나무 가지",
                "description_en": "A sturdy oak branch that fell from a tree. It could be useful as a walking stick.",
                "description_ko": "나무에서 떨어진 튼튼한 참나무 가지입니다. 지팡이로 사용할 수 있을 것 같습니다.",
                "object_type": "item",
                "location_type": "room",
                "location_id": "forest_1_1",
                "weight": 2.0,
                "category": "misc"
            },
            {
                "id": "obj_wild_berries",
                "name_en": "Wild Berries",
                "name_ko": "야생 베리",
                "description_en": "A cluster of sweet wild berries. They look safe to eat.",
                "description_ko": "달콤한 야생 베리 송이입니다. 먹어도 안전해 보입니다.",
                "object_type": "consumable",
                "location_type": "room",
                "location_id": "forest_2_3",
                "weight": 0.5,
                "category": "consumable"
            },
            {
                "id": "obj_smooth_stone",
                "name_en": "Smooth Stone",
                "name_ko": "매끄러운 돌",
                "description_en": "A perfectly smooth stone worn by water. It fits nicely in your palm.",
                "description_ko": "물에 의해 매끄럽게 다듬어진 완벽한 돌입니다. 손바닥에 잘 맞습니다.",
                "object_type": "item",
                "location_type": "room",
                "location_id": "forest_5_2",
                "weight": 1.0,
                "category": "misc"
            },
            {
                "id": "obj_mushroom",
                "name_en": "Forest Mushroom",
                "name_ko": "숲 버섯",
                "description_en": "A large mushroom growing near a tree stump. You're not sure if it's edible.",
                "description_ko": "나무 그루터기 근처에서 자라는 큰 버섯입니다. 먹을 수 있는지 확실하지 않습니다.",
                "object_type": "item",
                "location_type": "room",
                "location_id": "forest_3_5",
                "weight": 0.3,
                "category": "misc"
            },
            {
                "id": "obj_flower_crown",
                "name_en": "Wildflower Crown",
                "name_ko": "야생화 화관",
                "description_en": "A beautiful crown made of woven wildflowers. Someone must have dropped it.",
                "description_ko": "야생화로 엮어 만든 아름다운 화관입니다. 누군가 떨어뜨린 것 같습니다.",
                "object_type": "item",
                "location_type": "room",
                "location_id": "forest_6_4",
                "weight": 0.2,
                "category": "misc",
                "equipment_slot": "accessory"
            }
        ]

        # 객체들을 데이터베이스에 저장
        created_objects = 0
        for obj_data in forest_objects:
            # 기존 객체 확인
            existing_obj = await self.object_repo.get_by_id(obj_data["id"])
            if existing_obj:
                continue

            await self.object_repo.create(obj_data)
            created_objects += 1

        print(f"새로 생성된 숲 객체: {created_objects}개")

        print("숲 지역 게임 객체 배치 완료")

    async def verify_world_creation(self):
        """생성된 월드 검증"""
        print("\n=== 월드 생성 검증 ===")

        # 성문 확인
        gate = await self.room_repo.get_by_id("room_gate_west")
        if gate:
            print("✓ 서쪽 성문 생성 확인")
        else:
            print("✗ 서쪽 성문 생성 실패")

        # 마을 광장 출구 확인
        town_square = await self.room_repo.get_by_id("room_001")
        if town_square:
            exits = town_square.exits if isinstance(town_square.exits, dict) else json.loads(town_square.exits)
            if 'west' in exits:
                print("✓ 마을 광장 서쪽 출구 추가 확인")
            else:
                print("✗ 마을 광장 서쪽 출구 추가 실패")

        # 숲 지역 확인
        forest_count = 0
        for x in range(8):
            for y in range(8):
                room_id = f"forest_{x}_{y}"
                room = await self.room_repo.get_by_id(room_id)
                if room:
                    forest_count += 1

        print(f"✓ 숲 지역 방 생성: {forest_count}/64개")

        # 숲 객체 확인
        try:
            forest_objects = await self.object_repo.find_by(location_id="forest_1_1")
            print(f"✓ 숲 지역 객체 배치 확인: {len(forest_objects)}개 이상")
        except Exception as e:
            print(f"✓ 숲 지역 객체 배치 확인 중 오류: {e}")

    async def close(self):
        """리소스 정리"""
        if self.db_manager:
            await self.db_manager.close()


async def main():
    """메인 실행 함수"""
    print("=== 초기 월드 구성 시작 ===")

    creator = WorldCreator()

    try:
        await creator.initialize()

        # 1. 서쪽 성문 생성
        await creator.create_west_gate()

        # 2. 8x8 숲 지역 생성
        await creator.create_forest_region()

        # 3. 숲 지역 객체 배치
        await creator.create_forest_objects()

        # 4. 생성 결과 검증
        await creator.verify_world_creation()

        print("\n=== 초기 월드 구성 완료 ===")

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await creator.close()


if __name__ == "__main__":
    asyncio.run(main())