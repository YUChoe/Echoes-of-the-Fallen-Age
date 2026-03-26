# -*- coding: utf-8 -*-
"""현재 방에 있는 플레이어 목록 표시 명령어"""

import logging
from typing import List

from .base import BaseCommand, CommandResult, CommandResultType
from ..core.types import SessionType

logger = logging.getLogger(__name__)


class PlayersCommand(BaseCommand):
    """현재 방에 있는 플레이어 목록 표시"""

    def __init__(self):
        super().__init__(
            name="players",
            aliases=["방사람", "here"],
            description="현재 방에 있는 플레이어들을 표시합니다",
            usage="players"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        logger.debug(f"PlayersCommand 실행: 플레이어={session.player.username}")

        current_room_id = getattr(session, 'current_room_id', None)

        if not current_room_id:
            logger.error(f"PlayersCommand: 현재 방 정보 없음 - 플레이어={session.player.username}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="현재 방 정보를 찾을 수 없습니다."
            )

        # 같은 방에 있는 플레이어들 찾기
        players_in_room = []
        for other_session in session.game_engine.session_manager.iter_authenticated_sessions():
            if (other_session.player and
                getattr(other_session, 'current_room_id', None) == current_room_id):

                player_info = {
                    "name": other_session.player.username,
                    "is_self": other_session.session_id == session.session_id,
                    "following": getattr(other_session, 'following_player', None)
                }
                players_in_room.append(player_info)

        from ..core.localization import get_localization_manager
        localization = get_localization_manager()
        locale = getattr(session, 'locale', 'en')

        if not players_in_room:
            logger.info(f"PlayersCommand: 빈 방 - {current_room_id}")
            return CommandResult(
                result_type=CommandResultType.SUCCESS,
                message=localization.get_message("players.no_players_in_room", locale)
            )

        # 플레이어 목록 생성
        player_list = []
        for player in players_in_room:
            if player["is_self"]:
                me_marker = localization.get_message("players.me_marker", locale)
                player_text = localization.get_message("players.player_entry", locale,
                                                     username=player['name'],
                                                     marker=me_marker)
            else:
                player_text = localization.get_message("players.player_entry", locale,
                                                     username=player['name'],
                                                     marker="")

            if player["following"]:
                player_text += f" (→ {player['following']}님을 따라가는 중)"

            player_list.append(player_text)

        header = localization.get_message("players.in_room", locale, count=len(players_in_room))
        message = header + "\n" + "\n".join(player_list)

        logger.info(f"PlayersCommand 완료: 방={current_room_id}, 플레이어 수={len(players_in_room)}")

        return CommandResult(
            result_type=CommandResultType.SUCCESS,
            message=message,
            data={
                "players": players_in_room,
                "room_id": current_room_id
            }
        )
