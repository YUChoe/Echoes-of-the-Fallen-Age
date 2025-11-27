#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
출구 정보를 기반으로 방들의 좌표를 재배정하는 스크립트
Town Square를 (0, 0)으로 하고, 출구 방향에 따라 좌표 배정:
- north: y + 1
- south: y - 1
- east: x + 1
- west: x - 1
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Tuple, Set

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mud_engine.database.connection import DatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# 방향별 좌표 변화
DIRECTION_OFFSETS = {
    'north': (0, 1),
    'south': (0, -1),
    'east': (1, 0),
    'west': (-1, 0)
}


async def load_rooms(db_manager) -> Dict[str, dict]:
    """모든 방 정보 로드"""
    cursor = await db_manager.execute("SELECT id, name_ko, exits FROM rooms")
    rooms_data = await cursor.fetchall()
    
    rooms = {}
    for room_id, name_ko, exits_json in rooms_data:
        try:
            exits = json.loads(exits_json) if isinstance(exits_json, str) else exits_json
        except (json.JSONDecodeError, TypeError):
            exits = {}
        
        rooms[room_id] = {
            'id': room_id,
            'name_ko': name_ko,
            'exits': exits,
            'x': None,
            'y': None
        }
    
    return rooms


async def assign_coordinates_by_exits(db_manager, start_room_id: str = 'town_square'):
    """출구 기반으로 좌표 배정 (BFS 알고리즘)"""
    # 모든 방 로드
    rooms = await load_rooms(db_manager)
    
    if start_room_id not in rooms:
        logger.error(f"시작 방 '{start_room_id}'를 찾을 수 없습니다")
        return
    
    # 시작 방을 (0, 0)으로 설정
    rooms[start_room_id]['x'] = 0
    rooms[start_room_id]['y'] = 0
    
    # BFS 큐
    queue = [start_room_id]
    visited: Set[str] = {start_room_id}
    
    logger.info(f"시작 방: {start_room_id} ({rooms[start_room_id]['name_ko']}) at (0, 0)")
    
    while queue:
        current_room_id = queue.pop(0)
        current_room = rooms[current_room_id]
        current_x = current_room['x']
        current_y = current_room['y']
        
        # 현재 방의 모든 출구 확인
        for direction, target_room_id in current_room['exits'].items():
            if target_room_id not in rooms:
                logger.warning(f"출구 대상 방 '{target_room_id}'를 찾을 수 없음 (from {current_room_id}, direction {direction})")
                continue
            
            if target_room_id in visited:
                continue
            
            # 방향에 따른 좌표 계산
            dx, dy = DIRECTION_OFFSETS.get(direction, (0, 0))
            new_x = current_x + dx
            new_y = current_y + dy
            
            # 좌표 배정
            rooms[target_room_id]['x'] = new_x
            rooms[target_room_id]['y'] = new_y
            
            visited.add(target_room_id)
            queue.append(target_room_id)
            
            logger.info(f"  {direction:5s} -> {target_room_id} ({rooms[target_room_id]['name_ko']}) at ({new_x}, {new_y})")
    
    return rooms


async def update_database(db_manager, rooms: Dict[str, dict]):
    """데이터베이스에 좌표 업데이트"""
    updated_count = 0
    skipped_count = 0
    
    for room_id, room_data in rooms.items():
        x = room_data['x']
        y = room_data['y']
        
        if x is None or y is None:
            logger.warning(f"방 {room_id} ({room_data['name_ko']})는 좌표를 배정받지 못함")
            skipped_count += 1
            continue
        
        await db_manager.execute(
            "UPDATE rooms SET x = ?, y = ? WHERE id = ?",
            (x, y, room_id)
        )
        updated_count += 1
    
    await db_manager.commit()
    logger.info(f"총 {updated_count}개 방 좌표 업데이트, {skipped_count}개 방 건너뜀")


async def print_coordinate_map(rooms: Dict[str, dict]):
    """좌표 맵 출력"""
    # 좌표가 있는 방들만 필터링
    rooms_with_coords = {
        room_id: room_data 
        for room_id, room_data in rooms.items() 
        if room_data['x'] is not None and room_data['y'] is not None
    }
    
    if not rooms_with_coords:
        logger.warning("좌표가 배정된 방이 없습니다")
        return
    
    # 좌표 범위 계산
    min_x = min(room['x'] for room in rooms_with_coords.values())
    max_x = max(room['x'] for room in rooms_with_coords.values())
    min_y = min(room['y'] for room in rooms_with_coords.values())
    max_y = max(room['y'] for room in rooms_with_coords.values())
    
    logger.info(f"\n좌표 범위: x({min_x} ~ {max_x}), y({min_y} ~ {max_y})")
    logger.info(f"총 {len(rooms_with_coords)}개 방에 좌표 배정됨\n")
    
    # 좌표별로 정렬하여 출력
    sorted_rooms = sorted(
        rooms_with_coords.items(),
        key=lambda item: (item[1]['y'], item[1]['x']),
        reverse=True  # y 좌표 큰 것부터 (북쪽부터)
    )
    
    logger.info("좌표별 방 목록:")
    for room_id, room_data in sorted_rooms:
        logger.info(f"  ({room_data['x']:3d}, {room_data['y']:3d}) - {room_id:20s} ({room_data['name_ko']})")


async def main():
    """메인 함수"""
    db_manager = DatabaseManager("sqlite:///data/mud_engine.db")
    await db_manager.initialize()
    
    try:
        logger.info("=== 출구 기반 좌표 재배정 시작 ===\n")
        
        # 좌표 배정
        rooms = await assign_coordinates_by_exits(db_manager, start_room_id='town_square')
        
        if rooms:
            # 데이터베이스 업데이트
            await update_database(db_manager, rooms)
            
            # 결과 출력
            await print_coordinate_map(rooms)
        
        logger.info("\n=== 좌표 재배정 완료 ===")
        
    except Exception as e:
        logger.error(f"좌표 재배정 중 오류: {e}", exc_info=True)
        await db_manager.rollback()
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
