# -*- coding: utf-8 -*-
"""이벤트 핸들러"""

import logging
from typing import TYPE_CHECKING, Dict, Any
from datetime import datetime

from ..event_bus import Event, EventType

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
        self.game_engine.event_bus.subscribe(EventType.PLAYER_GIVE, self._on_player_give)
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
        from ..localization import get_message
        
        data = event.data
        username = data.get('username')

        # 모든 세션에 각자의 언어로 로그인 알림 전송
        for session in self.game_engine.session_manager.sessions.values():
            if session.player and session.player.username != username:
                # 각 세션의 언어 설정에 맞는 메시지 생성
                locale = getattr(session, 'language', 'en')
                message = get_message("game.player_joined", locale, username=username)
                
                login_message = {
                    "type": "system_message",
                    "message": message,
                    "timestamp": event.timestamp.isoformat()
                }
                
                await session.send_message(login_message)

        logger.info(f"플레이어 로그인 알림 브로드캐스트: {username}")

    async def _on_player_logout(self, event: Event) -> None:
        """플레이어 로그아웃 이벤트 핸들러"""
        from ..localization import get_message
        
        data = event.data
        username = data.get('username')

        # 모든 세션에 각자의 언어로 로그아웃 알림 전송
        for session in self.game_engine.session_manager.sessions.values():
            if session.player and session.player.username != username:
                # 각 세션의 언어 설정에 맞는 메시지 생성
                locale = getattr(session, 'language', 'en')
                message = get_message("game.player_left", locale, username=username)
                
                logout_message = {
                    "type": "system_message",
                    "message": message,
                    "timestamp": event.timestamp.isoformat()
                }
                
                await session.send_message(logout_message)

        logger.info(f"플레이어 로그아웃 알림 브로드캐스트: {username}")

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

    async def _on_player_emote(self, event: Event) -> None:
        """플레이어 감정 표현 이벤트 핸들러"""
        data = event.data
        username = data.get('username')
        emote_text = data.get('emote_text')
        room_id = event.room_id

        logger.info(f"플레이어 감정 표현: {username} (방 {room_id}) -> {emote_text}")

        # 방 내 다른 플레이어들의 UI 업데이트 (필요시)
        await self.game_engine.movement_manager.update_room_player_list(room_id)

    async def _on_player_give(self, event: Event) -> None:
        """플레이어 아이템 주기 이벤트 핸들러"""
        data = event.data
        giver_name = data.get('giver_name')
        receiver_name = data.get('receiver_name')
        item_name = data.get('item_name')
        room_id = event.room_id

        logger.info(f"아이템 전달: {giver_name} -> {receiver_name} ({item_name}) (방 {room_id})")

        # 방 내 모든 플레이어들에게 인벤토리 업데이트 알림
        inventory_update_message = {
            "type": "inventory_update",
            "message": f"🎁 {giver_name}님이 {receiver_name}님에게 '{item_name}'을(를) 주었습니다.",
            "timestamp": datetime.now().isoformat()
        }

        await self.game_engine.broadcast_to_room(room_id, inventory_update_message)

    async def _on_player_follow(self, event: Event) -> None:
        """플레이어 따라가기 이벤트 핸들러"""
        data = event.data
        follower_name = data.get('follower_name')
        target_name = data.get('target_name')
        room_id = event.room_id

        logger.info(f"플레이어 따라가기: {follower_name} -> {target_name} (방 {room_id})")

        # 방 내 플레이어 목록 업데이트 (따라가기 상태 반영)
        await self.game_engine.movement_manager.update_room_player_list(room_id)

    async def _on_object_picked_up(self, event: Event) -> None:
        """객체 획득 이벤트 핸들러"""
        data = event.data
        player_name = data.get('player_name')  # username -> player_name으로 수정
        object_name = data.get('object_name')
        room_id = event.room_id

        logger.info(f"객체 획득: {player_name} -> {object_name} (방 {room_id})")

        # 방 내 다른 플레이어들에게 객체 상태 변경 알림
        pickup_message = {
            "type": "object_update",
            "message": f"📦 {player_name}님이 '{object_name}'을(를) 가져갔습니다.",
            "action": "picked_up",
            "player": player_name,
            "object": object_name,
            "timestamp": datetime.now().isoformat()
        }

        await self.game_engine.broadcast_to_room(room_id, pickup_message, exclude_session=event.source)

    async def _on_object_dropped(self, event: Event) -> None:
        """객체 드롭 이벤트 핸들러"""
        data = event.data
        player_name = data.get('player_name')  # username -> player_name으로 수정
        object_name = data.get('object_name')
        room_id = event.room_id

        logger.info(f"객체 드롭: {player_name} -> {object_name} (방 {room_id})")

        # 방 내 다른 플레이어들에게 객체 상태 변경 알림
        drop_message = {
            "type": "object_update",
            "message": f"📦 {player_name}님이 '{object_name}'을(를) 내려놓았습니다.",
            "action": "dropped",
            "player": player_name,
            "object": object_name,
            "timestamp": datetime.now().isoformat()
        }

        await self.game_engine.broadcast_to_room(room_id, drop_message, exclude_session=event.source)

    # === 시스템 이벤트 핸들러들 ===

    async def _on_server_started(self, event: Event) -> None:
        """서버 시작 이벤트 핸들러"""
        logger.info("서버 시작 이벤트 수신")

    async def _on_server_stopping(self, event: Event) -> None:
        """서버 중지 이벤트 핸들러"""
        logger.info("서버 중지 이벤트 수신")

    # === 채팅 이벤트 핸들러들 ===

    async def handle_chat_message(self, event_data: Dict[str, Any]):
        """채팅 메시지 이벤트 처리"""
        try:
            channel = event_data.get("channel")
            message_data = event_data.get("message")

            if not channel or not message_data:
                return

            # 채널 구독자들에게 메시지 전송
            chat_message = {
                "type": "chat_message",
                "channel": channel,
                "message": message_data,
                "timestamp": datetime.now().isoformat()
            }

            # OOC 채널의 경우 모든 온라인 플레이어에게 전송
            if channel == "ooc":
                await self.game_engine.session_manager.broadcast_to_all(chat_message)
            else:
                # 다른 채널의 경우 구독자만
                if hasattr(self.game_engine, 'chat_manager') and self.game_engine.chat_manager:
                    channel_obj = self.game_engine.chat_manager.channels.get(channel)
                    if channel_obj:
                        for player_id in channel_obj.members:
                            session = self._find_session_by_player_id(player_id)
                            if session:
                                await session.send_message(chat_message)

        except Exception as e:
            logger.error(f"채팅 메시지 이벤트 처리 실패: {e}")

    async def handle_room_chat_message(self, event_data: Dict[str, Any]):
        """방 채팅 메시지 이벤트 처리"""
        try:
            room_id = event_data.get("room_id")
            message_data = event_data.get("message")

            if not room_id or not message_data:
                return

            # 같은 방의 플레이어들에게 메시지 전송
            room_message = {
                "type": "room_chat_message",
                "room_id": room_id,
                "message": message_data,
                "timestamp": datetime.now().isoformat()
            }

            # 방에 있는 모든 플레이어에게 전송
            for session in self.game_engine.session_manager.sessions.values():
                if (hasattr(session, 'current_room_id') and
                    session.current_room_id == room_id):
                    await session.send_message(room_message)

        except Exception as e:
            logger.error(f"방 채팅 메시지 이벤트 처리 실패: {e}")

    async def handle_private_message(self, event_data: Dict[str, Any]):
        """개인 메시지 이벤트 처리"""
        try:
            player_ids = event_data.get("player_ids", [])
            message_data = event_data.get("message")

            if not player_ids or not message_data:
                return

            # 개인 메시지
            private_message = {
                "type": "private_message",
                "message": message_data,
                "timestamp": datetime.now().isoformat()
            }

            # 지정된 플레이어들에게 메시지 전송
            for player_id in player_ids:
                session = self._find_session_by_player_id(player_id)
                if session:
                    await session.send_message(private_message)

        except Exception as e:
            logger.error(f"개인 메시지 이벤트 처리 실패: {e}")

    def _find_session_by_player_id(self, player_id: str):
        """플레이어 ID로 세션 찾기"""
        for session in self.game_engine.session_manager.sessions.values():
            if session.player and session.player.id == player_id:
                return session
        return None