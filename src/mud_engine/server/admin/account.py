# -*- coding: utf-8 -*-
"""계정 생성 경로 (`account_create`)

게임 클라이언트에는 회원가입이 없다. 랜딩 사이트가 서비스 토큰으로 인증한 뒤
이 경로로 계정을 만든다.

서비스 토큰이 설정되지 않은 배포에서는 경로를 등록하지 않는다. 계정 생성을
쓰지 않는 배포가 환경변수를 비워 두는 것만으로 경로를 닫을 수 있다.

프로토콜 계약: docs/protocol/admin.md
"""

import logging
import os
import re
from typing import Any, Optional

from ...utils.exceptions import AuthenticationError
from ..serialization import build
from . import audit
from .admin_session import AdminSession
from .auth import ALLOWED_SERVICES

logger = logging.getLogger(__name__)

# 사용자명 규칙. 로그인 식별자이므로 ASCII 로 제한한다. 한국어를 허용하면
# 키보드 배열이 다른 환경에서 자기 계정에 접속할 수 없는 경우가 생긴다
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 20

# 비밀번호 길이. bcrypt 는 72바이트를 넘는 입력을 조용히 잘라내므로 상한을 둔다.
# 잘린 채 저장되면 뒷부분이 다른 비밀번호로도 인증에 성공한다
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_BYTES = 72

# 이메일은 선택 항목이다. 형식만 확인하고 도달 가능성은 검증하지 않는다
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
EMAIL_MAX_LENGTH = 254

# `players.preferred_locale` 에 저장할 수 있는 값
SUPPORTED_LOCALES = ("en", "ko")


def is_enabled() -> bool:
    """계정 생성 경로를 열 수 있는지.

    허용된 서비스 중 하나라도 토큰이 설정돼 있어야 한다.
    """
    return any(
        os.getenv(f"{service.upper()}_SERVICE_TOKEN") for service in ALLOWED_SERVICES
    )


class AccountHandlers:
    """`account_create` 를 처리한다."""

    def __init__(self, player_manager: Any) -> None:
        self._players = player_manager

    def register_all(self, server: Any) -> None:
        """어드민 서버에 처리기를 등록한다.

        서비스 토큰이 없으면 등록하지 않는다. 미등록 타입은 `NOT_APPLICABLE` 로
        거절되므로 경로가 닫힌 사실이 응답으로 드러난다.
        """
        if not is_enabled():
            logger.warning(
                "서비스 토큰이 설정되지 않아 계정 생성 경로를 등록하지 않습니다. "
                f"{'/'.join(s.upper() + '_SERVICE_TOKEN' for s in ALLOWED_SERVICES)}"
            )
            return

        server.register("account_create", self.handle)

    async def handle(self, session: AdminSession, message: dict[str, Any]) -> None:
        """`account_create` 한 건을 처리한다."""
        seq = message.get("seq")
        actor = session.principal.name if session.principal else "unknown"

        username = message.get("username")
        password = message.get("password")
        email = message.get("email") or None
        locale = message.get("preferred_locale") or None

        error = _validate(username, password, email, locale)

        if error is not None:
            await self._deny(session, actor, "VALIDATION_FAILED", error, seq, username)
            return

        assert isinstance(username, str) and isinstance(password, str)

        try:
            player = await self._players.create_account(
                username, password, email, locale
            )
        except AuthenticationError:
            # 사용자명 중복이 유일한 사유다. 다른 실패는 예외 타입이 다르다
            await self._deny(
                session,
                actor,
                "USERNAME_TAKEN",
                f"username already exists: {username}",
                seq,
                username,
            )
            return
        except Exception as e:
            logger.error(f"계정 생성 실패 ({username}): {e}", exc_info=True)
            await self._deny(
                session, actor, "INTERNAL_ERROR", str(e), seq, username
            )
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


def _validate(
    username: Any, password: Any, email: Any, locale: Any
) -> Optional[str]:
    """입력 값을 검증한다.

    Returns:
        문제가 있으면 개발자용 영문 설명. 없으면 None
    """
    if not isinstance(username, str):
        return "username must be a string"

    if not USERNAME_MIN_LENGTH <= len(username) <= USERNAME_MAX_LENGTH:
        return (
            f"username must be {USERNAME_MIN_LENGTH}-{USERNAME_MAX_LENGTH} characters"
        )

    if USERNAME_PATTERN.match(username) is None:
        return "username may contain only letters, digits and underscore"

    if not isinstance(password, str):
        return "password must be a string"

    if len(password) < PASSWORD_MIN_LENGTH:
        return f"password must be at least {PASSWORD_MIN_LENGTH} characters"

    if len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        # bcrypt 가 조용히 잘라내므로 거절한다
        return f"password must not exceed {PASSWORD_MAX_BYTES} bytes"

    if email is not None:
        if not isinstance(email, str):
            return "email must be a string"
        if len(email) > EMAIL_MAX_LENGTH:
            return f"email must not exceed {EMAIL_MAX_LENGTH} characters"
        if EMAIL_PATTERN.match(email) is None:
            return "email format is invalid"

    if locale is not None:
        if not isinstance(locale, str) or locale not in SUPPORTED_LOCALES:
            return f"preferred_locale must be one of {', '.join(SUPPORTED_LOCALES)}"

    return None
