# -*- coding: utf-8 -*-
"""어드민 채널 인증

두 종류의 주체가 접속한다. 관리자는 `players.is_admin` 계정과 bcrypt 비밀번호로
전체 권한을 갖고, 서비스는 환경변수 토큰으로 계정 생성 권한만 갖는다.

관리자 인증은 게임 계정을 재사용한다. 계정 체계를 이중화하지 않기 위한 결정이며,
게임 세션의 인증 상태는 어드민 채널로 전이되지 않는다.

프로토콜 계약: docs/protocol/admin.md
"""

import hmac
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

from ...utils.exceptions import AuthenticationError

if TYPE_CHECKING:
    from ...game.managers import PlayerManager

logger = logging.getLogger(__name__)

# 어드민 세션 유효 기간. 만료되면 이후 요청을 SESSION_EXPIRED 로 거절한다
SESSION_LIFETIME = timedelta(hours=2)

# 토큰으로 접속할 수 있는 서비스 주체. 각각 환경변수 `{이름}_SERVICE_TOKEN` 을 읽는다
ALLOWED_SERVICES = ("landing",)

# 서비스 주체가 호출할 수 있는 메시지 타입
SERVICE_ALLOWED_TYPES = ("account_create",)


@dataclass
class AdminPrincipal:
    """인증된 어드민 채널 주체

    Attributes:
        kind: `admin` 또는 `service`
        name: 관리자 사용자명 또는 서비스 이름
        expires_at: 세션 만료 시각
        player_id: 관리자인 경우의 플레이어 uuid
        display_name: 관리자인 경우의 표시 이름
    """

    kind: str
    name: str
    expires_at: datetime
    player_id: Optional[str] = None
    display_name: Optional[str] = None

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        """세션이 만료됐는지"""
        return (now or datetime.now()) >= self.expires_at

    def may_send(self, message_type: str) -> bool:
        """이 주체가 해당 메시지 타입을 호출할 수 있는지

        서비스 주체는 계정 생성만 할 수 있다. 관리자는 제한이 없다.
        역할 기반 세분화는 범위 밖이다.
        """
        if self.kind == "service":
            return message_type in SERVICE_ALLOWED_TYPES
        return True


def _expiry(now: Optional[datetime] = None) -> datetime:
    """지금부터의 세션 만료 시각"""
    return (now or datetime.now()) + SESSION_LIFETIME


class AdminAuthenticator:
    """어드민 채널의 두 인증 경로를 담당한다."""

    def __init__(self, player_manager: "PlayerManager") -> None:
        self._player_manager = player_manager

    async def authenticate_admin(self, username: str, password: str) -> AdminPrincipal:
        """관리자를 인증한다.

        비밀번호 검증은 게임 채널과 같은 bcrypt 경로를 쓴다. 기존 Node 웹어드민의
        평문 환경변수 비교 방식은 폐기했다.

        Args:
            username: 사용자명
            password: 평문 비밀번호

        Returns:
            인증된 주체

        Raises:
            AuthenticationError: 자격 증명이 틀린 경우
            PermissionError: 자격은 맞지만 `is_admin` 이 거짓인 경우
        """
        player = await self._player_manager.authenticate(username, password)

        if not player.is_admin:
            raise PermissionError(f"not an admin account: {username}")

        return AdminPrincipal(
            kind="admin",
            name=player.username,
            expires_at=_expiry(),
            player_id=player.id,
            display_name=player.get_display_name(),
        )

    def authenticate_service(self, service: str, token: str) -> AdminPrincipal:
        """서비스 주체를 인증한다.

        Args:
            service: 서비스 이름. `ALLOWED_SERVICES` 에 있어야 한다
            token: 환경변수에 설정한 토큰

        Returns:
            인증된 주체

        Raises:
            AuthenticationError: 알 수 없는 서비스이거나 토큰이 틀린 경우
        """
        if service not in ALLOWED_SERVICES:
            raise AuthenticationError(f"unknown service: {service}")

        expected = os.getenv(f"{service.upper()}_SERVICE_TOKEN", "")

        if not expected:
            logger.error(f"서비스 토큰이 설정되지 않았습니다: {service.upper()}_SERVICE_TOKEN")
            raise AuthenticationError(f"service token not configured: {service}")

        # 타이밍 공격을 막기 위해 상수 시간 비교를 쓴다
        if not hmac.compare_digest(expected, token):
            raise AuthenticationError(f"invalid service token: {service}")

        return AdminPrincipal(kind="service", name=service, expires_at=_expiry())
