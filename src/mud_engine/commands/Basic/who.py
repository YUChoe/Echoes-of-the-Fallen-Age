# -*- coding: utf-8 -*-
"""접속자 목록 명령어"""

import logging
from typing import List

from ..base import BaseCommand, CommandResult, CommandResultType
from ...core.types import SessionType
from ...core.localization import get_localization_manager
from ...server.telnet_session import TelnetSession

logger = logging.getLogger(__name__)


class WhoCommand(BaseCommand):

    def __init__(self, session_manager=None):
        super().__init__(
            name="who",
            aliases=["users", "players"],
            description="현재 접속 중인 플레이어 목록을 표시합니다",
            usage="who"
        )
        self.session_manager = session_manager

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        localization = get_localization_manager()
        # preferred_locale 우선, 없으면 session.locale, 최종적으로 'en' 기본값
        locale = getattr(session.player, 'preferred_locale', None) if session.player else None
        if not locale:
            locale = getattr(session, 'locale', 'en')

        if not self.session_manager:
            # 기본 구현
            header = localization.get_message("who.connected_players", locale, count=1)
            you_marker = localization.get_message("who.you_marker", locale)
            player_entry = localization.get_message("who.player_entry", locale,
                                                   username=session.player.username,
                                                   marker=you_marker,
                                                   time=0)
            response = f"{header}\n{player_entry}"

            return self.create_success_result(
                message=response,
                data={
                    "action": "who",
                    "player_count": 1,
                    "players": [session.player.username]
                }
            )

        # SessionManager를 통해 실제 접속자 목록 가져오기
        players = []
        logger.info(f"who 명령어 실행 - 세션 수: {len(self.session_manager.sessions)}")

        for sess in self.session_manager.iter_authenticated_sessions():
            logger.info(f"세션 확인: {sess.session_id}, is_authenticated: {sess.is_authenticated}, player: {sess.player}")
            if sess.player:
                session_time = (sess.last_activity - sess.created_at).total_seconds()
                players.append({
                    "username": sess.player.username,
                    "session_time": int(session_time),
                    "is_self": sess.session_id == session.session_id
                })

        logger.info(f"who 명령어 - 찾은 플레이어 수: {len(players)}")

        if not players:
            return self.create_info_result(localization.get_message("who.no_players", locale))

        header = localization.get_message("who.connected_players", locale, count=len(players))
        response_lines = [header]

        for player in players:
            marker = localization.get_message("who.you_marker", locale) if player["is_self"] else ""
            player_entry = localization.get_message("who.player_entry", locale,
                                                   username=player['username'],
                                                   marker=marker,
                                                   time=player['session_time'])
            response_lines.append(player_entry)

        return self.create_success_result(
            message="\n".join(response_lines),
            data={
                "action": "who",
                "player_count": len(players),
                "players": [p["username"] for p in players]
            }
        )
