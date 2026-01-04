# -*- coding: utf-8 -*-
"""종료 명령어"""

import logging
from typing import List

from ..base import BaseCommand, CommandResult, CommandResultType
from ...core.types import SessionType
from ...core.localization import get_localization_manager
from ...server.telnet_session import TelnetSession

logger = logging.getLogger(__name__)


class QuitCommand(BaseCommand):

    def __init__(self):
        super().__init__(
            name="quit",
            aliases=["exit", "logout"],
            description="게임을 종료합니다",
            usage="quit"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        localization = get_localization_manager()
        locale = getattr(session.player, 'preferred_locale', 'en') if session.player else 'en'

        message = localization.get_message("quit.message", locale)

        return self.create_success_result(
            message=message,
            data={
                "action": "quit",
                "disconnect": True
            }
        )
