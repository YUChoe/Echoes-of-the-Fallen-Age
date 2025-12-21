# -*- coding: utf-8 -*-
"""방 관리자 모듈"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..repositories import RoomRepository
from ..models import Room

logger = logging.getLogger(__name__)


class RoomManager:
    """방 관리 전담 클래스"""

    def __init__(self, room_repo: RoomRepository) -> None:
        """RoomManager를 초기화합니다."""
        self._room_repo: RoomRepository = room_repo
        logger.info("RoomManager 초기화 완료")

    async def get_room(self, room_id: str) -> Optional[Room]:
        """방 ID로 방 정보를 조회합니다."""
        try:
            return await self._room_repo.get_by_id(room_id)
        except Exception as e:
            logger.error(f"방 조회 실패 ({room_id}): {e}")
            raise

    async def create_room(self, room_data: Dict[str, Any]) -> Room:
        """새로운 방을 생성합니다."""
        try:
            room = Room(
                id=room_data.get('id'),
                description=room_data.get('description', {}),
                x=room_data.get('x'),
                y=room_data.get('y'),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            created_room = await self._room_repo.create(room.to_dict())
            logger.info(f"새 방 생성됨: {created_room.id}")
            return created_room
        except Exception as e:
            logger.error(f"방 생성 실패: {e}")
            raise

    async def update_room(self, room_id: str, updates: Dict[str, Any]) -> Optional[Room]:
        """기존 방의 정보를 수정합니다."""
        try:
            existing_room = await self.get_room(room_id)
            if not existing_room:
                logger.warning(f"수정하려는 방이 존재하지 않음: {room_id}")
                return None

            for key, value in updates.items():
                if hasattr(existing_room, key) and key != 'exits':  # exits는 더 이상 사용하지 않음
                    setattr(existing_room, key, value)

            existing_room.updated_at = datetime.now()
            updated_room = await self._room_repo.update(room_id, existing_room.to_dict())
            if updated_room:
                logger.info(f"방 정보 수정됨: {room_id}")
            return updated_room
        except Exception as e:
            logger.error(f"방 수정 실패 ({room_id}): {e}")
            raise

    async def delete_room(self, room_id: str, object_manager=None) -> bool:
        """방을 삭제합니다."""
        try:
            if object_manager:
                objects_in_room = await object_manager.get_room_objects(room_id)
                default_room_id = 'town_square'
                for obj in objects_in_room:
                    await object_manager.move_object_to_room(obj.id, default_room_id)
                    logger.info(f"객체 {obj.id}를 기본 방으로 이동")

            await self._remove_exits_to_room(room_id)
            success = await self._room_repo.delete(room_id)
            if success:
                logger.info(f"방 삭제됨: {room_id}")
            return success
        except Exception as e:
            logger.error(f"방 삭제 실패 ({room_id}): {e}")
            raise

    async def get_all_rooms(self) -> List[Room]:
        """모든 방 목록을 조회합니다."""
        try:
            return await self._room_repo.get_all()
        except Exception as e:
            logger.error(f"전체 방 목록 조회 실패: {e}")
            raise

    async def find_rooms_by_name(self, name_pattern: str, locale: str = 'en') -> List[Room]:
        """이름 패턴으로 방을 검색합니다."""
        try:
            return await self._room_repo.find_rooms_by_name(name_pattern, locale)
        except Exception as e:
            logger.error(f"방 이름 검색 실패 ({name_pattern}): {e}")
            raise

    async def get_connected_rooms(self, room_id: str) -> List[Room]:
        """특정 방과 연결된 방들을 조회합니다."""
        try:
            return await self._room_repo.get_connected_rooms(room_id)
        except Exception as e:
            logger.error(f"연결된 방 조회 실패 ({room_id}): {e}")
            raise

    async def add_room_exit(self, room_id: str, direction: str, target_room_id: str) -> bool:
        """출구 추가 (좌표 기반 시스템에서는 사용하지 않음)."""
        logger.warning("좌표 기반 시스템에서는 add_room_exit을 사용하지 않습니다.")
        return False

    async def remove_room_exit(self, room_id: str, direction: str) -> bool:
        """출구 제거 (좌표 기반 시스템에서는 사용하지 않음)."""
        logger.warning("좌표 기반 시스템에서는 remove_room_exit을 사용하지 않습니다.")
        return False

    async def _remove_exits_to_room(self, target_room_id: str) -> None:
        """특정 방으로의 출구들을 제거합니다 (좌표 기반에서는 불필요)."""
        logger.debug(f"좌표 기반 시스템에서는 출구 제거가 불필요합니다: {target_room_id}")
        pass
    # === 좌표 기반 방 관리 ===

    async def get_room_at_coordinates(self, x: int, y: int) -> Optional[Room]:
        """특정 좌표의 방을 조회합니다."""
        try:
            # 직접 데이터베이스에서 좌표로 조회
            return await self._room_repo.get_room_by_coordinates(x, y)
        except Exception as e:
            logger.error(f"좌표 기반 방 조회 실패 ({x}, {y}): {e}")
            raise

    async def get_rooms_in_area(self, center_x: int, center_y: int, radius: int) -> List[Room]:
        """특정 좌표 주변의 방들을 조회합니다."""
        try:
            rooms = await self._room_repo.get_all()
            area_rooms = []

            for room in rooms:
                if room.x is not None and room.y is not None:
                    distance = ((room.x - center_x) ** 2 + (room.y - center_y) ** 2) ** 0.5
                    if distance <= radius:
                        area_rooms.append(room)

            return area_rooms
        except Exception as e:
            logger.error(f"영역 내 방 조회 실패 ({center_x}, {center_y}, radius={radius}): {e}")
            raise

    async def find_rooms_by_coordinates(self, min_x: int, max_x: int, min_y: int, max_y: int) -> List[Room]:
        """좌표 범위 내의 방들을 조회합니다."""
        try:
            rooms = await self._room_repo.get_all()
            filtered_rooms = []

            for room in rooms:
                if (room.x is not None and room.y is not None and
                    min_x <= room.x <= max_x and min_y <= room.y <= max_y):
                    filtered_rooms.append(room)

            return filtered_rooms
        except Exception as e:
            logger.error(f"좌표 범위 방 조회 실패 ({min_x}-{max_x}, {min_y}-{max_y}): {e}")
            raise
    async def get_coordinate_based_exits(self, room_id: str) -> Dict[str, str]:
        """좌표 기반으로 방의 출구를 계산합니다 (동서남북 + enter)."""
        try:
            room = await self.get_room(room_id)
            if not room or room.x is None or room.y is None:
                return {}

            exits = {}

            # 방향별 좌표 오프셋 (동서남북만)
            direction_offsets = {
                'north': (0, 1),
                'south': (0, -1),
                'east': (1, 0),
                'west': (-1, 0)
            }

            # 좌표를 기반으로 인접한 방들을 찾아 출구 생성
            for direction, (dx, dy) in direction_offsets.items():
                adj_x = room.x + dx
                adj_y = room.y + dy

                # 해당 좌표에 방이 있는지 직접 조회
                adjacent_room = await self.get_room_at_coordinates(adj_x, adj_y)
                if adjacent_room:
                    exits[direction] = adjacent_room.id

            # enter 연결 확인
            db_manager = await self._room_repo.get_db_manager()
            cursor = await db_manager.execute(
                "SELECT to_x, to_y FROM room_connections WHERE from_x = ? AND from_y = ?",
                (room.x, room.y)
            )
            connection = await cursor.fetchone()

            if connection:
                # enter 연결이 있으면 enter 출구 추가
                target_room = await self.get_room_at_coordinates(connection[0], connection[1])
                if target_room:
                    exits['enter'] = target_room.id

            return exits
        except Exception as e:
            logger.error(f"좌표 기반 출구 계산 실패 ({room_id}): {e}")
            return {}

    async def update_room_exits_by_coordinates(self, room_id: str) -> bool:
        """방의 출구를 좌표 기반으로 업데이트합니다 (좌표 기반에서는 불필요)."""
        logger.debug("좌표 기반 시스템에서는 출구 업데이트가 불필요합니다.")
        return True

    async def update_all_rooms_exits_by_coordinates(self) -> Dict[str, int]:
        """모든 방의 출구를 좌표 기반으로 업데이트합니다 (좌표 기반에서는 불필요)."""
        logger.debug("좌표 기반 시스템에서는 출구 업데이트가 불필요합니다.")
        return {'total': 0, 'updated': 0, 'errors': 0}

    async def get_connected_rooms_by_coordinates(self, room_id: str) -> List[Room]:
        """좌표 기반으로 연결된 방들을 조회합니다."""
        try:
            room = await self.get_room(room_id)
            if not room or room.x is None or room.y is None:
                return []

            from ...utils.coordinate_utils import Direction, calculate_new_coordinates
            connected_rooms = []

            # 모든 방향의 인접 좌표 확인
            for direction in Direction:
                target_x, target_y = calculate_new_coordinates(room.x, room.y, direction)
                target_room = await self.get_room_at_coordinates(target_x, target_y)
                if target_room:
                    connected_rooms.append(target_room)

            return connected_rooms
        except Exception as e:
            logger.error(f"좌표 기반 연결된 방 조회 실패 ({room_id}): {e}")
            return []