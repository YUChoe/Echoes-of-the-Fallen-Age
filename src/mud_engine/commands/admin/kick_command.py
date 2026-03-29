# -*- coding: utf-8 -*-
"""플레이어 추방 명령어"""

import logging
from typing import List

from .base import AdminCommand
from ..base import CommandResult, CommandResultType
from ..utils import get_user_locale
from ...core.types import SessionType
from ...core.localization import get_localization_manager

logger = logging.getLogger(__name__)
I18N = get_localization_manager()


class KickPlayerCommand(AdminCommand):
    """플레이어 추방 명령어"""

    def __init__(self):
        super().__init__(
            name="kick",
            description="플레이어를 서버에서 추방합니다",
            aliases=["kickplayer"]
        )

    async def execute_admin(self, session: SessionType, args: List[str]) -> CommandResult:
        """플레이어 추방 실행"""
        locale = get_user_locale(session)
        if len(args) < 1:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.kick.usage", locale)
            )

        target_username = args[0]
        reason = " ".join(args[1:]) if len(args) > 1 else I18N.get_message("admin.kick.default_reason", locale)

        if target_username == session.player.username:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.kick.self", locale)
            )

        try:
            target_session = None
            for sess in session.game_engine.session_manager.get_authenticated_sessions().values():
                if sess.player and sess.player.username == target_username:
                    target_session = sess
                    break

            if not target_session:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.kick.not_found", locale, username=target_username)
                )

            if target_session.player.is_admin:
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=I18N.get_message("admin.kick.is_admin", locale)
                )

            target_locale = get_user_locale(target_session)
            await target_session.send_message({
                "type": "system_message",
                "message": I18N.get_message("admin.kick.target_msg", target_locale, reason=reason),
                "disconnect": True
            })

            await session.game_engine.session_manager.remove_session(
                target_session.session_id,
                f"Admin kick: {reason}"
            )

            return CommandResult(
                result_type=CommandResultType.SUCCESS,
                message=I18N.get_message("admin.kick.success", locale, username=target_username, reason=reason),
                broadcast=True,
                broadcast_message=I18N.get_message("admin.kick.broadcast", locale, username=target_username)
            )

        except Exception as e:
            logger.error(f"플레이어 추방 중 오류: {e}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=I18N.get_message("admin.kick.error", locale, error=str(e))
            )

    def get_help(self) -> str:
        return """
🚫 **플레이어 추방 명령어**

**사용법:** `kick <플레이어명> [사유]`

**예시:**
- `kick badplayer` - 기본 사유로 추방
- `kick spammer 스팸 행위` - 사유와 함께 추방

**주의사항:**
- 자기 자신은 추방할 수 없습니다
- 다른 관리자는 추방할 수 없습니다

**별칭:** `kickplayer`
**권한:** 관리자 전용
        """
