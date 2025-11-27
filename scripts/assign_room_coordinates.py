#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기존 방들에 x, y 좌표를 배정하는 스크립트
"""

import asyncio
import logging
import re
import sys
from pathlib import Path

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


async def assign_coordinates():
    """기존 방들에 좌표 배정"""
    db_manager = DatabaseManager("sqlite:///data/mud_engine.db")
    await db_manager.initialize()
    
    try:
        # 모든 방 조회
        cursor = await db_manager.execute("SELECT id, name_ko, x, y FROM rooms")
        rooms = await cursor.fetchall()
        
        logger.info(f"총 {len(rooms)}개의 방 발견")
        
        updated_count = 0
        
        for room in rooms:
            room_id, name_ko, current_x, current_y = room
            
            # 이미 좌표가 있으면 건너뛰기
            if current_x is not None and current_y is not None:
                logger.info(f"방 {room_id} ({name_ko})는 이미 좌표가 있음: ({current_x}, {current_y})")
                continue
            
            # 방 ID에서 좌표 추출 시도
            # 패턴: forest_0_0, room_001 등
            x, y = None, None
            
            # forest_x_y 패턴
            match = re.match(r'forest_(\d+)_(\d+)', room_id)
            if match:
                x, y = int(match.group(1)), int(match.group(2))
            
            # town_x_y 패턴
            match = re.match(r'town_(\d+)_(\d+)', room_id)
            if match:
                x, y = int(match.group(1)), int(match.group(2))
            
            # room_001, room_002 등의 패턴 (기본 마을 방들)
            # 이런 방들은 임의의 좌표 배정
            if room_id == 'room_001':  # Town Square
                x, y = 50, 50  # 중앙 좌표
            elif room_id == 'room_002':  # North Street
                x, y = 50, 51  # 북쪽
            elif room_id == 'room_003':  # East Market
                x, y = 51, 50  # 동쪽
            
            if x is not None and y is not None:
                await db_manager.execute(
                    "UPDATE rooms SET x = ?, y = ? WHERE id = ?",
                    (x, y, room_id)
                )
                logger.info(f"방 {room_id} ({name_ko})에 좌표 ({x}, {y}) 배정")
                updated_count += 1
            else:
                logger.warning(f"방 {room_id} ({name_ko})의 좌표를 추출할 수 없음")
        
        await db_manager.commit()
        logger.info(f"총 {updated_count}개의 방에 좌표 배정 완료")
        
        # 결과 확인
        cursor = await db_manager.execute(
            "SELECT id, name_ko, x, y FROM rooms WHERE x IS NOT NULL AND y IS NOT NULL ORDER BY x, y"
        )
        rooms_with_coords = await cursor.fetchall()
        
        logger.info(f"\n좌표가 배정된 방 목록 ({len(rooms_with_coords)}개):")
        for room_id, name_ko, x, y in rooms_with_coords:
            logger.info(f"  ({x:3d}, {y:3d}) - {room_id} ({name_ko})")
        
    except Exception as e:
        logger.error(f"좌표 배정 중 오류: {e}", exc_info=True)
        await db_manager.rollback()
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(assign_coordinates())
