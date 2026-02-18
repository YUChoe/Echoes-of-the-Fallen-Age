# -*- coding: utf-8 -*-
"""도움말 명령어"""

import logging
from typing import List

from ..base import BaseCommand, CommandResult, CommandResultType
from ...core.types import SessionType
from ...core.localization import get_localization_manager
from ...server.telnet_session import TelnetSession

logger = logging.getLogger(__name__)


class HelpCommand(BaseCommand):

    def __init__(self, command_processor=None):
        super().__init__(
            name="help",
            aliases=["?", "commands"],
            description="명령어 도움말을 표시합니다",
            usage="help [명령어]"
        )
        self.command_processor = command_processor

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not self.command_processor:
            return self.create_error_result("명령어 처리기가 설정되지 않았습니다.")

        # 전투 중인 경우 전투 명령어만 표시
        if getattr(session, 'in_combat', False):
            localization = get_localization_manager()
            locale = session.player.preferred_locale if session.player else "en"

            combat_help = f"""
{localization.get_message("combat.help_title", locale)}

{localization.get_message("combat.help_attack", locale)}
{localization.get_message("combat.help_defend", locale)}
{localization.get_message("combat.help_flee", locale)}

{localization.get_message("combat.help_other", locale)}
• look - {localization.get_message("help.look_combat", locale, default="전투 상태 확인" if locale == "ko" else "Check combat status")}
• status - {localization.get_message("help.status", locale, default="능력치 확인" if locale == "ko" else "Check attributes")}
• combat - {localization.get_message("help.combat_detail", locale, default="전투 상태 상세 정보" if locale == "ko" else "Detailed combat information")}

💡 {localization.get_message("help.tip_numbers", locale, default="팁: 숫자만 입력해도 행동을 선택할 수 있습니다!" if locale == "ko" else "Tip: You can just enter numbers to select actions!")}
"""

            return self.create_success_result(
                message=combat_help.strip(),
                data={"action": "help_combat"}
            )

        # 플레이어의 관리자 권한 확인
        is_admin = False
        if session.player:
            is_admin = getattr(session.player, 'is_admin', False)

        if args:
            # 특정 명령어 도움말
            command_name = args[0]
            help_text = self.command_processor.get_help_text(command_name, is_admin)
        else:
            # 전체 명령어 목록
            help_text = self.command_processor.get_help_text(None, is_admin)

        return self.create_success_result(
            message=help_text,
            data={
                "action": "help",
                "command": args[0] if args else None,
                "is_admin": is_admin
            }
        )

