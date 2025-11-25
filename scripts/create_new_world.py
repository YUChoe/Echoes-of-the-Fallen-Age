#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""새로운 월드 구조 생성 스크립트"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.mud_engine.database.connection import DatabaseManager
from src.mud_engine.game.repositories import RoomRepository


async def create_town_square(room_repo: RoomRepository):
    """광장 생성"""
    print("광장 생성 중...")
    
    # 이미 존재하는지 확인
    existing = await room_repo.get_by_id("town_square")
    if existing:
        print("  ⏭️  광장이 이미 존재합니다. 건너뜁니다.")
        return
    
    town_square = {
        "id": "town_square",
        "name_ko": "마을 광장",
        "name_en": "Town Square",
        "description_ko": "마을의 중심 광장입니다. 분수대가 있고 사람들이 모여 이야기를 나눕니다.",
        "description_en": "The central square of the town. A fountain stands in the center where people gather to chat.",
        "exits": {
            "north": "plains_4_8",  # 평원 중앙 하단으로
            "east": "market",
            "west": "forest_8_4",  # 숲 중앙 우측으로
            "south": "road_south_1"
        }
    }
    
    await room_repo.create(town_square)
    print("✅ 광장 생성 완료")


async def create_plains(room_repo: RoomRepository):
    """북쪽 9x9 평원 생성"""
    print("\n북쪽 평원 생성 중...")
    
    created = 0
    skipped = 0
    
    for x in range(9):
        for y in range(9):
            room_id = f"plains_{x}_{y}"
            
            # 이미 존재하는지 확인
            existing = await room_repo.get_by_id(room_id)
            if existing:
                skipped += 1
                continue
            
            # 출구 설정
            exits = {}
            if x > 0:
                exits["west"] = f"plains_{x-1}_{y}"
            if x < 8:
                exits["east"] = f"plains_{x+1}_{y}"
            if y > 0:
                exits["north"] = f"plains_{x}_{y-1}"
            if y < 8:
                exits["south"] = f"plains_{x}_{y+1}"
            
            # 광장과 연결 (중앙 하단)
            if x == 4 and y == 8:
                exits["south"] = "town_square"
            
            room_data = {
                "id": room_id,
                "name_ko": f"평원 ({x},{y})",
                "name_en": f"Plains ({x},{y})",
                "description_ko": "넓은 평원이 펼쳐져 있습니다. 풀이 바람에 흔들립니다.",
                "description_en": "Wide plains stretch out before you. Grass sways in the wind.",
                "exits": exits
            }
            
            await room_repo.create(room_data)
            created += 1
    
    print(f"✅ 평원 {created}개 방 생성 완료 (건너뜀: {skipped}개)")


async def create_forest(room_repo: RoomRepository):
    """서쪽 9x9 숲 생성"""
    print("\n서쪽 숲 생성 중...")
    
    created = 0
    skipped = 0
    
    for x in range(9):
        for y in range(9):
            room_id = f"forest_{x}_{y}"
            
            # 이미 존재하는지 확인
            existing = await room_repo.get_by_id(room_id)
            if existing:
                skipped += 1
                continue
            
            # 출구 설정
            exits = {}
            if x > 0:
                exits["west"] = f"forest_{x-1}_{y}"
            if x < 8:
                exits["east"] = f"forest_{x+1}_{y}"
            if y > 0:
                exits["north"] = f"forest_{x}_{y-1}"
            if y < 8:
                exits["south"] = f"forest_{x}_{y+1}"
            
            # 광장과 연결 (중앙 우측)
            if x == 8 and y == 4:
                exits["east"] = "town_square"
            
            room_data = {
                "id": room_id,
                "name_ko": f"숲 ({x},{y})",
                "name_en": f"Forest ({x},{y})",
                "description_ko": "울창한 숲입니다. 나무들이 빽빽하게 들어서 있습니다.",
                "description_en": "A dense forest. Trees stand thick and close together.",
                "exits": exits
            }
            
            await room_repo.create(room_data)
            created += 1
    
    print(f"✅ 숲 {created}개 방 생성 완료 (건너뜀: {skipped}개)")


async def create_eastern_path(room_repo: RoomRepository):
    """동쪽 경로 생성: 시장 → 교회로 가는 길 → 교회 → 성으로 가는 길 → 성"""
    print("\n동쪽 경로 생성 중...")
    
    rooms = [
        {
            "id": "market",
            "name_ko": "시장",
            "name_en": "Market",
            "description_ko": "활기찬 시장입니다. 상인들이 물건을 팔고 있습니다.",
            "description_en": "A bustling market. Merchants sell their wares.",
            "exits": {"west": "town_square", "east": "path_to_church"}
        },
        {
            "id": "path_to_church",
            "name_ko": "교회로 가는 길",
            "name_en": "Path to Church",
            "description_ko": "교회로 이어지는 조용한 길입니다.",
            "description_en": "A quiet path leading to the church.",
            "exits": {"west": "market", "east": "church"}
        },
        {
            "id": "church",
            "name_ko": "교회",
            "name_en": "Church",
            "description_ko": "신성한 교회입니다. 촛불이 조용히 타오르고 있습니다.",
            "description_en": "A sacred church. Candles burn quietly.",
            "exits": {"west": "path_to_church", "east": "path_to_castle"}
        },
        {
            "id": "path_to_castle",
            "name_ko": "성으로 가는 길",
            "name_en": "Path to Castle",
            "description_ko": "성으로 이어지는 넓은 길입니다.",
            "description_en": "A wide path leading to the castle.",
            "exits": {"west": "church", "east": "castle"}
        },
        {
            "id": "castle",
            "name_ko": "성",
            "name_en": "Castle",
            "description_ko": "웅장한 성입니다. 높은 탑이 하늘을 찌릅니다.",
            "description_en": "A magnificent castle. Tall towers pierce the sky.",
            "exits": {"west": "path_to_castle"}
        }
    ]
    
    created = 0
    skipped = 0
    
    for room_data in rooms:
        existing = await room_repo.get_by_id(room_data["id"])
        if existing:
            print(f"  ⏭️  {room_data['name_ko']} 이미 존재")
            skipped += 1
            continue
        
        await room_repo.create(room_data)
        print(f"  ✅ {room_data['name_ko']} 생성")
        created += 1
    
    print(f"✅ 동쪽 경로 {created}개 방 생성 완료 (건너뜀: {skipped}개)")


async def create_southern_road(room_repo: RoomRepository):
    """남쪽 도로 생성: 8칸 길이 도로 → 선착장"""
    print("\n남쪽 도로 생성 중...")
    
    created = 0
    skipped = 0
    
    # 8칸 도로
    for i in range(1, 9):
        room_id = f"road_south_{i}"
        
        existing = await room_repo.get_by_id(room_id)
        if existing:
            skipped += 1
            continue
        
        exits = {}
        if i == 1:
            exits["north"] = "town_square"
        else:
            exits["north"] = f"road_south_{i-1}"
        
        if i < 8:
            exits["south"] = f"road_south_{i+1}"
        else:
            exits["south"] = "dock"
        
        room_data = {
            "id": room_id,
            "name_ko": f"남쪽 도로 {i}",
            "name_en": f"South Road {i}",
            "description_ko": "남쪽으로 이어지는 넓은 도로입니다.",
            "description_en": "A wide road leading south.",
            "exits": exits
        }
        
        await room_repo.create(room_data)
        created += 1
    
    # 선착장
    existing = await room_repo.get_by_id("dock")
    if not existing:
        dock = {
            "id": "dock",
            "name_ko": "선착장",
            "name_en": "Dock",
            "description_ko": "바다가 보이는 선착장입니다. 배들이 정박해 있습니다.",
            "description_en": "A dock overlooking the sea. Ships are moored here.",
            "exits": {"north": "road_south_8"}
        }
        
        await room_repo.create(dock)
        created += 1
    else:
        skipped += 1
    
    print(f"✅ 남쪽 도로 {created}개 방 생성 완료 (건너뜀: {skipped}개)")


async def main():
    """메인 실행 함수"""
    print("=== 새로운 월드 구조 생성 시작 ===\n")
    
    # 데이터베이스 연결
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    try:
        room_repo = RoomRepository(db_manager)
        
        # 기존 방 삭제
        cursor = await db_manager.execute("SELECT COUNT(*) FROM rooms")
        existing_count = (await cursor.fetchone())[0]
        print(f"\n현재 {existing_count}개의 방이 존재합니다.")
        print("⚠️  모든 기존 방을 삭제하고 새로운 월드를 생성합니다.")
        
        print("\n기존 방 삭제 중...")
        await db_manager.execute("DELETE FROM rooms")
        print("✅ 기존 방 삭제 완료")
        
        # 새 월드 생성
        await create_town_square(room_repo)
        await create_plains(room_repo)
        await create_forest(room_repo)
        await create_eastern_path(room_repo)
        await create_southern_road(room_repo)
        
        # 통계
        cursor = await db_manager.execute("SELECT COUNT(*) FROM rooms")
        count = await cursor.fetchone()
        
        print(f"\n=== 월드 생성 완료 ===")
        print(f"총 {count[0]}개의 방이 생성되었습니다.")
        print(f"  - 광장: 1개")
        print(f"  - 북쪽 평원: 81개 (9x9)")
        print(f"  - 서쪽 숲: 81개 (9x9)")
        print(f"  - 동쪽 경로: 5개 (시장→교회→성)")
        print(f"  - 남쪽 도로: 9개 (도로 8개 + 선착장)")
        
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
