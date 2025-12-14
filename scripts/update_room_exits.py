#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
좌표 기반 방 출구 업데이트 스크립트

모든 방의 출구를 좌표 기반으로 계산하여 데이터베이스에 업데이트합니다.
- 동서남북(north, south, east, west)과 enter만 지원
- 대각선 방향 및 기타 방향은 제거
- 좌표 기반으로 인접한 방을 찾아 출구 설정
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mud_engine.database.connection import DatabaseManager
from src.mud_engine.game.repositories import RoomRepository
from src.mud_engine.game.models import Room

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 허용되는 출구 방향 (동서남북 + enter만)
ALLOWED_DIRECTIONS = {'north', 'south', 'east', 'west', 'enter'}

# 방향별 좌표 오프셋
DIRECTION_OFFSETS = {
    'north': (0, 1),
    'south': (0, -1),
    'east': (1, 0),
    'west': (-1, 0)
}


class RoomExitUpdater:
    """방 출구 업데이트 관리자"""
    
    def __init__(self):
        self.db_manager = None
        self.room_repo = None
        self.rooms_by_coords: Dict[Tuple[int, int], Room] = {}
        
    async def initialize(self):
        """초기화"""
        self.db_manager = DatabaseManager()
        await self.db_manager.initialize()
        self.room_repo = RoomRepository(self.db_manager)
        
    async def cleanup(self):
        """정리"""
        if self.db_manager:
            await self.db_manager.close()
            
    async def load_all_rooms(self) -> List[Room]:
        """모든 방 로드"""
        logger.info("모든 방 데이터 로드 중...")
        rooms = await self.room_repo.get_all()
        logger.info(f"총 {len(rooms)}개 방 로드 완료")
        
        # 좌표별 방 매핑 생성
        self.rooms_by_coords = {}
        for room in rooms:
            if room.x is not None and room.y is not None:
                self.rooms_by_coords[(room.x, room.y)] = room
                
        logger.info(f"좌표가 있는 방: {len(self.rooms_by_coords)}개")
        return rooms
        
    def calculate_coordinate_exits(self, room: Room) -> Dict[str, str]:
        """좌표 기반으로 방의 출구 계산"""
        if room.x is None or room.y is None:
            logger.warning(f"방 {room.id}에 좌표가 없음")
            return {}
            
        new_exits = {}
        
        # 각 방향별로 인접한 방 확인
        for direction, (dx, dy) in DIRECTION_OFFSETS.items():
            target_x = room.x + dx
            target_y = room.y + dy
            
            # 해당 좌표에 방이 있는지 확인
            target_room = self.rooms_by_coords.get((target_x, target_y))
            if target_room:
                new_exits[direction] = target_room.id
                logger.debug(f"방 ({room.x}, {room.y}) -> {direction} -> ({target_x}, {target_y})")
                
        # 기존 enter 출구 유지 (특별한 출구)
        if 'enter' in room.exits:
            new_exits['enter'] = room.exits['enter']
            logger.debug(f"방 ({room.x}, {room.y})의 enter 출구 유지: {room.exits['enter']}")
            
        return new_exits
        
    def clean_invalid_exits(self, room: Room) -> Dict[str, str]:
        """허용되지 않는 출구 방향 제거"""
        cleaned_exits = {}
        
        for direction, target_id in room.exits.items():
            if direction in ALLOWED_DIRECTIONS:
                cleaned_exits[direction] = target_id
            else:
                logger.info(f"방 {room.id}에서 허용되지 않는 출구 제거: {direction}")
                
        return cleaned_exits
        
    async def update_room_exits(self, room: Room, new_exits: Dict[str, str]) -> bool:
        """방의 출구 업데이트"""
        if room.exits == new_exits:
            logger.debug(f"방 {room.id} ({room.x}, {room.y}): 출구 변경 없음")
            return False
            
        old_exits = room.exits.copy()
        room.exits = new_exits
        
        try:
            await self.room_repo.update(room.id, room.to_dict())
            logger.info(f"방 {room.id} ({room.x}, {room.y}) 출구 업데이트:")
            logger.info(f"  이전: {old_exits}")
            logger.info(f"  변경: {new_exits}")
            return True
        except Exception as e:
            logger.error(f"방 {room.id} 출구 업데이트 실패: {e}")
            room.exits = old_exits  # 롤백
            return False
            
    async def update_all_room_exits(self):
        """모든 방의 출구를 좌표 기반으로 업데이트"""
        logger.info("=== 방 출구 업데이트 시작 ===")
        
        # 모든 방 로드
        rooms = await self.load_all_rooms()
        
        updated_count = 0
        error_count = 0
        
        for room in rooms:
            try:
                # 1단계: 허용되지 않는 출구 제거
                cleaned_exits = self.clean_invalid_exits(room)
                
                # 2단계: 좌표 기반 출구 계산
                coordinate_exits = self.calculate_coordinate_exits(room)
                
                # 3단계: enter 출구는 기존 것 유지, 나머지는 좌표 기반으로 교체
                final_exits = coordinate_exits.copy()
                if 'enter' in cleaned_exits:
                    final_exits['enter'] = cleaned_exits['enter']
                
                # 4단계: 데이터베이스 업데이트
                if await self.update_room_exits(room, final_exits):
                    updated_count += 1
                    
            except Exception as e:
                logger.error(f"방 {room.id} 처리 중 오류: {e}")
                error_count += 1
                
        logger.info("=== 방 출구 업데이트 완료 ===")
        logger.info(f"총 방 수: {len(rooms)}")
        logger.info(f"업데이트된 방: {updated_count}")
        logger.info(f"오류 발생: {error_count}")
        
    async def validate_exits(self):
        """출구 유효성 검증"""
        logger.info("=== 출구 유효성 검증 시작 ===")
        
        rooms = await self.load_all_rooms()
        invalid_count = 0
        
        for room in rooms:
            for direction, target_id in room.exits.items():
                # 방향 유효성 검증
                if direction not in ALLOWED_DIRECTIONS:
                    logger.warning(f"방 {room.id}: 허용되지 않는 방향 '{direction}'")
                    invalid_count += 1
                    continue
                    
                # 대상 방 존재 여부 확인
                target_room = await self.room_repo.get_by_id(target_id)
                if not target_room:
                    logger.warning(f"방 {room.id}: 존재하지 않는 대상 방 '{target_id}' (방향: {direction})")
                    invalid_count += 1
                    continue
                    
                # 좌표 기반 검증 (enter 제외)
                if direction != 'enter' and room.x is not None and room.y is not None:
                    if target_room.x is not None and target_room.y is not None:
                        dx, dy = DIRECTION_OFFSETS.get(direction, (0, 0))
                        expected_x = room.x + dx
                        expected_y = room.y + dy
                        
                        if target_room.x != expected_x or target_room.y != expected_y:
                            logger.warning(f"방 {room.id} ({room.x}, {room.y}): "
                                         f"{direction} 방향 좌표 불일치 - "
                                         f"예상: ({expected_x}, {expected_y}), "
                                         f"실제: ({target_room.x}, {target_room.y})")
                            invalid_count += 1
                            
        logger.info("=== 출구 유효성 검증 완료 ===")
        logger.info(f"유효하지 않은 출구: {invalid_count}개")


async def main():
    """메인 함수"""
    updater = RoomExitUpdater()
    
    try:
        await updater.initialize()
        
        # 출구 업데이트 실행
        await updater.update_all_room_exits()
        
        # 검증 실행
        await updater.validate_exits()
        
    except Exception as e:
        logger.error(f"스크립트 실행 중 오류: {e}")
        return 1
    finally:
        await updater.cleanup()
        
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)