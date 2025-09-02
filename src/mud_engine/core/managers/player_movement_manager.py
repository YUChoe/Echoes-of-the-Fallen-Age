# -*- coding: utf-8 -*-
"""플레이어 이동 관리자"""

import logging
from typing import TYPE_CHECKING, Optional
from datetime import datetime

from ..event_bus import Event, EventType

if TYPE_CHECKING:
    from ..game_engine import GameEngine
    from ...server.session import Session

logger = logging.getLogger(__name__)


class PlayerMovementManager:
    """플레이어 이동 및 따라가기 시스템을 담당하는 매니저"""

    def __init__(self, game_engine: 'GameEngine'):
        self.game_engine = game_engine

    async def move_player_to_room(self, session: 'Session', room_id: str, skip_followers: bool = False) -> bool:
        """
        플레이어를 특정 방으로 이동시킵니다.

        Args:
            session: 플레이어 세션
            room_id: 목적지 방 ID
            skip_followers: 따라가는 플레이어들 이동 생략 여부

        Returns:
            bool: 이동 성공 여부
        """
        if not session.is_authenticated or not session.player:
            return False

        try:
            logger.debug(f"플레이어 이동 시작: {session.player.username} -> {room_id}")

            # 방이 존재하는지 확인
            room = await self.game_engine.world_manager.get_room(room_id)
            if not room:
                logger.warning(f"존재하지 않는 방으로 이동 시도: {room_id} (플레이어: {session.player.username})")
                await session.send_error("존재하지 않는 방입니다.")
                return False

            # 이전 방 ID 저장
            old_room_id = getattr(session, 'current_room_id', None)

            # 세션의 현재 방 업데이트
            session.current_room_id = room_id

            # 방 퇴장 이벤트 발행 (이전 방이 있는 경우)
            if old_room_id:
                await self.game_engine.event_bus.publish(Event(
                    event_type=EventType.ROOM_LEFT,
                    source=session.session_id,
                    room_id=old_room_id,
                    data={
                        "player_id": session.player.id,
                        "username": session.player.username,
                        "session_id": session.session_id,
                        "old_room_id": old_room_id,
                        "new_room_id": room_id
                    }
                ))

            # 방 입장 이벤트 발행
            await self.game_engine.event_bus.publish(Event(
                event_type=EventType.ROOM_ENTERED,
                source=session.session_id,
                room_id=room_id,
                data={
                    "player_id": session.player.id,
                    "username": session.player.username,
                    "session_id": session.session_id,
                    "room_id": room_id,
                    "old_room_id": old_room_id
                }
            ))

            # 이전 방의 다른 플레이어들에게 퇴장 알림
            if old_room_id:
                leave_message = {
                    "type": "room_message",
                    "message": f"🚶 {session.player.username}님이 떠났습니다.",
                    "timestamp": datetime.now().isoformat()
                }
                await self.game_engine.broadcast_to_room(old_room_id, leave_message, exclude_session=session.session_id)

            # 새 방의 다른 플레이어들에게 입장 알림
            enter_message = {
                "type": "room_message",
                "message": f"🚶 {session.player.username}님이 도착했습니다.",
                "timestamp": datetime.now().isoformat()
            }
            await self.game_engine.broadcast_to_room(room_id, enter_message, exclude_session=session.session_id)

            # 따라가는 플레이어들도 함께 이동 - skip_followers가 False인 경우에만
            if not skip_followers:
                await self.handle_player_movement_with_followers(session, room_id, old_room_id)

            # 방 플레이어 목록 업데이트 (이전 방과 새 방 모두)
            if old_room_id:
                await self.update_room_player_list(old_room_id)
            await self.update_room_player_list(room_id)

            # 방 정보를 플레이어에게 전송 (follower든 아니든 항상 전송)
            await self.send_room_info_to_player(session, room_id)

            logger.info(f"플레이어 {session.player.username}이 방 {room_id}로 이동")
            return True

        except Exception as e:
            logger.error(f"플레이어 방 이동 실패 ({session.player.username} -> {room_id}): {e}")
            await session.send_error("방 이동 중 오류가 발생했습니다.")
            return False

    async def send_room_info_to_player(self, session: 'Session', room_id: str) -> None:
        """
        플레이어에게 방 정보를 전송합니다.

        Args:
            session: 플레이어 세션
            room_id: 방 ID
        """
        try:
            room_info = await self.game_engine.get_room_info(room_id, session.locale)
            if room_info:
                # 디버깅: 몬스터 정보 로깅
                monsters = room_info.get('monsters', [])
                logger.debug(f"방 {room_id}에서 {len(monsters)}마리 몬스터 발견")
                for i, monster in enumerate(monsters):
                    logger.debug(f"몬스터 {i+1}: {monster.get_localized_name(session.locale)}, 타입: {monster.monster_type}, 행동: {monster.behavior}")
                room_data = {
                    "id": room_info['room'].id,
                    "name": room_info['room'].get_localized_name(session.locale),
                    "description": room_info['room'].get_localized_description(session.locale),
                    "exits": room_info['exits'],
                    "objects": [
                        {
                            "id": obj.id,
                            "name": obj.get_localized_name(session.locale),
                            "type": obj.object_type
                        }
                        for obj in room_info['objects']
                    ],
                    "monsters": [
                        {
                            "id": monster.id,
                            "name": monster.get_localized_name(session.locale),
                            "level": monster.level,
                            "current_hp": monster.current_hp,
                            "max_hp": monster.max_hp,
                            "monster_type": monster.monster_type.value if hasattr(monster.monster_type, 'value') else str(monster.monster_type),
                            "behavior": monster.behavior.value if hasattr(monster.behavior, 'value') else str(monster.behavior),
                            "is_aggressive": monster.is_aggressive(),
                            "is_passive": monster.is_passive(),
                            "is_neutral": monster.is_neutral()
                        }
                        for monster in room_info.get('monsters', [])
                    ]
                }

                await session.send_message({
                    "type": "room_info",
                    "room": room_data
                })

                # UI 업데이트 정보 전송
                await self.game_engine.ui_manager.send_ui_update(session, room_info)

                logger.debug(f"방 정보 전송 완료: {session.player.username} -> 방 {room_id}")

        except Exception as e:
            logger.error(f"방 정보 전송 실패 ({session.player.username}, {room_id}): {e}")

    async def handle_player_movement_with_followers(self, session: 'Session', new_room_id: str, old_room_id: Optional[str] = None) -> None:
        """
        플레이어 이동 시 따라가는 플레이어들도 함께 이동시킵니다.

        Args:
            session: 이동하는 플레이어의 세션
            new_room_id: 새로운 방 ID
            old_room_id: 이전 방 ID (따라가는 플레이어들을 찾기 위해 필요)
        """
        if not session.player or not old_room_id:
            return

        # 이 플레이어를 따라가는 다른 플레이어들 찾기 (이전 방에서)
        followers = []

        for other_session in self.game_engine.session_manager.get_authenticated_sessions().values():
            if (other_session.player and
                other_session.session_id != session.session_id and
                getattr(other_session, 'current_room_id', None) == old_room_id and
                getattr(other_session, 'following_player', None) == session.player.username):
                followers.append(other_session)

        if followers:
            logger.info(f"따라가는 플레이어 {len(followers)}명 발견: {[f.player.username for f in followers]}")
        else:
            logger.debug(f"따라가는 플레이어 없음 (리더: {session.player.username}, 이전 방: {old_room_id})")

        # 따라가는 플레이어들을 함께 이동
        for follower_session in followers:
            try:
                # 따라가는 플레이어에게 알림
                await follower_session.send_message({
                    "type": "following_movement",
                    "message": f"👥 {session.player.username}님을 따라 이동합니다..."
                })

                # 실제 이동 수행 (무한 재귀 방지를 위해 skip_followers=True)
                success = await self.move_player_to_room(follower_session, new_room_id, skip_followers=True)

                if success:
                    # 이동 성공 시 follower에게 이동 완료 메시지 전송
                    await follower_session.send_message({
                        "type": "following_movement_complete",
                        "message": f"👥 {session.player.username}님을 따라 이동했습니다."
                    })

                    logger.info(f"따라가기 이동 완료: {follower_session.player.username} -> 방 {new_room_id}")
                else:
                    # 이동 실패 시 따라가기 중지
                    if hasattr(follower_session, 'following_player'):
                        delattr(follower_session, 'following_player')

                    await follower_session.send_error(
                        f"{session.player.username}님을 따라가지 못했습니다. 따라가기가 중지됩니다."
                    )

            except Exception as e:
                logger.error(f"따라가기 이동 실패 ({follower_session.player.username}): {e}")
                # 오류 시 따라가기 중지
                if hasattr(follower_session, 'following_player'):
                    delattr(follower_session, 'following_player')

    async def update_room_player_list(self, room_id: str) -> None:
        """
        방의 플레이어 목록을 실시간으로 업데이트합니다.

        Args:
            room_id: 업데이트할 방 ID
        """
        try:
            # 방에 있는 모든 플레이어들 찾기
            players_in_room = []
            for session in self.game_engine.session_manager.get_authenticated_sessions().values():
                if (session.player and
                    getattr(session, 'current_room_id', None) == room_id):

                    player_info = {
                        "id": session.player.id,
                        "name": session.player.username,
                        "session_id": session.session_id,
                        "following": getattr(session, 'following_player', None)
                    }
                    players_in_room.append(player_info)

            # 방에 있는 모든 플레이어들에게 업데이트된 목록 전송
            update_message = {
                "type": "room_players_update",
                "room_id": room_id,
                "players": players_in_room,
                "player_count": len(players_in_room)
            }

            await self.game_engine.broadcast_to_room(room_id, update_message)
            logger.debug(f"방 {room_id} 플레이어 목록 업데이트: {len(players_in_room)}명")

        except Exception as e:
            logger.error(f"방 플레이어 목록 업데이트 실패 ({room_id}): {e}")

    async def handle_player_disconnect_cleanup(self, session: 'Session') -> None:
        """
        플레이어 연결 해제 시 따라가기 관련 정리 작업

        Args:
            session: 연결 해제된 플레이어의 세션
        """
        if not session.player:
            return

        try:
            disconnected_player = session.player.username

            # 이 플레이어를 따라가던 다른 플레이어들의 따라가기 해제
            for other_session in self.game_engine.session_manager.get_authenticated_sessions().values():
                if (other_session.player and
                    hasattr(other_session, 'following_player') and
                    other_session.following_player == disconnected_player):

                    # 따라가기 해제
                    delattr(other_session, 'following_player')

                    # 알림 전송
                    await other_session.send_message({
                        "type": "follow_stopped",
                        "message": f"👥 {disconnected_player}님이 연결을 해제하여 따라가기가 중지되었습니다.",
                        "reason": "player_disconnected"
                    })

            logger.info(f"플레이어 연결 해제 정리 완료: {disconnected_player}")

        except Exception as e:
            logger.error(f"플레이어 연결 해제 정리 실패: {e}")

    async def notify_player_status_change(self, player_id: str, status: str, data: dict = None) -> None:
        """
        플레이어 상태 변경을 다른 플레이어들에게 알립니다.

        Args:
            player_id: 상태가 변경된 플레이어 ID
            status: 상태 ('online', 'offline', 'busy', 'away' 등)
            data: 추가 데이터
        """
        try:
            # 상태 변경 이벤트 발행
            await self.game_engine.event_bus.publish(Event(
                event_type=EventType.PLAYER_STATUS_CHANGED,
                source=player_id,
                data={
                    "player_id": player_id,
                    "status": status,
                    "timestamp": datetime.now().isoformat(),
                    **(data or {})
                }
            ))

            # 전체 플레이어들에게 상태 변경 알림 (선택적)
            if status in ['online', 'offline']:
                player_session = None
                for session in self.game_engine.session_manager.get_authenticated_sessions().values():
                    if session.player and session.player.id == player_id:
                        player_session = session
                        break

                if player_session:
                    status_message = {
                        "type": "player_status_change",
                        "message": f"🔄 {player_session.player.username}님이 {status} 상태가 되었습니다.",
                        "player_name": player_session.player.username,
                        "status": status,
                        "timestamp": datetime.now().isoformat()
                    }

                    await self.game_engine.broadcast_to_all(status_message)

        except Exception as e:
            logger.error(f"플레이어 상태 변경 알림 실패 ({player_id}, {status}): {e}")