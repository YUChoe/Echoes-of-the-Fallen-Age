# -*- coding: utf-8 -*-
"""Telnet MUD 서버"""

import asyncio
import logging
from typing import Optional, Dict, Any

from ..game.managers import PlayerManager
from ..utils.exceptions import AuthenticationError
from .telnet_session import TelnetSession
from .ansi_colors import ANSIColors
from ..core.game_engine import GameEngine
from ..core.event_bus import initialize_event_bus, shutdown_event_bus

logger = logging.getLogger(__name__)


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
                await session.send_text("서버가 종료됩니다. 연결이 곧 끊어집니다.")
                await session.close("서버 종료")

            # 세션 정리
            self.sessions.clear()
            self.player_sessions.clear()

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

        logger.info(f"새로운 Telnet 클라이언트 연결: {session} (총 {len(self.sessions)}개)")

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
        """환영 메시지 전송

        Args:
            session: Telnet 세션
        """
        welcome_text = f"""
{ANSIColors.BOLD}{ANSIColors.BRIGHT_CYAN}
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║        {ANSIColors.BRIGHT_YELLOW}Echoes of the Fallen Age{ANSIColors.BRIGHT_CYAN}                        ║
║                                                               ║
║        {ANSIColors.WHITE}Welcome to Karnas, the Fallen Continent{ANSIColors.BRIGHT_CYAN}           ║
║        {ANSIColors.WHITE}몰락의 대륙, 카르나스에 오신 것을 환영합니다{ANSIColors.BRIGHT_CYAN}        ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
{ANSIColors.RESET}

{ANSIColors.CYAN}Centuries after the fall of the Golden Empire...
Your adventure begins in a world transformed into ruins and monster lairs.

황금 제국이 무너진 뒤 수백 년...
폐허와 괴물의 소굴로 변한 세상에서 당신의 모험이 시작됩니다.{ANSIColors.RESET}

"""
        await session.send_text(welcome_text)

    async def handle_authentication(self, session: TelnetSession) -> bool:
        """인증 처리

        Args:
            session: Telnet 세션

        Returns:
            bool: 인증 성공 여부
        """
        max_attempts = 3
        attempts = 0

        while attempts < max_attempts:
            try:
                await session.send_text("")
                await session.send_info("1. Login / 로그인")
                await session.send_info("2. Register / 회원가입")
                await session.send_info("3. Quit / 종료")
                await session.send_text("")
                await session.send_prompt("Choice / 선택> ")

                choice = await session.read_line(timeout=60.0)

                if not choice:
                    await session.send_error("입력 시간이 초과되었습니다.")
                    return False

                choice = choice.lower().strip()

                if choice in ['3', 'quit', 'exit', 'q']:
                    await session.send_text("Goodbye! / 안녕히 가세요!")
                    return False

                if choice in ['1', 'login', 'l']:
                    if await self.handle_login(session):
                        return True
                elif choice in ['2', 'register', 'r']:
                    if await self.handle_register(session):
                        # 회원가입 후 자동 로그인
                        return True
                else:
                    await session.send_error("Invalid choice. Please enter 1, 2, or 3. / 잘못된 선택입니다. 1, 2, 또는 3을 입력하세요.")

                attempts += 1

            except AuthenticationError as e:
                await session.send_error(str(e))
                attempts += 1
            except Exception as e:
                logger.error(f"인증 처리 중 오류: {e}", exc_info=True)
                await session.send_error("인증 처리 중 오류가 발생했습니다.")
                return False

        await session.send_error("최대 시도 횟수를 초과했습니다.")
        return False

    async def handle_login(self, session: TelnetSession) -> bool:
        """로그인 처리

        Args:
            session: Telnet 세션

        Returns:
            bool: 로그인 성공 여부
        """
        await session.send_text("")
        await session.send_info("=== Login / 로그인 ===")
        await session.send_prompt("Username / 사용자명: ")
        username = await session.read_line(timeout=60.0)

        if not username:
            await session.send_error("Username not entered. / 사용자명을 입력하지 않았습니다.")
            return False

        # 패스워드 입력 시 에코 비활성화
        await session.disable_echo()
        await session.send_prompt("Password / 비밀번호: ")
        password = await session.read_line(timeout=60.0)
        await session.enable_echo()
        await session.send_text("")  # 줄바꿈 추가

        if not password:
            await session.send_error("Password not entered. / 비밀번호를 입력하지 않았습니다.")
            return False

        try:
            logger.info(f"🔐 Telnet 로그인 시도: 사용자명='{username}', IP={session.ip_address}")
            player = await self.player_manager.authenticate(username, password)

            # 기존 세션이 있다면 종료
            if player.id in self.player_sessions:
                old_session_id = self.player_sessions[player.id]
                if old_session_id in self.sessions:
                    old_session = self.sessions[old_session_id]
                    await old_session.send_text("다른 위치에서 로그인하여 연결이 종료됩니다.")
                    await self.remove_session(old_session_id, "중복 로그인")

            # 세션 인증
            session.authenticate(player)
            self.player_sessions[player.id] = session.session_id
            
            # 세션의 locale을 플레이어의 preferred_locale로 설정
            session.locale = player.preferred_locale

            # 게임 엔진에 세션 추가
            if self.game_engine:
                await self.game_engine.add_player_session(session, player)

            # 다국어 환영 메시지
            from ..core.localization import get_localization_manager
            localization = get_localization_manager()
            welcome_msg = localization.get_message("auth.login_success", session.locale, username=player.get_display_name())
            
            await session.send_success(welcome_msg)
            
            # 게임 입장 메시지
            game_entered_msg = localization.get_message("game.entered", session.locale)
            await session.send_info(game_entered_msg)
            
            # 선호 언어 설정 표시
            language_name = "English" if session.locale == "en" else "한국어"
            language_info = localization.get_message("auth.language_preference", session.locale, language=language_name)
            await session.send_message({
                "type": "system_message", 
                "message": language_info
            })
            
            logger.info(f"✅ Telnet 로그인 성공: 사용자명='{username}', 플레이어ID={player.id}")
            return True

        except AuthenticationError as e:
            logger.warning(f"❌ Telnet 인증 실패: IP={session.ip_address}, 오류='{str(e)}'")
            await session.send_error(str(e))
            return False

    async def handle_register(self, session: TelnetSession) -> bool:
        """회원가입 처리

        Args:
            session: Telnet 세션

        Returns:
            bool: 회원가입 성공 여부
        """
        await session.send_text("")
        await session.send_info("=== Register / 회원가입 ===")
        await session.send_prompt("Username (3-20 chars, no spaces) / 사용자명 (3-20자, 공백 불가): ")
        username = await session.read_line(timeout=60.0)

        if not username:
            await session.send_error("Username not entered. / 사용자명을 입력하지 않았습니다.")
            return False
        
        # 사용자명 검증: 공백 불허
        if ' ' in username:
            await session.send_error("Username cannot contain spaces. / 사용자명에 공백을 사용할 수 없습니다.")
            return False
        
        # 사용자명 길이 검증
        if len(username) < 3 or len(username) > 20:
            await session.send_error("Username must be 3-20 characters. / 사용자명은 3-20자여야 합니다.")
            return False

        # 패스워드 입력 시 에코 비활성화
        await session.disable_echo()
        await session.send_prompt("Password (min 6 chars) / 비밀번호 (최소 6자): ")
        password = await session.read_line(timeout=60.0)
        await session.send_text("")  # 줄바꿈 추가

        if not password:
            await session.enable_echo()
            await session.send_error("Password not entered. / 비밀번호를 입력하지 않았습니다.")
            return False

        await session.send_prompt("Confirm password / 비밀번호 확인: ")
        password_confirm = await session.read_line(timeout=60.0)
        await session.enable_echo()
        await session.send_text("")  # 줄바꿈 추가

        if password != password_confirm:
            await session.send_error("비밀번호가 일치하지 않습니다.")
            return False

        try:
            logger.info(f"🆕 Telnet 회원가입 시도: 사용자명='{username}', IP={session.ip_address}")
            player = await self.player_manager.create_account(username, password)

            # 자동 로그인
            session.authenticate(player)
            self.player_sessions[player.id] = session.session_id

            # 게임 엔진에 세션 추가
            if self.game_engine:
                await self.game_engine.add_player_session(session, player)

            await session.send_success(f"계정 '{username}'이(가) 생성되었습니다!")
            await session.send_success("자동으로 로그인되었습니다.")
            logger.info(f"✅ Telnet 회원가입 성공: 사용자명='{username}', 플레이어ID={player.id}")
            return True

        except Exception as e:
            logger.error(f"❌ Telnet 회원가입 실패: {e}", exc_info=True)
            await session.send_error(f"회원가입 실패: {e}")
            return False

    async def game_loop(self, session: TelnetSession) -> None:
        """게임 메인 루프

        Args:
            session: Telnet 세션
        """
        # 다국어 게임 입장 메시지
        from ..core.localization import get_localization_manager
        localization = get_localization_manager()
        
        await session.send_text("")
        game_entered_msg = localization.get_message("game.entered", session.locale)
        await session.send_info(game_entered_msg)
        await session.send_text("")

        while session.is_active():
            try:
                # 프롬프트 표시
                await session.send_prompt("> ")

                # 명령어 입력 대기
                command = await session.read_line(timeout=300.0)

                if command is None:
                    # 타임아웃 또는 연결 종료
                    logger.debug(f"Telnet 세션 {session.session_id}: read_line returned None")
                    break

                # 빈 문자열인 경우 (Telnet 프로토콜 바이트만 있었던 경우) 무시하고 계속
                if command == "":
                    continue

                # 명령어 처리
                await self.handle_game_command(session, command)

            except asyncio.CancelledError:
                logger.info(f"Telnet 세션 {session.session_id} 게임 루프 취소됨")
                break
            except Exception as e:
                logger.error(f"Telnet 세션 {session.session_id} 게임 루프 오류: {e}", exc_info=True)
                await session.send_error("명령어 처리 중 오류가 발생했습니다.")

    async def handle_game_command(self, session: TelnetSession, command: str) -> None:
        """게임 명령어 처리

        Args:
            session: Telnet 세션
            command: 명령어 문자열
        """
        command = command.strip()

        if not command:
            return

        logger.info(f"🎮 Telnet 명령어 입력: 플레이어='{session.player.username}', 명령어='{command}'")

        # 종료 명령어
        if command.lower() in ['quit', 'exit', 'logout']:
            await session.send_success("게임을 종료합니다. 안녕히 가세요!")
            await session.close("플레이어 요청으로 종료")
            return

        # 게임 엔진에 명령어 처리 위임
        if self.game_engine:
            result = await self.game_engine.handle_player_command(session, command)

            # 결과 메시지 전송 (게임 엔진에서 이미 전송했을 수 있음)
            # 필요시 추가 처리
        else:
            await session.send_error("게임 엔진이 초기화되지 않았습니다.")

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
            del self.player_sessions[session.player.id]

        # 연결 종료
        await session.close(reason)

        # 로그아웃 로깅
        if session.player:
            logger.info(f"🚪 Telnet 세션 종료: 플레이어='{session.player.username}', 이유='{reason}'")

        # 세션 제거
        if session_id in self.sessions:
            del self.sessions[session_id]

        logger.info(f"Telnet 세션 {session_id[:8]}... 제거: {reason} (남은 세션: {len(self.sessions)}개)")
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
