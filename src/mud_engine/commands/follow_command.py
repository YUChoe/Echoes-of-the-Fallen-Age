# -*- coding: utf-8 -*-
"""다른 플레이어 따라가기 명령어"""

import logging
from typing import List

from .base import BaseCommand, CommandResult, CommandResultType
from ..core.types import SessionType
from ..core.event_bus import Event, EventType

logger = logging.getLogger(__name__)


class FollowCommand(BaseCommand):
    """다른 플레이어 따라가기"""

    def __init__(self):
        super().__init__(
            name="follow",
            aliases=["따라가기"],
            description="다른 플레이어를 따라갑니다",
            usage="follow <플레이어명> 또는 follow stop (따라가기 중지)"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        logger.debug(f"FollowCommand 실행: 플레이어={session.player.username}, args={args}")

        if not args:
            logger.warning(f"FollowCommand: 빈 인수 - 플레이어={session.player.username}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="사용법: follow <플레이어명> 또는 follow stop"
            )

        if args[0].lower() == "stop":
            # 따라가기 중지
            if hasattr(session, 'following_player'):
                followed_player = session.following_player
                delattr(session, 'following_player')

                logger.info(f"따라가기 중지: {session.player.username} (대상: {followed_player})")
                return CommandResult(
                    result_type=CommandResultType.SUCCESS,
                    message=f"{followed_player}님 따라가기를 중지했습니다."
                )
            else:
                logger.warning(f"FollowCommand: 따라가는 플레이어 없음 - {session.player.username}")
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message="현재 따라가고 있는 플레이어가 없습니다."
                )

        # 플레이어 이름 (공백 불허이므로 첫 번째 인자만 사용)
        target_player_name = args[0]
        current_room_id = getattr(session, 'current_room_id', None)

        if not current_room_id:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="현재 방 정보를 찾을 수 없습니다."
            )

        # 대상 플레이어 찾기
        target_session = None
        for other_session in session.game_engine.session_manager.iter_authenticated_sessions():
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

        # 따라가기 설정
        session.following_player = target_session.player.username

        logger.info(f"따라가기 시작: {session.player.username} -> {target_session.player.username} (방: {current_room_id})")

        # 이벤트 발행
        await session.game_engine.event_bus.publish(Event(
            event_type=EventType.PLAYER_FOLLOW,
            source=session.session_id,
            room_id=current_room_id,
            data={
                "follower_id": session.player.id,
                "follower_name": session.player.username,
                "target_id": target_session.player.id,
                "target_name": target_session.player.username
            }
        ))

        # 대상 플레이어에게 알림
        await target_session.send_message({
            "type": "being_followed",
            "message": f"👥 {session.player.username}님이 당신을 따라가기 시작했습니다."
        })

        return CommandResult(
            result_type=CommandResultType.SUCCESS,
            message=f"{target_session.player.username}님을 따라가기 시작했습니다.",
            broadcast=True,
            broadcast_message=f"👥 {session.player.username}님이 {target_session.player.username}님을 따라가기 시작했습니다.",
            room_only=True
        )
