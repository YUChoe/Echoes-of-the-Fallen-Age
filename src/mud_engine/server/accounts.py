# -*- coding: utf-8 -*-
"""계정 생성 규칙

두 경로가 같은 규칙을 쓴다. 게임 채널의 `register` 와 어드민 채널의
`account_create` 다. 앞의 것은 새 플레이어가 클라이언트에서 직접 만드는 경로이고
뒤의 것은 관리자가 만드는 경로다.

규칙을 한 곳에 두는 것은 두 경로가 갈라지지 않게 하려는 것이다. 사용자명 규칙이
한쪽에서만 느슨해지면 그 경로로 만든 계정이 다른 쪽 검사를 통과하지 못한다.

프로토콜 계약: docs/protocol/client-to-server.md, docs/protocol/admin.md
"""

import logging
import re
from typing import Any, Optional

from ..utils.exceptions import AuthenticationError

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


def validate(
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


async def create(
    player_manager: Any,
    username: str,
    password: str,
    email: Optional[str],
    locale: Optional[str],
) -> tuple[Any, Optional[str], str]:
    """계정을 만든다.

    Returns:
        `(player, reason_code, detail)`. 성공하면 `reason_code` 가 None 이다.
        사유 코드는 계약이 정한 `USERNAME_TAKEN`, `INTERNAL_ERROR` 다.
    """
    try:
        player = await player_manager.create_account(
            username, password, email, locale
        )
    except AuthenticationError:
        # 사용자명 중복이 유일한 사유다. 다른 실패는 예외 타입이 다르다
        return None, "USERNAME_TAKEN", f"username already exists: {username}"
    except Exception as e:
        logger.error(f"계정 생성 실패 ({username}): {e}", exc_info=True)
        return None, "INTERNAL_ERROR", str(e)

    return player, None, ""
