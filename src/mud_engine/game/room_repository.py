# -*- coding: utf-8 -*-
"""방 리포지토리"""

import logging
from typing import List, Optional

from ..database.repository import BaseRepository
from .models import Room

logger = logging.getLogger(__name__)


class RoomRepository(BaseRepository[Room]):
    """방 리포지토리"""

    def get_table_name(self) -> str:
        return "rooms"

    def get_model_class(self):
        return Room

    async def get_room_by_coordinates(self, x: int, y: int) -> Optional[Room]:
        """좌표로 방 조회"""
        try:
            db_manager = await self.get_db_manager()
            cursor = await db_manager.execute(
                "SELECT * FROM rooms WHERE x = ? AND y = ?",
                (x, y)
            )
            row = await cursor.fetchone()
            if row:
                # SQLite row를 딕셔너리로 변환
                columns = [description[0] for description in cursor.description]
                row_dict = dict(zip(columns, row))
                return Room.from_dict(row_dict)
            return None
        except Exception as e:
            logger.error(f"좌표 기반 방 조회 실패 ({x}, {y}): {e}")
            raise

    async def get_connected_rooms(self, room_id: str) -> List[Room]:
        """연결된 방들 조회 (좌표 기반)"""
        try:
            room = await self.get_by_id(room_id)
            if not room or room.x is None or room.y is None:
                return []

            from ...utils.coordinate_utils import Direction, calculate_new_coordinates
            connected_rooms = []

            # 모든 방향의 인접 좌표 확인
            for direction in Direction:
                target_x, target_y = calculate_new_coordinates(room.x, room.y, direction)

                # 해당 좌표에 방이 있는지 확인
                db_manager = await self.get_db_manager()
                cursor = await db_manager.execute(
                    "SELECT * FROM rooms WHERE x = ? AND y = ?",
                    (target_x, target_y)
                )
                row = await cursor.fetchone()
                if row:
                    connected_room = Room.from_dict(dict(row))
                    connected_rooms.append(connected_room)

            return connected_rooms
        except Exception as e:
            logger.error(f"연결된 방 조회 실패 ({room_id}): {e}")
            raise

    async def find_rooms_by_name(self, name_pattern: str, locale: str = 'en') -> List[Room]:
        """이름 패턴으로 방 검색 (부분 일치)"""
        try:
            # 모든 방을 가져와서 이름으로 필터링 (SQLite LIKE 쿼리 대신)
            all_rooms = await self.get_all()
            matching_rooms = []

            for room in all_rooms:
                # 방 설명으로 검색
                room_desc = room.get_localized_description(locale).lower()
                if name_pattern.lower() in room_desc:
                    matching_rooms.append(room)

            return matching_rooms
        except Exception as e:
            logger.error(f"방 이름 검색 실패 ({name_pattern}): {e}")
            raise

    async def get_rooms_with_exits_to(self, target_room_id: str) -> List[Room]:
        """특정 방으로 출구가 있는 방들 조회 (좌표 기반)"""
        try:
            target_room = await self.get_by_id(target_room_id)
            if not target_room or target_room.x is None or target_room.y is None:
                return []

            from ...utils.coordinate_utils import Direction, calculate_new_coordinates
            rooms_with_exits = []

            # 대상 방의 인접 좌표들 확인
            for direction in Direction:
                source_x, source_y = calculate_new_coordinates(target_room.x, target_room.y, direction)

                # 해당 좌표에 방이 있는지 확인
                db_manager = await self.get_db_manager()
                cursor = await db_manager.execute(
                    "SELECT * FROM rooms WHERE x = ? AND y = ?",
                    (source_x, source_y)
                )
                row = await cursor.fetchone()
                if row:
                    source_room = Room.from_dict(dict(row))
                    rooms_with_exits.append(source_room)

            return rooms_with_exits
        except Exception as e:
            logger.error(f"출구 대상 방 조회 실패 ({target_room_id}): {e}")
            raise
