# -*- coding: utf-8 -*-
"""귓속말 명령어"""

import logging
from typing import List
from datetime import datetime

from ..base import BaseCommand, CommandResult, CommandResultType
from ...core.types import SessionType

logger = logging.getLogger(__name__)


# TODO: 테스트 필요
class WhisperCommand(BaseCommand):
    """다른 플레이어에게 귓속말"""

    def __init__(self):
        super().__init__(
            name="whisper",
            aliases=["wh", "tell"],
            description="특정 플레이어에게 개인 메시지를 전달합니다",
            usage="whisper <플레이어명> <메시지>"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        logger.debug(f"WhisperCommand 실행: 플레이어={session.player.username}, args={args}") # pyright: ignore[reportOptionalMemberAccess]

        if len(args) < 2:
            logger.warning(f"WhisperCommand: 잘못된 인수 개수 - 플레이어={session.player.username}, args={args}") # pyright: ignore[reportOptionalMemberAccess]
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="사용법: whisper <플레이어명> <메시지>"
            )

        target_player_name = args[0]
        message = " ".join(args[1:])

        logger.info(f"귓속말 시도: {session.player.username} -> {target_player_name}") # pyright: ignore[reportOptionalMemberAccess]
        current_room_id = getattr(session, 'current_room_id', None)

        if not current_room_id:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="현재 방 정보를 찾을 수 없습니다."
            )

        # 대상 플레이어 찾기 (같은 방에 있는 플레이어만)
        target_session = None
        for other_session in session.game_engine.session_manager.get_authenticated_sessions().values(): # pyright: ignore[reportOptionalMemberAccess]
            if (other_session.player and
                other_session.player.username.lower() == target_player_name.lower() and
                getattr(other_session, 'current_room_id', None) == current_room_id and
                other_session.session_id != session.session_id):
                target_session = other_session
                break

        if not target_session:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=f"{target_player_name}님을 이 방에서 찾을 수 없습니다."
            )

        # 대상 플레이어에게 귓속말 전송
        await target_session.send_message({
            "type": "whisper_received",
            "message": f"💬 {session.player.username}님이 귓속말: {message}", # pyright: ignore[reportOptionalMemberAccess]
            "from": session.player.username, # pyright: ignore[reportOptionalMemberAccess]
            "timestamp": datetime.now().isoformat() # pyright: ignore[reportOptionalMemberAccess]
        })

        # 방의 다른 플레이어들에게는 귓속말이 있었다는 것만 알림
        whisper_notice = f"💭 {session.player.username}님이 {target_session.player.username}님에게 귓속말을 했습니다." # pyright: ignore[reportOptionalMemberAccess]

        return CommandResult(
            result_type=CommandResultType.SUCCESS,
            message=f"{target_session.player.username}님에게 귓속말: {message}",
            broadcast=True,
            broadcast_message=whisper_notice,
            room_only=True
        )
