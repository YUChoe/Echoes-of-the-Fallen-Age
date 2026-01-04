# -*- coding: utf-8 -*-
"""말하기 명령어"""

import logging
from typing import List

from ..base import BaseCommand, CommandResult, CommandResultType
from ...core.types import SessionType
from ...core.localization import get_localization_manager
from ...server.telnet_session import TelnetSession

logger = logging.getLogger(__name__)


class SayCommand(BaseCommand):

    def __init__(self):
        super().__init__(
            name="say",
            aliases=["'"],
            description="같은 방에 있는 모든 플레이어에게 메시지를 전달합니다",
            usage="say <메시지> 또는 '<메시지>"
        )

    async def execute(self, session: TelnetSession, args: List[str]) -> CommandResult:
        localization = get_localization_manager()
        locale = session.player.preferred_locale if session.player else "en"

        if not self.validate_args(args, min_args=1):
            error_msg = localization.get_message("say.usage_error", locale)
            return self.create_error_result(error_msg)

        message = " ".join(args)
        username = session.player.get_display_name() # pyright: ignore[reportOptionalMemberAccess]

        # 플레이어에게 확인 메시지
        player_message = localization.get_message("say.success", locale, message=message)
        broadcast_message = localization.get_message("say.broadcast", locale, username=username, message=message)

        return self.create_success_result(
            message=player_message,
            data={
                "action": "say",
                "speaker": username,
                "message": message
            },
            broadcast=True,
            broadcast_message=broadcast_message,
            room_only=True
        )
