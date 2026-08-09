# -*- coding: utf-8 -*-
"""채팅 처리

채팅은 액션이 아니라 별도 메시지 타입이다. 게임 상태를 바꾸지 않고 본문을
번역하지 않으므로 디스패처를 거치지 않는다.

서버는 길이 검증과 제어문자 제거만 수행한다. `say` 와 `whisper` 명령어를 대체한다.

프로토콜 계약: docs/protocol/client-to-server.md
"""

import logging
from typing import Any, Optional

from .serialization import build_chat, error as protocol_error
from ..core.types import SessionType

logger = logging.getLogger(__name__)

# 본문 최대 길이
MAX_MESSAGE_LENGTH = 500

# 허용 채널
CHANNEL_ROOM = "room"
CHANNEL_WHISPER = "whisper"
VALID_CHANNELS = (CHANNEL_ROOM, CHANNEL_WHISPER)


def sanitise(message: str) -> str:
    """제어문자를 제거하고 앞뒤 공백을 다듬는다.

    개행은 라인 프로토콜의 경계를 깨뜨리지 않지만(JSON 문자열로 이스케이프됨)
    한 줄 채팅에 여러 줄을 담을 이유가 없으므로 제거한다.
    """
    cleaned = "".join(ch for ch in message if ch == " " or not _is_control(ch))
    return cleaned.strip()


def _is_control(ch: str) -> bool:
    """제어문자인지 판별한다."""
    code = ord(ch)
    return code < 0x20 or code == 0x7F


class ChatRouter:
    """채팅 메시지를 대상에게 전달한다."""

    def __init__(self, game_engine: Any) -> None:
        self.game_engine = game_engine

    async def handle(self, session: SessionType, message: dict[str, Any]) -> None:
        """chat 메시지를 처리한다.

        Args:
            session: 발신 세션
            message: 봉투 검증을 통과한 chat 메시지
        """
        seq = message.get("seq")

        if session.player is None:
            await session.send_message(
                protocol_error("NOT_AUTHENTICATED", "chat requires authentication", seq)
            )
            return

        channel = message.get("channel")
        if channel not in VALID_CHANNELS:
            await session.send_message(
                protocol_error(
                    "MALFORMED_MESSAGE", f"channel must be one of {VALID_CHANNELS}", seq
                )
            )
            return

        raw = message.get("message")
        if not isinstance(raw, str):
            await session.send_message(
                protocol_error("MALFORMED_MESSAGE", "message must be a string", seq)
            )
            return

        body = sanitise(raw)
        if not body:
            await session.send_message(
                protocol_error("MALFORMED_MESSAGE", "message is empty", seq)
            )
            return

        if len(body) > MAX_MESSAGE_LENGTH:
            await session.send_message(
                protocol_error(
                    "MALFORMED_MESSAGE",
                    f"message exceeds {MAX_MESSAGE_LENGTH} characters",
                    seq,
                )
            )
            return

        if channel == CHANNEL_WHISPER:
            await self._whisper(session, message.get("to"), body, seq)
            return

        await self._room(session, body, seq)

    async def _room(
        self, session: SessionType, body: str, seq: Optional[int]
    ) -> None:
        """같은 방 전체에 전달한다. 발신자에게도 되돌려 준다."""
        room_id = getattr(session, "current_room_id", None)
        if not room_id:
            await session.send_message(
                protocol_error("WRONG_STATE", "no current room", seq)
            )
            return

        assert session.player is not None
        payload = build_chat(CHANNEL_ROOM, session.player, body)

        await self.game_engine.broadcast_to_room(
            room_id, payload, exclude_session=session.session_id
        )
        await session.send_message(
            build_chat(CHANNEL_ROOM, session.player, body, seq=seq)
        )

    async def _whisper(
        self,
        session: SessionType,
        recipient_id: Any,
        body: str,
        seq: Optional[int],
    ) -> None:
        """지정한 플레이어에게만 전달한다.

        방 제한을 두지 않는다. `who_result` 로 얻은 uuid 로 어디서든 보낼 수 있다.
        기존 whisper 명령어는 같은 방만 허용했으나 계약은 그 제한을 두지 않는다.
        """
        if not isinstance(recipient_id, str) or not recipient_id:
            await session.send_message(
                protocol_error(
                    "MALFORMED_MESSAGE", "whisper requires a recipient uuid", seq
                )
            )
            return

        target = self._find_session(recipient_id)
        if target is None or target.session_id == session.session_id:
            await session.send_message(
                protocol_error("NOT_FOUND", "recipient is not online", seq)
            )
            return

        assert session.player is not None

        await target.send_message(build_chat(CHANNEL_WHISPER, session.player, body))
        await session.send_message(
            build_chat(CHANNEL_WHISPER, session.player, body, seq=seq)
        )

    def _find_session(self, player_id: str) -> Optional[Any]:
        """플레이어 uuid 로 접속 세션을 찾는다."""
        sessions = self.game_engine.session_manager.get_authenticated_sessions()

        for candidate in sessions:
            if candidate.player and candidate.player.id == player_id:
                return candidate

        return None
