# -*- coding: utf-8 -*-
"""감정 표현 명령어"""

import logging
from typing import List

from .base import BaseCommand, CommandResult, CommandResultType
from ..core.types import SessionType
from ..core.event_bus import Event, EventType

logger = logging.getLogger(__name__)


class EmoteCommand(BaseCommand):
    """감정 표현 명령어 - 플레이어가 감정이나 행동을 표현"""

    def __init__(self):
        super().__init__(
            name="emote",
            aliases=["em", "me"],
            description="감정이나 행동을 표현합니다",
            usage="emote <행동/감정>"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        logger.debug(f"EmoteCommand 실행: 플레이어={session.player.username}, args={args}")

        if not args:
            logger.warning(f"EmoteCommand: 빈 인수 - 플레이어={session.player.username}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="표현할 감정이나 행동을 입력해주세요. 예: emote 웃는다"
            )

        emote_text = " ".join(args)
        player_name = session.player.username

        logger.info(f"플레이어 감정 표현: {player_name} -> {emote_text}")

        # 이벤트 발행
        await session.game_engine.event_bus.publish(Event(
            event_type=EventType.PLAYER_EMOTE,
            source=session.session_id,
            room_id=getattr(session, 'current_room_id', None),
            data={
                "player_id": session.player.id,
                "username": player_name,
                "emote_text": emote_text,
                "session_id": session.session_id
            }
        ))

        # 방 내 모든 플레이어에게 감정 표현 전송
        emote_message = f"* {player_name} {emote_text}"

        return CommandResult(
            result_type=CommandResultType.SUCCESS,
            message=f"당신은 {emote_text}",
            broadcast=True,
            broadcast_message=emote_message,
            room_only=True
        )
