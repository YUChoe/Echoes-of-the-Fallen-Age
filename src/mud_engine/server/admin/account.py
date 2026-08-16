# -*- coding: utf-8 -*-
"""계정 생성 경로 (`account_create`)

관리자가 계정을 만드는 경로다. 새 플레이어는 게임 채널의 `register` 로 직접
만든다. 두 경로는 같은 규칙(`server/accounts.py`)을 쓰고 감사 기록과 응답
형식만 다르다.

프로토콜 계약: docs/protocol/admin.md
"""

import logging
from typing import Any, Optional

from .. import accounts
from ..serialization import build
from . import audit
from .admin_session import AdminSession

logger = logging.getLogger(__name__)

class AccountHandlers:
    """`account_create` 를 처리한다."""

    def __init__(self, player_manager: Any) -> None:
        self._players = player_manager

    def register_all(self, server: Any) -> None:
        """어드민 서버에 처리기를 등록한다."""
        server.register("account_create", self.handle)

    async def handle(self, session: AdminSession, message: dict[str, Any]) -> None:
        """`account_create` 한 건을 처리한다."""
        seq = message.get("seq")
        actor = session.principal.name if session.principal else "unknown"

        username = message.get("username")
        password = message.get("password")
        email = message.get("email") or None
        locale = message.get("preferred_locale") or None

        error = accounts.validate(username, password, email, locale)

        if error is not None:
            await self._deny(session, actor, "VALIDATION_FAILED", error, seq, username)
            return

        assert isinstance(username, str) and isinstance(password, str)

        player, reason_code, detail = await accounts.create(
            self._players, username, password, email, locale
        )

        if reason_code is not None:
            await self._deny(session, actor, reason_code, detail, seq, username)
            return

        audit.record(
            actor=actor,
            operation="account_create",
            resource="players",
            target={"id": player.id, "username": username},
            changes={"email": email, "preferred_locale": locale},
        )

        logger.info(f"계정 생성: {username} (주체: {actor})")

        await session.send_message(
            build("account_create_result", seq=seq, success=True, player_id=player.id)
        )

    @staticmethod
    async def _deny(
        session: AdminSession,
        actor: str,
        reason_code: str,
        detail: str,
        seq: Optional[int],
        username: Any,
    ) -> None:
        """계정 생성을 거절하고 감사 로그에 남긴다."""
        audit.record(
            actor=actor,
            operation="account_create",
            resource="players",
            target={"username": username} if isinstance(username, str) else {},
            result="rejected",
            reason_code=reason_code,
            detail=detail,
        )

        await session.send_message(
            build(
                "account_create_result",
                seq=seq,
                success=False,
                reason_code=reason_code,
            )
        )
