# -*- coding: utf-8 -*-
"""Telnet MUD 서버"""

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Dict, Any

from ..game.managers import PlayerManager
from ..utils.exceptions import AuthenticationError
from .telnet_session import TelnetSession
from .channels import (
    ADMIN_ONLY_TYPES,
    CHANNEL_ADMIN,
    CHANNEL_GAME,
    wrong_channel_detail,
)
from .chat import ChatRouter
from .serialization import PROTOCOL_VERSION, build, message_payload
from ..core.game_engine import GameEngine
from ..core.event_bus import initialize_event_bus, shutdown_event_bus
from ..utils.version_manager import get_version_manager
from .player_session_logger import PlayerSessionLogger

if TYPE_CHECKING:
    from .admin.admin_server import AdminServer

logger = logging.getLogger(__name__)

# 인증 대기 시간 (초)
AUTH_TIMEOUT = 60.0

# 인증 후 메시지 수신 대기 시간 (초)
SESSION_TIMEOUT = 300.0

# 같은 연결에서 허용하는 연속 로그인 실패 횟수
MAX_LOGIN_ATTEMPTS = 5


class TelnetServer:
    """asyncio 기반의 Telnet MUD 서버"""

    def __init__(self, host: str = "0.0.0.0", port: int = 4000,
                 player_manager: Optional[PlayerManager] = None,
                 db_manager: Optional[Any] = None):
        """TelnetServer 초기화

        Args:
            host: 서버 호스트
            port: 서버 포트
            player_manager: 플레이어 매니저
            db_manager: 데이터베이스 매니저
        """
        self.host: str = host
        self.port: int = port
        self.player_manager: PlayerManager = player_manager
        self.db_manager = db_manager
        self.sessions: Dict[str, TelnetSession] = {}
        self.player_sessions: Dict[str, str] = {}  # player_id -> session_id 매핑
        self.game_engine: Optional[GameEngine] = None
        # 어드민 채널 참조. 로그인 응답에 사용 가능 여부를 담기 위해서만 쓴다.
        # main.py 가 배선하며 어드민 서버가 없는 배포도 성립한다
        self.admin_server: Optional["AdminServer"] = None
        self.server: Optional[asyncio.Server] = None
        self._is_running: bool = False
        self._cleanup_task: Optional[asyncio.Task] = None
        self.player_session_logger: PlayerSessionLogger = PlayerSessionLogger()
        self._chat: Optional[ChatRouter] = None

        logger.info("TelnetServer 초기화")

    async def start(self) -> None:
        """Telnet 서버 시작"""
        logger.info(f"Telnet 서버 시작 중... telnet://{self.host}:{self.port}")

        # 이벤트 버스 초기화 (웹 서버와 공유하지 않는 경우)
        # event_bus = await initialize_event_bus()

        # 게임 엔진 초기화
        if self.player_manager and self.db_manager:
            # 웹 서버와 게임 엔진을 공유하는 경우, 이 부분은 main.py에서 처리
            pass

        # Telnet 서버 시작
        self.server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )

        # 세션 정리 작업 시작
        self._cleanup_task = asyncio.create_task(self._cleanup_inactive_sessions())

        self._is_running = True
        logger.info("Telnet 서버가 성공적으로 시작되었습니다.")

    async def stop(self) -> None:
        """Telnet 서버 중지"""
        if self.server:
            logger.info("Telnet 서버 종료 중...")

            # 모든 세션에 종료 알림 전송
            for session in list(self.sessions.values()):
                await session.send_event("system.server_shutdown")
                await session.close("서버 종료")

            # 세션 정리
            self.sessions.clear()
            self.player_sessions.clear()

            # 플레이어 세션 로거 전체 정리
            self.player_session_logger.cleanup_all()

            # 정리 작업 중지
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass

            # 서버 종료
            self.server.close()
            await self.server.wait_closed()
            self._is_running = False
            logger.info("Telnet 서버가 성공적으로 종료되었습니다.")

    async def handle_client(self, reader: asyncio.StreamReader,
                           writer: asyncio.StreamWriter) -> None:
        """클라이언트 연결 처리

        Args:
            reader: StreamReader 객체
            writer: StreamWriter 객체
        """
        session = TelnetSession(reader, writer)
        self.sessions[session.session_id] = session

        short_session_id = session.session_id.split('-')[-1] if '-' in session.session_id else session.session_id
        logger.info(f"새로운 Telnet 클라이언트 연결: TelnetSession[{short_session_id}](미인증) (총 {len(self.sessions)}개)")

        try:
            # Telnet 프로토콜 초기화
            await session.initialize_telnet()

            # 환영 메시지 전송
            await self.send_welcome_message(session)

            # 인증 처리
            authenticated = await self.handle_authentication(session)

            if authenticated:
                # 게임 루프
                await self.game_loop(session)

        except asyncio.CancelledError:
            logger.info(f"Telnet 세션 {session.session_id} 핸들러 취소됨")
        except Exception as e:
            logger.error(f"Telnet 세션 {session.session_id} 처리 중 오류: {e}", exc_info=True)
            await session.send_protocol_error("INTERNAL_ERROR", str(e))
        finally:
            # 게임 엔진에서 세션 제거
            if self.game_engine and session.is_authenticated:
                await self.game_engine.remove_player_session(session, "연결 종료")

            # 세션 정리
            await self.remove_session(session.session_id, "연결 종료")

    async def send_welcome_message(self, session: TelnetSession) -> None:
        """접속 직후 서버 정보를 전송한다.

        Args:
            session: Telnet 세션
        """
        version_manager = get_version_manager()

        await session.send_message(
            build(
                "welcome",
                protocol_version=PROTOCOL_VERSION,
                channel=CHANNEL_GAME,
                server_version=version_manager.get_version_string(),
                supported_locales=["en", "ko"],
                title={
                    "en": "The Chronicles of Karnas: Divided Dominion",
                    "ko": "카르나스 연대기: 분할된 지배권",
                },
            )
        )

    async def handle_authentication(self, session: TelnetSession) -> bool:
        """login 메시지를 받아 인증을 처리한다.

        같은 연결에서 연속 실패가 상한에 도달하면 연결을 종료한다.

        Args:
            session: Telnet 세션

        Returns:
            인증 성공 여부
        """
        attempts = 0

        while attempts < MAX_LOGIN_ATTEMPTS:
            try:
                message = await session.read_message(timeout=AUTH_TIMEOUT)
            except Exception as e:
                logger.error(f"인증 메시지 수신 오류: {e}", exc_info=True)
                return False

            if message is None:
                logger.debug(f"세션 {session.session_id}: 인증 대기 중 연결 종료")
                return False

            msg_type = message["type"]
            seq = message.get("seq")

            if msg_type == "ping":
                await self._send_pong(session, seq)
                continue

            if msg_type == "client_info":
                logger.info(
                    "클라이언트 정보: version=%s, platform=%s, locale=%s",
                    message.get("client_version"),
                    message.get("platform"),
                    message.get("locale"),
                )
                continue

            if msg_type in ADMIN_ONLY_TYPES:
                await self._reject_wrong_channel(session, msg_type, seq)
                continue

            if msg_type != "login":
                # 인증 전에는 login 외의 메시지를 허용하지 않는다
                await session.send_protocol_error(
                    "NOT_AUTHENTICATED",
                    f"{msg_type} requires authentication",
                    seq,
                )
                continue

            if await self.handle_login(session, message):
                return True

            attempts += 1

        logger.warning(
            f"세션 {session.session_id}: 로그인 실패 {MAX_LOGIN_ATTEMPTS}회로 연결 종료"
        )
        return False

    async def handle_login(
        self, session: TelnetSession, message: Dict[str, Any]
    ) -> bool:
        """login 메시지를 처리하고 login_result 를 응답한다.

        Args:
            session: Telnet 세션
            message: login 메시지

        Returns:
            로그인 성공 여부
        """
        seq = message.get("seq")
        username = message.get("username")
        password = message.get("password")

        if not isinstance(username, str) or not isinstance(password, str):
            await self._send_login_failure(session, seq)
            return False

        try:
            logger.info(
                f"🔐 로그인 시도: 사용자명='{username}', IP={session.ip_address}"
            )
            player = await self.player_manager.authenticate(username, password)
        except AuthenticationError as e:
            # 사용자명 존재 여부를 구분하지 않는다. 계정 열거 공격을 막기 위한 조치다.
            logger.warning(f"❌ 인증 실패: IP={session.ip_address}, 오류='{e}'")
            await self._send_login_failure(session, seq)
            return False

        # 같은 계정의 기존 세션이 있으면 종료한다. 자기 자신은 제외한다.
        # 같은 연결에서 로그아웃 후 다시 들어오는 경우가 있다.
        old_session_id = self.player_sessions.get(player.id)
        if old_session_id is not None and old_session_id != session.session_id:
            old_session = self.sessions.get(old_session_id)
            if old_session:
                await old_session.send_event("system.duplicate_login")
                await self.remove_session(old_session_id, "중복 로그인")

        session.authenticate(player)
        self.player_sessions[player.id] = session.session_id

        payload: Dict[str, Any] = {
            "success": True,
            "player": {
                "id": player.id,
                "username": player.username,
                "display_name": player.get_display_name(),
                # SQLite 는 boolean 을 정수로 저장하므로 계약대로 bool 로 맞춘다
                "is_admin": bool(player.is_admin),
                "faction_id": player.faction_id,
            },
        }

        admin_channel = self._admin_channel_info(player)
        if admin_channel is not None:
            payload["admin_channel"] = admin_channel

        await session.send_message(build("login_result", seq=seq, **payload))

        logger.info(
            f"✅ 로그인 성공: 사용자명='{username}', 플레이어ID={player.id}"
        )

        self.player_session_logger.setup_player_logger(
            player_id=player.id,
            player_username=player.username,
            session_id=session.session_id,
            ip_address=session.ip_address or "unknown",
        )

        if self.game_engine:
            await self.game_engine.add_player_session(session, player)
            await self._send_login_snapshots(session)

            if await self.game_engine.try_rejoin_combat(session):
                logger.info(f"플레이어 {username} 전투 복귀 성공")

        return True

    async def _handle_logout(
        self, session: TelnetSession, seq: Optional[int]
    ) -> None:
        """인증을 해제하되 연결은 유지한다.

        계약(`docs/protocol/client-to-server.md` logout)이 "연결은 유지되므로
        클라이언트는 로그인 화면으로 전환한다" 를 규정한다. 연결을 닫으면
        클라이언트가 재접속 백오프에 들어가고 자동 로그인이 다시 걸린다.

        게임 상태 정리는 접속 종료 경로와 같다. 위치 저장과 따라가기 해제가
        필요하고 다른 플레이어에게 퇴장을 알려야 한다.
        """
        player = session.player

        if self.game_engine is not None and player is not None:
            await self.game_engine.remove_player_session(
                session, "클라이언트 로그아웃"
            )
            self.game_engine.session_manager.remove_session(session.session_id)

        # 서버가 따로 들고 있는 계정→세션 매핑도 지운다. 남겨 두면 같은 연결에서
        # 다시 로그인할 때 자기 자신을 중복 로그인으로 판정해 끊는다.
        if (
            player is not None
            and self.player_sessions.get(player.id) == session.session_id
        ):
            del self.player_sessions[player.id]

        session.deauthenticate()
        await session.send_message(
            build("logout_result", seq=seq, success=True)
        )

    async def _send_login_snapshots(self, session: TelnetSession) -> None:
        """로그인 직후 초기 스냅샷을 보낸다.

        계약(`docs/protocol/README.md` 연결 수명주기 4항)이 `login_result` 성공
        후 `room_info`, `player_state`, `inventory` 세 메시지를 보내도록 한다.
        클라이언트는 셋을 모두 받은 뒤에 게임 화면을 표시한다.

        `room_info` 는 `add_player_session` 의 방 이동이 이미 보냈다. 나머지 둘을
        재요청 verb 로 보낸다. 같은 스냅샷을 만드는 코드가 이미 있으므로 별도
        경로를 만들지 않는다. `seq` 는 담지 않는다. 클라이언트 요청에 대한 응답이
        아니라 서버가 자발적으로 보내는 것이기 때문이다.
        """
        if self.game_engine is None:
            return

        for verb in ("request_state", "request_inventory"):
            # `type` 은 담지 않는다. `build_context` 가 verb, target, params,
            # seq 만 읽고, 담아 두면 계약 정합성 검사가 이 내부 합성 메시지를
            # 서버가 내보내는 타입으로 오인한다.
            await self.game_engine.command_manager.handle_action(
                session, {"verb": verb}
            )

    def _admin_channel_info(self, player: Any) -> Optional[Dict[str, Any]]:
        """어드민 권한 계정에게 어드민 채널 사용 가능 여부를 알린다.

        `is_admin` 이 거짓이면 필드를 아예 담지 않는다. `available` 은 권한만이
        아니라 어드민 서버가 실제로 떠 있는지를 반영한다. 권한이 있어도 이
        배포에 어드민 채널이 없으면 클라이언트가 진입 버튼을 노출해서는 안 된다.

        Returns:
            어드민 계정이면 채널 정보, 그 밖에는 None
        """
        if not player.is_admin:
            return None

        available = self.admin_server is not None and self.admin_server.is_running

        return {
            "available": available,
            "channel": CHANNEL_ADMIN,
            # 게임 세션 인증은 어드민 채널로 전이되지 않는다. 항상 참이다
            "requires_reauth": True,
        }

    async def _send_login_failure(
        self, session: TelnetSession, seq: Optional[int]
    ) -> None:
        """로그인 실패 응답. 사유를 세분화하지 않는다."""
        await session.send_message(
            build(
                "login_result",
                seq=seq,
                success=False,
                reason_code="INVALID_CREDENTIALS",
                message=message_payload("auth.login_failed"),
            )
        )

    def _chat_router(self, game_engine: GameEngine) -> ChatRouter:
        """채팅 라우터를 반환한다. 상태가 없어 세션마다 만들어도 무해하다."""
        if self._chat is None:
            self._chat = ChatRouter(game_engine)
        return self._chat

    async def _reject_wrong_channel(
        self, session: TelnetSession, msg_type: str, seq: Optional[int]
    ) -> None:
        """어드민 채널 메시지를 게임 채널에서 받았을 때 거절한다.

        조용히 무시하면 클라이언트가 잘못된 포트에 붙은 사실을 알 수 없다.
        """
        logger.warning(
            f"게임 채널에서 어드민 메시지 수신: {msg_type} "
            f"(세션 {session.session_id})"
        )
        await session.send_protocol_error(
            "NOT_APPLICABLE", wrong_channel_detail(msg_type, CHANNEL_GAME), seq
        )

    async def _send_pong(
        self, session: TelnetSession, seq: Optional[int]
    ) -> None:
        """ping 에 응답한다."""
        await session.send_message(
            build("pong", seq=seq, server_time=datetime.now().isoformat())
        )

    async def game_loop(self, session: TelnetSession) -> None:
        """인증된 세션의 메시지 수신 루프

        Args:
            session: Telnet 세션
        """
        while session.is_active():
            try:
                message = await session.read_message(timeout=SESSION_TIMEOUT)

                if message is None:
                    logger.debug(
                        f"세션 {session.session_id}: 연결 종료 또는 수신 타임아웃"
                    )
                    break

                if not await self.handle_client_message(session, message):
                    break

            except asyncio.CancelledError:
                logger.info(f"Telnet 세션 {session.session_id} 게임 루프 취소됨")
                break
            except Exception as e:
                logger.error(
                    f"Telnet 세션 {session.session_id} 게임 루프 오류: {e}",
                    exc_info=True,
                )
                await session.send_protocol_error(
                    "INTERNAL_ERROR", "message handling failed"
                )

    async def handle_client_message(
        self, session: TelnetSession, message: Dict[str, Any]
    ) -> bool:
        """인증된 세션의 메시지 한 건을 처리한다.

        Args:
            session: Telnet 세션
            message: 봉투 검증을 통과한 메시지

        Returns:
            연결을 유지하면 True, 종료해야 하면 False
        """
        msg_type = message["type"]
        seq = message.get("seq")

        if msg_type == "ping":
            await self._send_pong(session, seq)
            return True

        if msg_type in ADMIN_ONLY_TYPES:
            await self._reject_wrong_channel(session, msg_type, seq)
            return True

        if msg_type == "login":
            # 로그아웃 뒤 같은 연결에서 다른 계정으로 들어올 수 있다. 계약이
            # 로그아웃에서 연결을 유지하도록 정하므로 인증 루프가 아니라 이곳이
            # 재로그인을 받는 자리다.
            if session.is_authenticated:
                await session.send_protocol_error(
                    "WRONG_STATE",
                    "already authenticated; send logout first",
                    seq,
                )
                return True
            await self.handle_login(session, message)
            return True

        if msg_type == "logout":
            await self._handle_logout(session, seq)
            return True

        if msg_type == "client_info":
            logger.info(
                "클라이언트 정보: version=%s, platform=%s, locale=%s",
                message.get("client_version"),
                message.get("platform"),
                message.get("locale"),
            )
            return True

        if msg_type == "action":
            if self.game_engine:
                await self.game_engine.command_manager.handle_action(session, message)
            else:
                await session.send_protocol_error(
                    "INTERNAL_ERROR", "game engine not initialised", seq
                )
            return True

        if msg_type == "chat":
            if self.game_engine:
                await self._chat_router(self.game_engine).handle(session, message)
            else:
                await session.send_protocol_error(
                    "INTERNAL_ERROR", "game engine not initialised", seq
                )
            return True

        # 계약에 없는 type 은 무시한다. 상위 버전 클라이언트와의 호환을 위한 규칙이다.
        logger.warning(f"알 수 없는 메시지 타입 무시: {msg_type}")
        return True

    async def remove_session(self, session_id: str, reason: str = "세션 종료") -> bool:
        """세션 제거

        Args:
            session_id: 제거할 세션 ID
            reason: 제거 이유

        Returns:
            bool: 제거 성공 여부
        """
        session = self.sessions.get(session_id)
        if not session:
            return False

        # 플레이어 매핑 제거
        if session.player and session.player.id in self.player_sessions:
            # 플레이어 세션 로그 종료 및 정리
            self.player_session_logger.log_session_end(session.player.id, reason)
            self.player_session_logger.cleanup_player_logger(session.player.id)
            del self.player_sessions[session.player.id]

        # 연결 종료
        await session.close(reason)

        # 로그아웃 로깅
        if session.player:
            logger.info(f"🚪 Telnet 세션 종료: 플레이어='{session.player.username}', 이유='{reason}'")

        # 세션 제거
        if session_id in self.sessions:
            del self.sessions[session_id]

        short_session_id = session_id.split('-')[-1] if '-' in session_id else session_id
        logger.info(f"Telnet 세션 {short_session_id} 제거: {reason} (남은 세션: {len(self.sessions)}개)")
        return True

    async def _cleanup_inactive_sessions(self) -> None:
        """비활성 세션 정리 (백그라운드 작업)"""
        cleanup_interval = 60  # 60초마다 정리

        while True:
            try:
                await asyncio.sleep(cleanup_interval)

                inactive_sessions = []
                for session_id, session in self.sessions.items():
                    if not session.is_active():
                        inactive_sessions.append(session_id)

                for session_id in inactive_sessions:
                    await self.remove_session(session_id, "비활성 상태로 인한 정리")

                if inactive_sessions:
                    logger.info(f"Telnet: {len(inactive_sessions)}개 비활성 세션 정리 완료")

            except asyncio.CancelledError:
                logger.info("Telnet 세션 정리 작업 취소됨")
                break
            except Exception as e:
                logger.error(f"Telnet 세션 정리 중 오류: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """서버 통계 정보 반환

        Returns:
            Dict: 통계 정보
        """
        total_sessions = len(self.sessions)
        authenticated_sessions = sum(1 for s in self.sessions.values() if s.is_authenticated)
        active_sessions = sum(1 for s in self.sessions.values() if s.is_active())

        return {
            "total_sessions": total_sessions,
            "authenticated_sessions": authenticated_sessions,
            "active_sessions": active_sessions,
            "inactive_sessions": total_sessions - active_sessions,
            "is_running": self._is_running
        }
