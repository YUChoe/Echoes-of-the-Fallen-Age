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
                exits=room_data.get('exits', {}),
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
                if hasattr(existing_room, key):
                    if key == 'exits' and isinstance(value, dict):
                        existing_exits = existing_room.exits.copy()
                        existing_exits.update(value)
                        setattr(existing_room, key, existing_exits)
                    else:
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
        """방에 새로운 출구를 추가합니다."""
        try:
            room = await self.get_room(room_id)
            if not room:
                return False

            target_room = await self.get_room(target_room_id)
            if not target_room:
                logger.warning(f"대상 방이 존재하지 않음: {target_room_id}")
                return False

            room.add_exit(direction, target_room_id)
            updated_room = await self.update_room(room_id, {
                'exits': room.exits,
                'updated_at': datetime.now()
            })

            success = updated_room is not None
            if success:
                logger.info(f"방 {room_id}에 출구 추가: {direction} -> {target_room_id}")
            return success
        except Exception as e:
            logger.error(f"출구 추가 실패 ({room_id}, {direction}, {target_room_id}): {e}")
            raise

    async def remove_room_exit(self, room_id: str, direction: str) -> bool:
        """방에서 출구를 제거합니다."""
        try:
            room = await self.get_room(room_id)
            if not room:
                return False

            removed = room.remove_exit(direction)
            if not removed:
                return False

            updated_room = await self.update_room(room_id, {
                'exits': room.exits,
                'updated_at': datetime.now()
            })

            success = updated_room is not None
            if success:
                logger.info(f"방 {room_id}에서 출구 제거: {direction}")
            return success
        except Exception as e:
            logger.error(f"출구 제거 실패 ({room_id}, {direction}): {e}")
            raise

    async def _remove_exits_to_room(self, target_room_id: str) -> None:
        """특정 방으로의 모든 출구를 제거합니다."""
        try:
            rooms_with_exits = await self._room_repo.get_rooms_with_exits_to(target_room_id)
            for room in rooms_with_exits:
                exits_to_remove = []
                for direction, room_id in room.exits.items():
                    if room_id == target_room_id:
                        exits_to_remove.append(direction)

                for direction in exits_to_remove:
                    room.remove_exit(direction)

                await self.update_room(room.id, {
                    'exits': room.exits,
                    'updated_at': datetime.now()
                })
                logger.info(f"방 {room.id}에서 삭제된 방 {target_room_id}로의 출구 제거")
        except Exception as e:
            logger.error(f"방으로의 출구 제거 실패 ({target_room_id}): {e}")
            raise
