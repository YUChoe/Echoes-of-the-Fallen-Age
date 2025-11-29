# -*- coding: utf-8 -*-
"""게임 객체 관리자 모듈"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..repositories import GameObjectRepository
from ..models import GameObject

logger = logging.getLogger(__name__)


class ObjectManager:
    """게임 객체 관리 전담 클래스"""

    def __init__(self, object_repo: GameObjectRepository) -> None:
        """ObjectManager를 초기화합니다."""
        self._object_repo: GameObjectRepository = object_repo
        logger.info("ObjectManager 초기화 완료")

    async def get_game_object(self, object_id: str) -> Optional[GameObject]:
        """게임 객체 ID로 객체 정보를 조회합니다."""
        try:
            return await self._object_repo.get_by_id(object_id)
        except Exception as e:
            logger.error(f"게임 객체 조회 실패 ({object_id}): {e}")
            raise

    async def create_game_object(self, object_data: Dict[str, Any]) -> GameObject:
        """새로운 게임 객체를 생성합니다."""
        try:
            game_object = GameObject(
                id=object_data.get('id'),
                name=object_data.get('name', {}),
                description=object_data.get('description', {}),
                object_type=object_data.get('object_type', 'item'),
                location_type=object_data.get('location_type', 'room'),
                location_id=object_data.get('location_id'),
                properties=object_data.get('properties', {}),
                created_at=datetime.now()
            )
            created_object = await self._object_repo.create(game_object.to_dict())
            logger.info(f"새 게임 객체 생성됨: {created_object.id}")
            return created_object
        except Exception as e:
            logger.error(f"게임 객체 생성 실패: {e}")
            raise

    async def update_game_object(self, object_id: str, updates: Dict[str, Any]) -> Optional[GameObject]:
        """게임 객체 정보를 수정합니다."""
        try:
            existing_object = await self.get_game_object(object_id)
            if not existing_object:
                logger.warning(f"수정하려는 객체가 존재하지 않음: {object_id}")
                return None

            for key, value in updates.items():
                if hasattr(existing_object, key):
                    setattr(existing_object, key, value)

            updated_object = await self._object_repo.update(object_id, existing_object.to_dict())
            if updated_object:
                logger.info(f"게임 객체 정보 수정됨: {object_id}")
            return updated_object
        except Exception as e:
            logger.error(f"게임 객체 수정 실패 ({object_id}): {e}")
            raise

    async def delete_game_object(self, object_id: str) -> bool:
        """게임 객체를 삭제합니다."""
        try:
            success = await self._object_repo.delete(object_id)
            if success:
                logger.info(f"게임 객체 삭제됨: {object_id}")
            return success
        except Exception as e:
            logger.error(f"게임 객체 삭제 실패 ({object_id}): {e}")
            raise

    async def get_room_objects(self, room_id: str) -> List[GameObject]:
        """특정 방에 있는 모든 객체를 조회합니다."""
        try:
            return await self._object_repo.get_objects_in_room(room_id)
        except Exception as e:
            logger.error(f"방 내 객체 조회 실패 ({room_id}): {e}")
            raise

    async def get_inventory_objects(self, character_id: str) -> List[GameObject]:
        """특정 캐릭터의 인벤토리 객체들을 조회합니다."""
        try:
            return await self._object_repo.get_objects_in_inventory(character_id)
        except Exception as e:
            logger.error(f"인벤토리 객체 조회 실패 ({character_id}): {e}")
            raise

    async def move_object_to_room(self, object_id: str, room_id: str, room_manager=None) -> bool:
        """객체를 특정 방으로 이동시킵니다."""
        try:
            if room_manager:
                room = await room_manager.get_room(room_id)
                if not room:
                    logger.warning(f"대상 방이 존재하지 않음: {room_id}")
                    return False

            updated_object = await self._object_repo.move_object_to_room(object_id, room_id)
            success = updated_object is not None
            if success:
                logger.info(f"객체 {object_id}를 방 {room_id}로 이동")
            return success
        except Exception as e:
            logger.error(f"객체 방 이동 실패 ({object_id} -> {room_id}): {e}")
            raise

    async def move_object_to_inventory(self, object_id: str, character_id: str) -> bool:
        """객체를 특정 캐릭터의 인벤토리로 이동시킵니다."""
        try:
            updated_object = await self._object_repo.move_object_to_inventory(object_id, character_id)
            success = updated_object is not None
            if success:
                logger.info(f"객체 {object_id}를 캐릭터 {character_id}의 인벤토리로 이동")
            return success
        except Exception as e:
            logger.error(f"객체 인벤토리 이동 실패 ({object_id} -> {character_id}): {e}")
            raise

    async def find_objects_by_name(self, name_pattern: str, locale: str = 'en') -> List[GameObject]:
        """이름 패턴으로 게임 객체를 검색합니다."""
        try:
            return await self._object_repo.find_objects_by_name(name_pattern, locale)
        except Exception as e:
            logger.error(f"객체 이름 검색 실패 ({name_pattern}): {e}")
            raise

    async def get_objects_by_type(self, object_type: str) -> List[GameObject]:
        """특정 타입의 모든 객체를 조회합니다."""
        try:
            return await self._object_repo.get_objects_by_type(object_type)
        except Exception as e:
            logger.error(f"타입별 객체 조회 실패 ({object_type}): {e}")
            raise

    async def update_object(self, game_object: GameObject) -> bool:
        """게임 객체를 업데이트합니다."""
        try:
            updated_object = await self._object_repo.update(game_object.id, game_object.to_dict())
            if updated_object:
                logger.info(f"게임 객체 업데이트됨: {game_object.id}")
                return True
            return False
        except Exception as e:
            logger.error(f"게임 객체 업데이트 실패 ({game_object.id}): {e}")
            raise

    async def remove_object(self, object_id: str) -> bool:
        """게임 객체를 제거합니다."""
        try:
            success = await self._object_repo.delete(object_id)
            if success:
                logger.info(f"게임 객체 제거됨: {object_id}")
            return success
        except Exception as e:
            logger.error(f"게임 객체 제거 실패 ({object_id}): {e}")
            raise

    async def get_equipped_objects(self, character_id: str) -> List[GameObject]:
        """특정 캐릭터가 착용 중인 장비들을 조회합니다."""
        try:
            inventory_objects = await self.get_inventory_objects(character_id)
            return [obj for obj in inventory_objects if obj.is_equipped]
        except Exception as e:
            logger.error(f"착용 장비 조회 실패 ({character_id}): {e}")
            raise

    async def get_objects_by_category(self, character_id: str, category: str) -> List[GameObject]:
        """특정 캐릭터의 인벤토리에서 카테고리별 객체들을 조회합니다."""
        try:
            inventory_objects = await self.get_inventory_objects(character_id)
            return [obj for obj in inventory_objects if obj.category == category]
        except Exception as e:
            logger.error(f"카테고리별 객체 조회 실패 ({character_id}, {category}): {e}")
            raise
