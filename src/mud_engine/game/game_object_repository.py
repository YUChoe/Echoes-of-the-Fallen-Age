# -*- coding: utf-8 -*-
"""게임 객체 리포지토리"""

import logging
from typing import List, Optional

from ..database.repository import BaseRepository
from .models import GameObject

logger = logging.getLogger(__name__)


class GameObjectRepository(BaseRepository[GameObject]):
    """게임 객체 리포지토리"""

    def get_table_name(self) -> str:
        return "game_objects"

    def get_model_class(self):
        return GameObject

    async def get_objects_in_room(self, room_id: str) -> List[GameObject]:
        """특정 방에 있는 객체들 조회"""
        try:
            # 대소문자 모두 검색
            room_objects = await self.find_by(location_type='ROOM', location_id=room_id)
            room_objects_lower = await self.find_by(location_type='room', location_id=room_id)
            return room_objects + room_objects_lower
        except Exception as e:
            logger.error(f"방 내 객체 조회 실패 ({room_id}): {e}")
            raise

    async def get_objects_in_inventory(self, character_id: str) -> List[GameObject]:
        """특정 캐릭터의 인벤토리 객체들 조회"""
        try:
            # 대소문자 모두 검색
            inventory_objects = await self.find_by(location_type='INVENTORY', location_id=character_id)
            inventory_objects_lower = await self.find_by(location_type='inventory', location_id=character_id)
            return inventory_objects + inventory_objects_lower
        except Exception as e:
            logger.error(f"인벤토리 객체 조회 실패 ({character_id}): {e}")
            raise

    async def get_objects_by_type(self, object_type: str) -> List[GameObject]:
        """타입별 객체 조회 (object_type 필드 제거됨 - 모든 객체 반환)"""
        try:
            # object_type 필드가 제거되었으므로 모든 객체를 반환
            return await self.get_all()
        except Exception as e:
            logger.error(f"객체 조회 실패: {e}")
            raise

    async def move_object_to_room(self, object_id: str, room_id: str) -> Optional[GameObject]:
        """객체를 방으로 이동"""
        try:
            return await self.update(object_id, {
                'location_type': 'ROOM',
                'location_id': room_id
            })
        except Exception as e:
            logger.error(f"객체 방 이동 실패 ({object_id} -> {room_id}): {e}")
            raise

    async def move_object_to_inventory(self, object_id: str, character_id: str) -> Optional[GameObject]:
        """객체를 인벤토리로 이동"""
        try:
            return await self.update(object_id, {
                'location_type': 'inventory',
                'location_id': character_id
            })
        except Exception as e:
            logger.error(f"객체 인벤토리 이동 실패 ({object_id} -> {character_id}): {e}")
            raise

    async def find_objects_by_name(self, name_pattern: str, locale: str = 'en') -> List[GameObject]:
        """이름 패턴으로 객체 검색 (부분 일치)"""
        try:
            # 모든 객체를 가져와서 이름으로 필터링
            all_objects = await self.get_all()
            matching_objects = []

            for obj in all_objects:
                obj_name = obj.get_localized_name(locale).lower()
                if name_pattern.lower() in obj_name:
                    matching_objects.append(obj)

            return matching_objects
        except Exception as e:
            logger.error(f"객체 이름 검색 실패 ({name_pattern}): {e}")
            raise

    async def get_objects_in_container(self, container_id: str) -> List[GameObject]:
        """컨테이너 내부의 객체들 조회"""
        try:
            # 대소문자 모두 검색
            container_objects = await self.find_by(location_type='CONTAINER', location_id=container_id)
            container_objects_lower = await self.find_by(location_type='container', location_id=container_id)
            return container_objects + container_objects_lower
        except Exception as e:
            logger.error(f"컨테이너 내 객체 조회 실패 ({container_id}): {e}")
            raise

    async def move_object_to_container(self, object_id: str, container_id: str) -> Optional[GameObject]:
        """객체를 컨테이너로 이동"""
        try:
            return await self.update(object_id, {
                'location_type': 'container',
                'location_id': container_id
            })
        except Exception as e:
            logger.error(f"객체 컨테이너 이동 실패 ({object_id} -> {container_id}): {e}")
            raise
