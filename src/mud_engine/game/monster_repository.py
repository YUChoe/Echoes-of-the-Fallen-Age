# -*- coding: utf-8 -*-
"""몬스터 리포지토리"""

import logging
from typing import List, Optional

from ..database.repository import BaseRepository
from .models import GameObject
from .monster import Monster

logger = logging.getLogger(__name__)


class MonsterRepository(BaseRepository):
    """몬스터 리포지토리"""

    def get_table_name(self) -> str:
        return "monsters"

    def get_model_class(self):
        from .monster import Monster
        return Monster

    async def get_monsters_at_coordinates(self, x: int, y: int) -> List[Monster]:
        """특정 좌표에 있는 살아있는 몬스터들을 조회합니다."""
        try:
            monsters = await self.find_by(x=x, y=y, is_alive=True)
            logger.debug(f"좌표 ({x}, {y})에서 {len(monsters)}마리 몬스터 조회")
            return monsters
        except Exception as e:
            logger.error(f"좌표 내 몬스터 조회 실패 ({x}, {y}): {e}")
            return []

    async def get_monsters_in_room(self, room_id: str) -> List[Monster]:
        """특정 방에 있는 살아있는 몬스터들을 조회합니다 (레거시 호환용)."""
        try:
            # room_id로 방의 좌표를 찾아서 해당 좌표의 몬스터들을 조회
            from .managers.room_manager import RoomManager
            # 임시로 빈 리스트 반환 (좌표 기반으로 변경 필요)
            logger.warning(f"get_monsters_in_room은 더 이상 사용되지 않습니다. get_monsters_at_coordinates를 사용하세요.")
            return []
        except Exception as e:
            logger.error(f"방 내 몬스터 조회 실패 ({room_id}): {e}")
            return []

    async def kill_monster(self, monster_id: str) -> bool:
        """몬스터 사망 처리"""
        try:
            from datetime import datetime
            current_time = datetime.now().isoformat()

            db_manager = await self.get_db_manager()
            await db_manager.execute(
                "UPDATE monsters SET is_alive = FALSE, last_death_time = ? WHERE id = ?",
                (current_time, monster_id)
            )
            await db_manager.commit()

            logger.info(f"몬스터 {monster_id} 사망 처리 완료")
            return True

        except Exception as e:
            logger.error(f"몬스터 사망 처리 실패: {e}")
            db_manager = await self.get_db_manager()
            await db_manager.rollback()
            return False

    async def respawn_monster(self, monster_id: str) -> bool:
        """몬스터 리스폰 처리"""
        try:
            import json

            # 몬스터 정보 조회
            monster = await self.get_by_id(monster_id)
            if not monster:
                logger.error(f"몬스터 {monster_id}를 찾을 수 없습니다")
                return False

            # 좌표는 그대로 유지 (원래 스폰 위치에서 리스폰)

            # 능력치를 최대치로 복구
            monster.stats.current_hp = monster.stats.max_hp
            stats_json = json.dumps(monster.stats.to_dict(), ensure_ascii=False)

            db_manager = await self.get_db_manager()
            await db_manager.execute("""
                UPDATE monsters
                SET is_alive = TRUE,
                    last_death_time = NULL,
                    stats = ?
                WHERE id = ?
            """, (stats_json, monster_id))

            await db_manager.commit()

            logger.info(f"몬스터 {monster_id} 리스폰 완료")
            return True

        except Exception as e:
            logger.error(f"몬스터 리스폰 실패: {e}")
            db_manager = await self.get_db_manager()
            await db_manager.rollback()
            return False

    async def move_object_to_container(self, object_id: str, container_id: str) -> Optional[GameObject]:
        """객체를 컨테이너로 이동"""
        try:
            return await self.update(object_id, {
                'location_type': 'CONTAINER',
                'location_id': container_id
            })
        except Exception as e:
            logger.error(f"객체 컨테이너 이동 실패 ({object_id} -> {container_id}): {e}")
            raise
