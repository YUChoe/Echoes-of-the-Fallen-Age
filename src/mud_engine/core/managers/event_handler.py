# -*- coding: utf-8 -*-
"""이벤트 핸들러"""

import logging
from typing import TYPE_CHECKING, Dict, Any, Optional
from datetime import datetime

from ..event_bus import Event, EventType
from ...server.serialization import build_event

if TYPE_CHECKING:
    from ..game_engine import GameEngine

logger = logging.getLogger(__name__)


class EventHandler:
    """게임 이벤트 처리를 담당하는 핸들러"""

    def __init__(self, game_engine: 'GameEngine'):
        self.game_engine = game_engine

    def setup_event_subscriptions(self) -> None:
        """이벤트 구독 설정"""
        # 플레이어 관련 이벤트 구독
        self.game_engine.event_bus.subscribe(EventType.PLAYER_CONNECTED, self._on_player_connected)
        self.game_engine.event_bus.subscribe(EventType.PLAYER_DISCONNECTED, self._on_player_disconnected)
        self.game_engine.event_bus.subscribe(EventType.PLAYER_LOGIN, self._on_player_login)
        self.game_engine.event_bus.subscribe(EventType.PLAYER_LOGOUT, self._on_player_logout)
        self.game_engine.event_bus.subscribe(EventType.PLAYER_COMMAND, self._on_player_command)

        # 방 관련 이벤트 구독
        self.game_engine.event_bus.subscribe(EventType.ROOM_ENTERED, self._on_room_entered)
        self.game_engine.event_bus.subscribe(EventType.ROOM_LEFT, self._on_room_left)
        self.game_engine.event_bus.subscribe(EventType.ROOM_MESSAGE, self._on_room_message)

        # 플레이어 상호작용 이벤트 구독
        self.game_engine.event_bus.subscribe(EventType.PLAYER_ACTION, self._on_player_action)
        self.game_engine.event_bus.subscribe(EventType.PLAYER_EMOTE, self._on_player_emote)
        self.game_engine.event_bus.subscribe(EventType.PLAYER_FOLLOW, self._on_player_follow)
        self.game_engine.event_bus.subscribe(EventType.OBJECT_PICKED_UP, self._on_object_picked_up)
        self.game_engine.event_bus.subscribe(EventType.OBJECT_DROPPED, self._on_object_dropped)

        # 시스템 이벤트 구독
        self.game_engine.event_bus.subscribe(EventType.SERVER_STARTED, self._on_server_started)
        self.game_engine.event_bus.subscribe(EventType.SERVER_STOPPING, self._on_server_stopping)

        logger.info("이벤트 구독 설정 완료")

    # === 플레이어 이벤트 핸들러들 ===

    async def _on_player_connected(self, event: Event) -> None:
        """플레이어 연결 이벤트 핸들러"""
        data = event.data
        session_id = data.get('session_id', '')
        short_session_id = session_id.split('-')[-1] if '-' in session_id else session_id
        logger.info(f"플레이어 연결: {data.get('username')} (세션: {short_session_id})")

    async def _on_player_disconnected(self, event: Event) -> None:
        """플레이어 연결 해제 이벤트 핸들러"""
        data = event.data
        username = data.get('username', '알 수 없음')
        reason = data.get('reason', '알 수 없는 이유')
        logger.info(f"플레이어 연결 해제: {username} (이유: {reason})")

    async def _on_player_login(self, event: Event) -> None:
        """플레이어 로그인 이벤트 핸들러"""
        username = event.data.get('username')

        await self._announce_to_others(
            username, "game.player_joined", category="social"
        )

        logger.info(f"플레이어 로그인 알림 브로드캐스트: {username}")

    async def _on_player_logout(self, event: Event) -> None:
        """플레이어 로그아웃 이벤트 핸들러"""
        username = event.data.get('username')

        await self._announce_to_others(
            username, "game.player_left", category="social"
        )

        logger.info(f"플레이어 로그아웃 알림 브로드캐스트: {username}")

    async def _announce_to_others(
        self, username: Optional[str], key: str, category: str = "system"
    ) -> None:
        """본인을 제외한 모든 세션에 번역 키 알림을 보낸다.

        키를 전달하므로 수신자가 각자의 언어로 번역한다. 기존에는 발신 시점에
        문장을 만들어 보내며 세션 속성 `language` 를 참조했는데, 그 속성은
        존재하지 않아 항상 영어로 나갔다.
        """
        payload = build_event(key, {"username": username}, category=category)

        for session in self.game_engine.session_manager.sessions.values():
            if session.player and session.player.username != username:
                await session.send_message(payload)

    async def _on_player_command(self, event: Event) -> None:
        """플레이어 명령어 이벤트 핸들러"""
        data = event.data
        username = data.get('username')
        command = data.get('command')
        logger.debug(f"플레이어 명령어: {username} -> {command}")

    # === 방 이벤트 핸들러들 ===

    async def _on_room_entered(self, event: Event) -> None:
        """방 입장 이벤트 핸들러"""
        data = event.data
        username = data.get('username')
        room_id = event.room_id
        
        # 방 좌표 가져오기
        try:
            room = await self.game_engine.world_manager.get_room(room_id)
            if room:
                coord = f"({room.x}, {room.y})"
            else:
                coord = "알 수 없음"
        except Exception:
            coord = "알 수 없음"
        
        logger.info(f"방 입장: {username} -> {coord}")

    async def _on_room_left(self, event: Event) -> None:
        """방 퇴장 이벤트 핸들러"""
        data = event.data
        username = data.get('username')
        room_id = event.room_id
        
        # 방 정보를 가져와서 좌표로 표시
        try:
            if self.game_engine and self.game_engine.world_manager:
                room = await self.game_engine.world_manager.get_room(room_id)
                if room and hasattr(room, 'x') and hasattr(room, 'y'):
                    coord = f"({room.x}, {room.y})"
                else:
                    coord = f"방 {room_id}"
            else:
                coord = f"방 {room_id}"
        except Exception:
            coord = f"방 {room_id}"
        
        logger.info(f"방 퇴장: {username} <- {coord}")

    async def _on_room_message(self, event: Event) -> None:
        """방 메시지 이벤트 핸들러"""
        data = event.data
        username = data.get('username')
        message = data.get('message')
        room_id = event.room_id
        logger.debug(f"방 메시지: {username} (방 {room_id}) -> {message}")

    # === 플레이어 상호작용 이벤트 핸들러들 ===

    async def _on_player_action(self, event: Event) -> None:
        """플레이어 액션 이벤트 핸들러"""
        data = event.data
        username = data.get('username')
        action = data.get('action')
        room_id = event.room_id
        logger.debug(f"플레이어 액션: {username} (방 {room_id}) -> {action}")

    # 아래 세 핸들러는 로그만 남긴다. 플레이어에게 보내는 알림은 액션 핸들러가
    # `BroadcastSpec` 으로 이미 처리한다(`emote.*.other`, `follow.broadcast`,
    # `obj.get.broadcast`, `obj.drop.broadcast`). 여기서 다시 보내면 같은 사건이
    # 두 번 전달되고, 계약에 없는 타입으로 나가 클라이언트가 버린다.

    async def _on_player_emote(self, event: Event) -> None:
        """플레이어 감정 표현 이벤트 핸들러"""
        data = event.data
        logger.info(
            f"플레이어 감정 표현: {data.get('username')} "
            f"(방 {event.room_id}) -> {data.get('emote_id') or data.get('emote_text')}"
        )

    async def _on_player_follow(self, event: Event) -> None:
        """플레이어 따라가기 이벤트 핸들러"""
        data = event.data
        logger.info(
            f"플레이어 따라가기: {data.get('follower_name')} -> "
            f"{data.get('target_name')} (방 {event.room_id})"
        )

    async def _on_object_picked_up(self, event: Event) -> None:
        """객체 획득 이벤트 핸들러"""
        data = event.data
        logger.info(
            f"객체 획득: {data.get('player_name')} -> {data.get('object_name')} "
            f"(방 {event.room_id})"
        )

    async def _on_object_dropped(self, event: Event) -> None:
        """객체 드롭 이벤트 핸들러"""
        data = event.data
        logger.info(
            f"객체 드롭: {data.get('player_name')} -> {data.get('object_name')} "
            f"(방 {event.room_id})"
        )

    # === 시스템 이벤트 핸들러들 ===

    async def _on_server_started(self, event: Event) -> None:
        """서버 시작 이벤트 핸들러"""
        logger.info("서버 시작 이벤트 수신")

    async def _on_server_stopping(self, event: Event) -> None:
        """서버 중지 이벤트 핸들러"""
        logger.info("서버 중지 이벤트 수신")

    # 채팅 이벤트 핸들러 세 개(`handle_chat_message`, `handle_room_chat_message`,
    # `handle_private_message`)를 제거했다. 호출처가 없었고 존재하지 않는
    # `chat_manager` 속성을 참조했다. 채팅은 `server/chat.py` 가 계약의 `chat`
    # 타입으로 처리한다.
        return None