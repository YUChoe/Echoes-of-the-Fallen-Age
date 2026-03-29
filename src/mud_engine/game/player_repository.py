# -*- coding: utf-8 -*-
"""플레이어 리포지토리"""

import logging
from typing import Optional

from ..database.repository import BaseRepository
from .models import Player

logger = logging.getLogger(__name__)


class PlayerRepository(BaseRepository[Player]):
    """플레이어 리포지토리"""

    def get_table_name(self) -> str:
        return "players"

    def get_model_class(self):
        return Player

    async def get_by_username(self, username: str) -> Optional[Player]:
        """사용자명으로 플레이어 조회"""
        try:
            results = await self.find_by(username=username)
            return results[0] if results else None
        except Exception as e:
            logger.error(f"사용자명으로 플레이어 조회 실패 ({username}): {e}")
            raise

    async def username_exists(self, username: str) -> bool:
        """사용자명 중복 확인"""
        try:
            player = await self.get_by_username(username)
            return player is not None
        except Exception as e:
            logger.error(f"사용자명 중복 확인 실패 ({username}): {e}")
            raise

    async def update_last_login(self, player_id: str) -> Optional[Player]:
        """마지막 로그인 시간 업데이트"""
        from datetime import datetime
        try:
            return await self.update(player_id, {'last_login': datetime.now().isoformat()})
        except Exception as e:
            logger.error(f"마지막 로그인 시간 업데이트 실패 ({player_id}): {e}")
            raise
