# -*- coding: utf-8 -*-
"""Enter 명령어 구현"""

import logging

from typing import List, Optional, Dict, Any
from ..base import BaseCommand, CommandResult, CommandResultType
from ...core.types import SessionType
from ...core.localization import get_localization_manager
from ...server.telnet_session import TelnetSession


class EnterCommand(BaseCommand):
    """Enter 명령어 - 특별한 장소로 들어가기"""

    def __init__(self):
        super().__init__(
            name="enter",
            aliases=["enter", "go_in", "진입"],
            description="Enter a special location or passage",
            usage="enter"
        )
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _get_text(self, session: SessionType, key: str) -> str:
        """세션의 언어 설정에 따라 텍스트 가져오기"""
        localization = get_localization_manager()
        locale = getattr(session, 'locale', 'en')
        return localization.get_message(key, locale)

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        """Enter 명령어 실행"""
        if not session.player:
            return self.create_error_result(self._get_text(session, "enter.login_required"))

        # 게임 엔진 가져오기
        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result(self._get_text(session, "enter.game_engine_error"))

        # 현재 방 ID 확인
        current_room_id = getattr(session, 'current_room_id', None)
        if not current_room_id:
            return self.create_error_result(self._get_text(session, "enter.location_error"))

        # 현재 방 정보 가져오기
        current_room = await game_engine.world_manager.get_room(current_room_id)
        if not current_room or current_room.x is None or current_room.y is None:
            return self.create_error_result(self._get_text(session, "enter.coordinates_error"))

        current_x = current_room.x
        current_y = current_room.y

        self.logger.info(f"Enter 명령어 실행: 플레이어 {session.player.username}, 현재 위치 ({current_x}, {current_y})")

        # 현재 위치에서 연결된 곳이 있는지 확인
        connection = await self._get_room_connection(session, current_x, current_y)

        if not connection:
            return self.create_error_result(self._get_text(session, "enter.no_entrance"))

        # 목적지로 이동
        target_x = connection['to_x']
        target_y = connection['to_y']

        try:
            # 플레이어 위치 업데이트
            await game_engine.movement_manager.move_player_to_coordinates(
                session, target_x, target_y
            )

            # 이동 메시지 전송
            await session.send_message({
                "type": "movement",
                "message": self._get_text(session, "enter.moved_through_passage")
            })

            self.logger.info(f"플레이어 {session.player.username}가 enter로 ({current_x},{current_y}) -> ({target_x},{target_y}) 이동")

            return self.create_success_result(self._get_text(session, "enter.movement_complete"))

        except Exception as e:
            self.logger.error(f"Enter 이동 실패: {e}")
            return self.create_error_result(self._get_text(session, "enter.movement_error"))

    async def _get_room_connection(self, session: SessionType, from_x: int, from_y: int) -> Optional[Dict[str, Any]]:
        """현재 위치에서 연결된 방 정보 조회"""
        try:
            game_engine = getattr(session, 'game_engine', None)
            if not game_engine:
                return None

            cursor = await game_engine.db_manager.execute(
                "SELECT to_x, to_y FROM room_connections WHERE from_x = ? AND from_y = ?",
                (from_x, from_y)
            )
            result = await cursor.fetchone()

            if result:
                return {
                    'to_x': result[0],
                    'to_y': result[1]
                }
            return None

        except Exception as e:
            self.logger.error(f"방 연결 조회 실패: {e}")
            return None