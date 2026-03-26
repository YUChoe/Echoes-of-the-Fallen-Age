# -*- coding: utf-8 -*-
"""모델 매니저 - 모든 리포지토리를 통합 관리"""

import logging

from .player_repository import PlayerRepository
from .room_repository import RoomRepository
from .game_object_repository import GameObjectRepository

logger = logging.getLogger(__name__)


class ModelManager:
    """모델 매니저 - 모든 리포지토리를 통합 관리"""

    def __init__(self, db_manager=None):
        """ModelManager 초기화"""
        self.players = PlayerRepository(db_manager)
        # self.characters = CharacterRepository(db_manager)
        self.rooms = RoomRepository(db_manager)
        self.game_objects = GameObjectRepository(db_manager)

        logger.info("ModelManager 초기화 완료")

    async def validate_object_location_reference(self, object_id: str) -> bool:
        """객체의 위치 참조 무결성 검증"""
        try:
            obj = await self.game_objects.get_by_id(object_id)
            if not obj or not obj.location_id:
                return True  # 위치가 설정되지 않은 경우는 유효

            if obj.location_type == 'room':
                room = await self.rooms.get_by_id(obj.location_id)
                return room is not None
            # elif obj.location_type == 'inventory':
            #     character = await self.characters.get_by_id(obj.location_id)
            #     return character is not None

            return False
        except Exception as e:
            logger.error(f"객체 위치 참조 검증 실패 ({object_id}): {e}")
            return False
