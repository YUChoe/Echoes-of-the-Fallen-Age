#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
북쪽 평원에 작은 쥐 20마리를 스폰하는 스크립트

작은 쥐 특성:
- 레벨 1
- 약한 능력치 (HP 10, 공격력 2, 방어력 1)
- 명중률 낮음 (50%)
- 경험치 보상 매우 적음 (5 exp)
- 골드 보상 없음 (0 gold)
- 2x2 영역 내에서 로밍
- 1분에 한 번 50% 확률로 이동
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mud_engine.database.connection import DatabaseManager
from src.mud_engine.game.repositories import MonsterRepository, RoomRepository
from src.mud_engine.game.monster import Monster, MonsterType, MonsterBehavior, MonsterStats, DropItem
from uuid import uuid4
from datetime import datetime


async def find_north_plains_rooms(room_repo: RoomRepository) -> list:
    """북쪽 평원 방들을 찾습니다."""
    # 평원 관련 방들 조회
    all_rooms = await room_repo.get_all()
    
    # 이름에 '평원'이 포함된 방들 필터링
    plains_rooms = []
    for room in all_rooms:
        name_ko = room.name.get('ko', '')
        if '평원' in name_ko and room.x is not None and room.y is not None:
            plains_rooms.append(room)
    
    # 좌표 기준으로 정렬 (북쪽 = y값이 큰 것)
    plains_rooms.sort(key=lambda r: (r.y, r.x), reverse=True)
    
    return plains_rooms


async def get_spawn_area(plains_rooms: list) -> dict:
    """스폰 영역을 결정합니다 (평원 전체)."""
    if not plains_rooms:
        return {}
    
    # 평원 전체 영역 계산
    min_x = min(room.x for room in plains_rooms)
    max_x = max(room.x for room in plains_rooms)
    min_y = min(room.y for room in plains_rooms)
    max_y = max(room.y for room in plains_rooms)
    
    spawn_area = {
        'min_x': min_x,
        'max_x': max_x,
        'min_y': min_y,
        'max_y': max_y
    }
    
    return {
        'area': spawn_area,
        'rooms': plains_rooms  # 평원 전체 방 사용
    }


async def create_small_rat_template(monster_repo: MonsterRepository) -> Monster:
    """작은 쥐 템플릿을 생성합니다."""
    template_id = "template_small_rat"
    
    # 기존 템플릿 확인
    existing = await monster_repo.get_by_id(template_id)
    if existing:
        print(f"✅ 작은 쥐 템플릿이 이미 존재합니다: {template_id}")
        return existing
    
    # 작은 쥐 능력치 (D&D 기반 - 매우 약함)
    rat_stats = MonsterStats(
        strength=6,      # 힘 6 (매우 약함) -> 공격력 약 4
        dexterity=16,    # 민첩 16 (빠름) -> AC 13, 명중 어려움
        constitution=8,  # 체력 8 (약함) -> HP 10
        intelligence=2,  # 지능 2 (동물)
        wisdom=10,       # 지혜 10 (보통)
        charisma=4,      # 매력 4 (낮음)
        level=1,         # 레벨 1
        current_hp=10    # 현재 HP
    )
    
    # 작은 쥐 템플릿 생성
    rat_template = Monster(
        id=template_id,
        name={'en': 'Small Rat', 'ko': '작은 쥐'},
        description={
            'en': 'A tiny rat scurrying around. It looks weak and scared.',
            'ko': '작고 빠르게 움직이는 쥐입니다. 약하고 겁이 많아 보입니다.'
        },
        monster_type=MonsterType.PASSIVE,  # 후공형 (공격받으면 반격)
        behavior=MonsterBehavior.ROAMING,  # 로밍형
        stats=rat_stats,
        experience_reward=5,  # 경험치 5 (매우 적음)
        gold_reward=0,  # 골드 보상 없음
        drop_items=[],  # 드롭 아이템 없음
        spawn_room_id=None,  # 템플릿이므로 스폰 방 없음
        current_room_id=None,
        respawn_time=300,  # 5분 리스폰
        aggro_range=0,  # 어그로 없음 (후공형)
        roaming_range=2,  # 로밍 범위 2칸
        properties={
            'level': 1,
            'is_template': True
        },
        created_at=datetime.now()
    )
    
    # 데이터베이스에 저장
    created = await monster_repo.create(rat_template.to_dict())
    print(f"✅ 작은 쥐 템플릿 생성 완료: {template_id}")
    
    return created


async def spawn_small_rats(monster_repo: MonsterRepository, spawn_info: dict, count: int = 20) -> list:
    """작은 쥐들을 스폰합니다 (평원 전체에 분산)."""
    area_rooms = spawn_info['rooms']
    spawn_area = spawn_info['area']
    
    if not area_rooms:
        print("❌ 스폰 가능한 방이 없습니다.")
        return []
    
    print(f"\n📍 스폰 영역: X({spawn_area['min_x']}-{spawn_area['max_x']}), Y({spawn_area['min_y']}-{spawn_area['max_y']})")
    print(f"📍 스폰 가능한 방: {len(area_rooms)}개")
    print(f"📍 평원 전체에 {count}마리 분산 스폰")
    
    spawned_rats = []
    
    # 로밍 설정
    roaming_config = {
        'roam_chance': 0.5,  # 50% 확률로 이동
        'roaming_area': spawn_area
    }
    
    # 평원 전체에 균등하게 분배
    import random
    for i in range(count):
        # 랜덤하게 방 선택 (평원 전체)
        spawn_room = random.choice(area_rooms)
        
        # 작은 쥐 능력치 (D&D 기반)
        rat_stats = MonsterStats(
            strength=6,      # 힘 6 (매우 약함)
            dexterity=16,    # 민첩 16 (빠름)
            constitution=8,  # 체력 8 (약함)
            intelligence=2,  # 지능 2 (동물)
            wisdom=10,       # 지혜 10 (보통)
            charisma=4,      # 매력 4 (낮음)
            level=1,         # 레벨 1
            current_hp=10    # 현재 HP
        )
        
        # 작은 쥐 생성
        rat = Monster(
            id=str(uuid4()),
            name={'en': 'Small Rat', 'ko': '작은 쥐'},
            description={
                'en': 'A tiny rat scurrying around. It looks weak and scared.',
                'ko': '작고 빠르게 움직이는 쥐입니다. 약하고 겁이 많아 보입니다.'
            },
            monster_type=MonsterType.PASSIVE,
            behavior=MonsterBehavior.ROAMING,
            stats=rat_stats,
            experience_reward=5,
            gold_reward=0,
            drop_items=[],
            spawn_room_id=spawn_room.id,
            current_room_id=spawn_room.id,
            respawn_time=300,
            aggro_range=0,
            roaming_range=2,
            properties={
                'level': 1,
                'template_id': 'template_small_rat',
                'roaming_config': roaming_config
            },
            is_alive=True,
            created_at=datetime.now()
        )
        
        # 데이터베이스에 저장
        created_rat = await monster_repo.create(rat.to_dict())
        spawned_rats.append(created_rat)
        
        room_name = spawn_room.name.get('ko', spawn_room.id)
        print(f"  🐀 작은 쥐 #{i+1} 스폰됨: {room_name} ({spawn_room.x}, {spawn_room.y})")
    
    return spawned_rats


async def setup_spawn_points(world_manager, spawn_info: dict) -> None:
    """스폰 포인트를 설정합니다."""
    area_rooms = spawn_info['rooms']
    
    for room in area_rooms:
        await world_manager.add_spawn_point(
            room_id=room.id,
            monster_template_id='template_small_rat',
            max_count=5,  # 각 방에 최대 5마리
            spawn_chance=0.5  # 50% 확률로 스폰
        )
        
        room_name = room.name.get('ko', room.id)
        print(f"  📌 스폰 포인트 설정: {room_name} (최대 5마리)")


async def main():
    """메인 함수"""
    print("=" * 60)
    print("작은 쥐 스폰 스크립트")
    print("=" * 60)
    
    # 데이터베이스 연결
    db_manager = DatabaseManager("data/mud_engine.db")
    await db_manager.initialize()
    
    try:
        # 리포지토리 생성
        room_repo = RoomRepository(db_manager)
        monster_repo = MonsterRepository(db_manager)
        
        # 1. 북쪽 평원 방들 찾기
        print("\n1️⃣ 북쪽 평원 방 검색 중...")
        plains_rooms = await find_north_plains_rooms(room_repo)
        
        if not plains_rooms:
            print("❌ 평원 방을 찾을 수 없습니다.")
            return
        
        print(f"✅ 평원 방 {len(plains_rooms)}개 발견")
        
        # 2. 스폰 영역 결정 (2x2)
        print("\n2️⃣ 스폰 영역 결정 중...")
        spawn_info = await get_spawn_area(plains_rooms)
        
        if not spawn_info or not spawn_info.get('rooms'):
            print("❌ 스폰 가능한 영역을 찾을 수 없습니다.")
            return
        
        print(f"✅ 스폰 영역 설정 완료: {len(spawn_info['rooms'])}개 방")
        
        # 3. 작은 쥐 템플릿 생성
        print("\n3️⃣ 작은 쥐 템플릿 생성 중...")
        await create_small_rat_template(monster_repo)
        
        # 4. 작은 쥐 20마리 스폰
        print("\n4️⃣ 작은 쥐 20마리 스폰 중...")
        spawned_rats = await spawn_small_rats(monster_repo, spawn_info, count=20)
        
        print(f"\n✅ 총 {len(spawned_rats)}마리의 작은 쥐가 스폰되었습니다!")
        
        # 5. 스폰 포인트 설정 안내
        print("\n5️⃣ 스폰 포인트 설정 안내")
        print("=" * 60)
        print("서버 시작 시 WorldManager에서 다음과 같이 스폰 포인트를 설정하세요:")
        print()
        for room in spawn_info['rooms']:
            room_name = room.name.get('ko', room.id)
            print(f"  await world_manager.add_spawn_point(")
            print(f"      room_id='{room.id}',")
            print(f"      monster_template_id='template_small_rat',")
            print(f"      max_count=5,")
            print(f"      spawn_chance=0.5")
            print(f"  )  # {room_name}")
            print()
        
        print("=" * 60)
        print("✅ 작은 쥐 스폰 완료!")
        print("=" * 60)
        
        # 스폰된 쥐 정보 출력
        print("\n📊 스폰된 작은 쥐 정보:")
        print(f"  - 총 개체 수: {len(spawned_rats)}마리")
        print(f"  - 레벨: 1")
        print(f"  - HP: 10")
        print(f"  - 공격력: 2")
        print(f"  - 방어력: 1")
        print(f"  - 명중률: 50%")
        print(f"  - 경험치 보상: 5 exp")
        print(f"  - 골드 보상: 0 gold")
        print(f"  - 로밍: 2x2 영역 내에서 1분마다 50% 확률로 이동")
        
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
