# -*- coding: utf-8 -*-
"""어드민 서버 (TCP 4001)

게임용 4000 과 별도 포트를 연다. 어드민은 게임 세션과 분리된 경로와 인증을 갖고,
게임 세션에서 `is_admin` 이 참이어도 어드민 기능을 쓸 수 없다.

이 포트는 외부에 노출하지 않는다. 기본 바인드 주소가 루프백인 이유이며,
게이트웨이와 랜딩 백엔드만 도달할 수 있게 구성한다.

프로토콜 계약: docs/protocol/admin.md
"""

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Optional

from ...utils.exceptions import AuthenticationError
from ...utils.version_manager import get_version_manager
from ..channels import (
    CHANNEL_ADMIN,
    GAME_ONLY_TYPES,
    wrong_channel_detail,
)
from ..serialization import (
    MAX_LINE_BYTES,
    PROTOCOL_VERSION,
    admin_login_result,
    build,
    service_login_result,
)
from .admin_session import AdminSession
from .auth import AdminAuthenticator

if TYPE_CHECKING:
    from ...game.managers import PlayerManager

logger = logging.getLogger(__name__)

# 인증 전 연결이 유휴 상태로 머물 수 있는 시간 (초)
AUTH_TIMEOUT = 60.0

# 인증 전에 허용하는 메시지 타입
PREAUTH_TYPES = ("admin_login", "service_login", "ping")

# 메시지 타입 → 처리기. 리소스 CRUD 와 액션은 Task 7.2~7.5 에서 등록한다
AdminHandler = Callable[[AdminSession, dict[str, Any]], Awaitable[None]]


class AdminServer:
    """어드민 채널 연결을 받아 인증하고 요청을 라우팅한다."""

    def __init__(
        self,
        host: str,
        port: int,
        player_manager: "PlayerManager",
    ) -> None:
        self.host = host
        self.port = port
        self.authenticator = AdminAuthenticator(player_manager)
        self.sessions: dict[str, AdminSession] = {}
        self.handlers: dict[str, AdminHandler] = {}
        self.server: Optional[asyncio.AbstractServer] = None

    def register(self, message_type: str, handler: AdminHandler) -> None:
        """인증 후 메시지 처리기를 등록한다.

        Task 7.2~7.5 가 리소스 CRUD, 통계, 맵, 액션 처리기를 여기에 붙인다.
        """
        self.handlers[message_type] = handler

    async def start(self) -> None:
        """어드민 서버를 시작한다."""
        self.server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port,
            limit=MAX_LINE_BYTES,
        )
        logger.info(f"어드민 서버 시작: {self.host}:{self.port}")

    async def stop(self) -> None:
        """어드민 서버를 종료한다."""
        if not self.server:
            return

        for session in list(self.sessions.values()):
            await session.close("서버 종료")

        self.sessions.clear()

        self.server.close()
        await self.server.wait_closed()
        self.server = None
        logger.info("어드민 서버 종료 완료")

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """연결 하나의 수명주기를 처리한다."""
        session = AdminSession(reader, writer)
        self.sessions[session.session_id] = session
        logger.info(f"어드민 채널 접속: {session.short_id} ({session.ip_address})")

        try:
            await self._send_welcome(session)

            if await self._authenticate(session):
                await self._serve(session)
        except asyncio.CancelledError:
            logger.info(f"어드민 세션 {session.short_id} 핸들러 취소됨")
        except Exception as e:
            logger.error(
                f"어드민 세션 {session.short_id} 처리 중 오류: {e}", exc_info=True
            )
            await session.send_error("INTERNAL_ERROR", str(e))
        finally:
            self.sessions.pop(session.session_id, None)
            await session.close("연결 종료")

    @staticmethod
    async def _send_welcome(session: AdminSession) -> None:
        """접속 직후 채널을 밝힌다.

        게임 채널의 `welcome` 과 같은 타입이지만 `channel` 이 `admin` 이고
        `supported_locales` 와 `title` 이 없다. 어드민 채널은 번역을 하지 않고
        도구가 소비하므로 표시용 정보를 담지 않는다.
        """
        await session.send_message(
            build(
                "welcome",
                protocol_version=PROTOCOL_VERSION,
                channel=CHANNEL_ADMIN,
                server_version=get_version_manager().get_version_string(),
            )
        )

    async def _authenticate(self, session: AdminSession) -> bool:
        """인증 메시지를 받아 주체를 확정한다.

        인증 전에는 `admin_login`, `service_login`, `ping` 만 허용한다. 실패해도
        연결을 끊지 않고 다음 시도를 기다린다. 유휴 상태가 `AUTH_TIMEOUT` 을
        넘으면 연결이 끝난다.

        Returns:
            인증 성공 여부
        """
        while True:
            message = await session.read_message(timeout=AUTH_TIMEOUT)

            if message is None:
                return False

            msg_type = message["type"]
            seq = message.get("seq")

            if msg_type == "ping":
                await self._send_pong(session, seq)
                continue

            if msg_type in GAME_ONLY_TYPES:
                await self._reject_wrong_channel(session, msg_type, seq)
                continue

            if msg_type not in PREAUTH_TYPES:
                await session.send_rejected(
                    msg_type,
                    "NOT_AUTHENTICATED",
                    f"{msg_type} requires authentication",
                    seq,
                )
                continue

            if msg_type == "admin_login":
                if await self._handle_admin_login(session, message):
                    return True
                continue

            if await self._handle_service_login(session, message):
                return True

    async def _handle_admin_login(
        self, session: AdminSession, message: dict[str, Any]
    ) -> bool:
        """`admin_login` 을 처리하고 결과를 응답한다."""
        seq = message.get("seq")
        username = message.get("username")
        password = message.get("password")

        if not isinstance(username, str) or not isinstance(password, str):
            await session.send_message(
                admin_login_result(seq, False, reason_code="VALIDATION_FAILED")
            )
            return False

        try:
            principal = await self.authenticator.authenticate_admin(username, password)
        except AuthenticationError:
            # 사용자명 존재 여부를 구분하지 않는다. 계정 열거 공격을 막기 위한 조치다
            logger.warning(
                f"어드민 인증 실패: IP={session.ip_address}, 세션={session.short_id}"
            )
            await session.send_message(
                admin_login_result(seq, False, reason_code="NOT_AUTHENTICATED")
            )
            return False
        except PermissionError:
            logger.warning(f"어드민 권한 없는 계정의 접속 시도: {username}")
            await session.send_message(
                admin_login_result(seq, False, reason_code="PERMISSION_DENIED")
            )
            return False

        session.principal = principal
        logger.info(f"어드민 인증 성공: {principal.name} (세션 {session.short_id})")

        await session.send_message(
            admin_login_result(
                seq,
                True,
                admin={
                    "id": principal.player_id,
                    "username": principal.name,
                    "display_name": principal.display_name,
                },
                expires_at=principal.expires_at.isoformat(),
            )
        )
        return True

    async def _handle_service_login(
        self, session: AdminSession, message: dict[str, Any]
    ) -> bool:
        """`service_login` 을 처리하고 결과를 응답한다."""
        seq = message.get("seq")
        service = message.get("service")
        token = message.get("token")

        if not isinstance(service, str) or not isinstance(token, str):
            await session.send_message(
                service_login_result(seq, False, reason_code="VALIDATION_FAILED")
            )
            return False

        try:
            principal = self.authenticator.authenticate_service(service, token)
        except AuthenticationError:
            logger.warning(
                f"서비스 인증 실패: service={service}, IP={session.ip_address}"
            )
            await session.send_message(
                service_login_result(seq, False, reason_code="NOT_AUTHENTICATED")
            )
            return False

        session.principal = principal
        logger.info(f"서비스 인증 성공: {service} (세션 {session.short_id})")

        await session.send_message(
            service_login_result(
                seq,
                True,
                service=service,
                expires_at=principal.expires_at.isoformat(),
            )
        )
        return True

    async def _serve(self, session: AdminSession) -> None:
        """인증된 세션의 요청을 처리한다.

        세션 만료는 매 요청과 읽기 대기 시각에 확인한다. 만료되면
        `SESSION_EXPIRED` 를 보내고 연결을 끝낸다.
        """
        while True:
            timeout = self._seconds_until_expiry(session)

            if timeout <= 0:
                await self._expire(session)
                return

            message = await session.read_message(timeout=timeout)

            if message is None:
                if self._seconds_until_expiry(session) <= 0:
                    await self._expire(session)
                return

            if not session.is_authenticated:
                await self._expire(session)
                return

            await self._route(session, message)

    async def _route(self, session: AdminSession, message: dict[str, Any]) -> None:
        """인증 후 메시지를 등록된 처리기로 보낸다."""
        msg_type = message["type"]
        seq = message.get("seq")
        principal = session.principal

        if msg_type == "ping":
            await self._send_pong(session, seq)
            return

        if msg_type in GAME_ONLY_TYPES:
            await self._reject_wrong_channel(session, msg_type, seq)
            return

        if principal is not None and not principal.may_send(msg_type):
            await session.send_rejected(
                msg_type,
                "PERMISSION_DENIED",
                f"{principal.kind} principal may not send {msg_type}",
                seq,
            )
            return

        handler = self.handlers.get(msg_type)

        if handler is None:
            await session.send_rejected(
                msg_type, "NOT_APPLICABLE", f"unsupported message type: {msg_type}", seq
            )
            return

        await handler(session, message)

    @staticmethod
    async def _reject_wrong_channel(
        session: AdminSession, msg_type: str, seq: Optional[int]
    ) -> None:
        """게임 채널 메시지를 어드민 채널에서 받았을 때 거절한다.

        조용히 무시하면 클라이언트가 잘못된 포트에 붙은 사실을 알 수 없다.
        """
        logger.warning(
            f"어드민 채널에서 게임 메시지 수신: {msg_type} (세션 {session.short_id})"
        )
        await session.send_rejected(
            msg_type,
            "NOT_APPLICABLE",
            wrong_channel_detail(msg_type, CHANNEL_ADMIN),
            seq,
        )

    async def _expire(self, session: AdminSession) -> None:
        """만료된 세션을 정리한다."""
        logger.info(f"어드민 세션 만료: {session.short_id}")
        await session.send_rejected(
            "session", "SESSION_EXPIRED", "admin session expired"
        )

    @staticmethod
    def _seconds_until_expiry(session: AdminSession) -> float:
        """세션 만료까지 남은 시간 (초)"""
        if session.principal is None:
            return 0.0

        return (session.principal.expires_at - datetime.now()).total_seconds()

    @staticmethod
    async def _send_pong(session: AdminSession, seq: Optional[int]) -> None:
        """`ping` 에 응답한다. 게임 채널과 같은 형식이다."""
        await session.send_message(
            build("pong", seq=seq, server_time=datetime.now().isoformat())
        )
