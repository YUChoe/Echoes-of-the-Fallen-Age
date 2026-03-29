# -*- coding: utf-8 -*-
"""관리자 명령어 기본 클래스"""

import logging
from typing import List

from ..base import BaseCommand, CommandResult, CommandResultType
from ..utils import get_user_locale
from ...core.types import SessionType
from ...core.localization import get_localization_manager

logger = logging.getLogger(__name__)
I18N = get_localization_manager()


class AdminCommand(BaseCommand):
    """관리자 명령어 기본 클래스"""

    def __init__(self, name: str, description: str, aliases: List[str] = None, usage: str = ""):
        super().__init__(name, aliases, description, usage, admin_only=True)
        self.admin_required = True

    def check_admin_permission(self, session: SessionType) -> bool:
        """관리자 권한 확인"""
        if not session.player or not session.player.is_admin:
            return False
        return True

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        """관리자 권한 확인 후 명령어 실행"""
        if not self.check_admin_permission(session):
            locale = get_user_locale(session)
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.permission_denied", locale)
            )
        return await self.execute_admin(session, args)

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
        """관리자 명령어 실행 (하위 클래스에서 구현)"""
        raise NotImplementedError
