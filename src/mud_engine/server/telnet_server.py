# -*- coding: utf-8 -*-
"""Telnet MUD 서버"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any

from ..game.managers import PlayerManager
from ..utils.exceptions import AuthenticationError
from .telnet_session import TelnetSession
from .chat import ChatRouter
from .serialization import PROTOCOL_VERSION, build, message_payload
from ..core.game_engine import GameEngine
from ..core.event_bus import initialize_event_bus, shutdown_event_bus
from ..utils.version_manager import get_version_manager
from .player_session_logger import PlayerSessionLogger

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
                await session.send_event(
                    "서버가 종료됩니다. 연결이 곧 끊어집니다.", category="system"
                )
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
            await session.send_error(f"서버 오류가 발생했습니다: {e}")
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
                server_version=version_manager.get_version_string(),
                supported_locales=["en", "ko"],
                title={
                    "en": "The Chronicles of Karnas: Divided Dominion",
                    "ko": "카르나스 연대기: 분할된 지배권",
                },
            )
        )

        await self._send_announcements(session)

    async def _send_announcements(self, session: TelnetSession) -> None:
        """공지사항 파일이 있으면 알림으로 전송한다.

        Args:
            session: Telnet 세션
        """
        try:
            announcements_path = os.path.join("data", "announcements.txt")

            if not os.path.exists(announcements_path):
                logger.debug(f"공지사항 파일을 찾을 수 없습니다: {announcements_path}")
                return

            with open(announcements_path, "r", encoding="utf-8") as f:
                announcements = f.read().strip()

            if not announcements:
                logger.debug("공지사항 파일이 비어있습니다")
                return

            # 본문의 개행은 json.dumps 가 \n 으로 이스케이프하므로 라인 경계를
            # 깨뜨리지 않는다. 줄바꿈 표시는 클라이언트가 판단한다.
            await session.send_event(announcements, category="system")

        except Exception as e:
            logger.error(f"공지사항 읽기 실패: {e}")
            # 공지사항 실패는 접속 흐름에 영향을 주지 않는다

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
                logger.info(f"클라이언트 정보: {message.get('client')}")
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

        # 같은 계정의 기존 세션이 있으면 종료한다
        if player.id in self.player_sessions:
            old_session_id = self.player_sessions[player.id]
            old_session = self.sessions.get(old_session_id)
            if old_session:
                await old_session.send_event(
                    "다른 위치에서 로그인하여 연결이 종료됩니다.", category="system"
                )
                await self.remove_session(old_session_id, "중복 로그인")

        session.authenticate(player)
        self.player_sessions[player.id] = session.session_id
        session.locale = player.preferred_locale

        await session.send_message(
            build(
                "login_result",
                seq=seq,
                success=True,
                player={
                    "id": player.id,
                    "username": player.username,
                    "display_name": player.get_display_name(),
                    # SQLite 는 boolean 을 정수로 저장하므로 계약대로 bool 로 맞춘다
                    "is_admin": bool(player.is_admin),
                    "faction_id": player.faction_id,
                },
            )
        )

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

            if await self.game_engine.try_rejoin_combat(session):
                logger.info(f"플레이어 {username} 전투 복귀 성공")

        return True

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

        if msg_type == "logout":
            await session.send_message(
                build("logout_result", seq=seq, success=True)
            )
            await session.close("클라이언트 요청으로 로그아웃")
            return False

        if msg_type == "client_info":
            logger.info(f"클라이언트 정보: {message.get('client')}")
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
