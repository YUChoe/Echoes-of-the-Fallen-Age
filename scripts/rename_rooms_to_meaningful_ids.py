#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""방 ID를 좌표 기반에서 의미 있는 이름으로 변경"""

import asyncio
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mud_engine.database.connection import DatabaseManager


# 방 타입별 이름 변형
ROOM_NAME_VARIANTS = {
    'forest': [
        'forest', 'forest_clearing', 'forest_path', 'forest_grove', 
        'forest_thicket', 'forest_glade', 'forest_edge', 'forest_depths',
        'forest_trail', 'forest_hollow', 'forest_canopy', 'forest_undergrowth'
    ],
    'plains': [
        'plains', 'plains_field', 'plains_meadow', 'plains_grassland',
        'plains_prairie', 'plains_steppe', 'plains_pasture', 'plains_clearing',
        'plains_expanse', 'plains_vista', 'plains_horizon', 'plains_stretch'
    ],
    'road': [
        'road', 'road_crossing', 'road_bend', 'road_fork',
        'road_junction', 'road_path', 'road_trail', 'road_way'
    ],
    'path': [
        'path', 'path_trail', 'path_way', 'path_route',
        'path_track', 'path_passage', 'path_walkway', 'path_lane'
    ],
    'town': [
        'town_square', 'town_street', 'town_alley', 'town_plaza',
        'town_market', 'town_gate', 'town_center', 'town_district'
    ],
    'room': [
        'room', 'chamber', 'hall', 'space',
        'area', 'zone', 'section', 'quarter'
    ]
}


def generate_room_id(base_type: str, index: int, total: int) -> str:
    """방 타입과 인덱스로 의미 있는 ID 생성"""
    variants = ROOM_NAME_VARIANTS.get(base_type, [base_type])
    
    # 변형 이름 순환 사용
    variant_index = index % len(variants)
    variant_name = variants[variant_index]
    
    # 같은 변형이 여러 개 필요한 경우 번호 추가
    repeat_count = index // len(variants)
    if repeat_count > 0:
        return f"{variant_name}_{repeat_count + 1}"
    else:
        return variant_name


def clean_room_name(name: str) -> str:
    """방 이름에서 좌표 제거"""
    # "(0,0)" 같은 좌표 패턴 제거
    import re
    cleaned = re.sub(r'\s*\([0-9\-]+,\s*[0-9\-]+\)', '', name)
    return cleaned.strip()


async def rename_rooms():
    """방 ID와 이름 변경"""
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    try:
        print("=== 방 ID 및 이름 변경 시작 ===\n")
        
        # 외래 키 제약 조건 비활성화
        await db_manager.execute("PRAGMA foreign_keys = OFF")
        
        # 1. 모든 방 조회
        cursor = await db_manager.execute(
            "SELECT id, name_en, name_ko, x, y, exits FROM rooms ORDER BY id"
        )
        rooms = await cursor.fetchall()
        
        print(f"총 {len(rooms)}개의 방 발견\n")
        
        # 2. 방 타입별로 그룹화
        room_groups: Dict[str, List[Tuple]] = {}
        for room in rooms:
            old_id = room[0]
            
            # 타입 추출 (예: forest_0_0 -> forest)
            if '_' in old_id:
                base_type = old_id.split('_')[0]
            else:
                base_type = old_id
            
            if base_type not in room_groups:
                room_groups[base_type] = []
            room_groups[base_type].append(room)
        
        # 3. ID 매핑 생성
        id_mapping: Dict[str, str] = {}  # old_id -> new_id
        
        for base_type, type_rooms in room_groups.items():
            print(f"\n{base_type} 타입: {len(type_rooms)}개")
            
            for index, room in enumerate(type_rooms):
                old_id = room[0]
                new_id = generate_room_id(base_type, index, len(type_rooms))
                
                # ID 중복 방지
                counter = 1
                original_new_id = new_id
                while new_id in id_mapping.values():
                    new_id = f"{original_new_id}_{counter}"
                    counter += 1
                
                id_mapping[old_id] = new_id
                print(f"  {old_id} -> {new_id}")
        
        print(f"\n총 {len(id_mapping)}개의 방 ID 매핑 생성")
        
        # 4. 사용자 확인
        response = input("\n변경을 진행하시겠습니까? (yes/no): ")
        if response.lower() != 'yes':
            print("취소되었습니다.")
            return
        
        # 5. 임시 테이블 생성 및 데이터 복사
        print("\n임시 테이블 생성 중...")
        await db_manager.execute("""
            CREATE TABLE rooms_new (
                id TEXT PRIMARY KEY,
                name_en TEXT NOT NULL,
                name_ko TEXT NOT NULL,
                description_en TEXT,
                description_ko TEXT,
                exits TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                x INTEGER,
                y INTEGER
            )
        """)
        
        # 6. 데이터 변환 및 삽입
        print("데이터 변환 중...")
        for room in rooms:
            old_id, name_en, name_ko, x, y, exits_json = room[0], room[1], room[2], room[3], room[4], room[5]
            new_id = id_mapping[old_id]
            
            # 이름에서 좌표 제거
            new_name_en = clean_room_name(name_en)
            new_name_ko = clean_room_name(name_ko)
            
            # exits JSON 업데이트
            try:
                exits = json.loads(exits_json) if exits_json else {}
                new_exits = {}
                for direction, target_id in exits.items():
                    new_target_id = id_mapping.get(target_id, target_id)
                    new_exits[direction] = new_target_id
                new_exits_json = json.dumps(new_exits, ensure_ascii=False)
            except:
                new_exits_json = '{}'
            
            await db_manager.execute("""
                INSERT INTO rooms_new (id, name_en, name_ko, description_en, description_ko, exits, x, y)
                SELECT ?, ?, ?, description_en, description_ko, ?, ?, ?
                FROM rooms WHERE id = ?
            """, (new_id, new_name_en, new_name_ko, new_exits_json, x, y, old_id))
        
        # 7. 플레이어 last_room_id 업데이트 (좌표 기반)
        print("플레이어 위치 업데이트 중...")
        cursor = await db_manager.execute("SELECT id, last_room_x, last_room_y FROM players")
        players = await cursor.fetchall()
        
        for player_id, x, y in players:
            if x is not None and y is not None:
                # 좌표로 새 room_id 찾기
                cursor2 = await db_manager.execute(
                    "SELECT id FROM rooms_new WHERE x = ? AND y = ?",
                    (x, y)
                )
                room_row = await cursor2.fetchone()
                if room_row:
                    new_room_id = room_row[0]
                    await db_manager.execute(
                        "UPDATE players SET last_room_id = ? WHERE id = ?",
                        (new_room_id, player_id)
                    )
        
        # 8. 몬스터 위치 업데이트
        print("몬스터 위치 업데이트 중...")
        cursor = await db_manager.execute("SELECT id, spawn_room_id, current_room_id FROM monsters")
        monsters = await cursor.fetchall()
        
        for monster_id, spawn_room_id, current_room_id in monsters:
            new_spawn = id_mapping.get(spawn_room_id, spawn_room_id)
            new_current = id_mapping.get(current_room_id, current_room_id)
            await db_manager.execute(
                "UPDATE monsters SET spawn_room_id = ?, current_room_id = ? WHERE id = ?",
                (new_spawn, new_current, monster_id)
            )
        
        # 9. 기존 테이블 삭제 및 새 테이블로 교체
        print("테이블 교체 중...")
        await db_manager.execute("DROP TABLE rooms")
        await db_manager.execute("ALTER TABLE rooms_new RENAME TO rooms")
        
        # 10. 인덱스 재생성
        print("인덱스 재생성 중...")
        await db_manager.execute("CREATE INDEX IF NOT EXISTS idx_rooms_coordinates ON rooms(x, y)")
        
        # 외래 키 제약 조건 재활성화
        await db_manager.execute("PRAGMA foreign_keys = ON")
        
        await db_manager.commit()
        
        print("\n✅ 방 ID 및 이름 변경 완료!")
        print(f"  - 총 {len(rooms)}개의 방 업데이트")
        print(f"  - 총 {len(players)}명의 플레이어 위치 업데이트")
        print(f"  - 총 {len(monsters)}개의 몬스터 위치 업데이트")
        
        # 11. 결과 확인
        print("\n변경 결과 샘플:")
        cursor = await db_manager.execute("SELECT id, name_en, name_ko FROM rooms LIMIT 10")
        sample_rooms = await cursor.fetchall()
        for room in sample_rooms:
            print(f"  {room[0]}: {room[1]} / {room[2]}")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        await db_manager.rollback()
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(rename_rooms())
