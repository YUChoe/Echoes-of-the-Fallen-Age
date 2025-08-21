# -*- coding: utf-8 -*-
"""MUD 게임 서버의 핵심 클래스"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any

from aiohttp import web, WSMsgType

from ..game.managers import PlayerManager
from ..game.models import Player
from ..utils.exceptions import AuthenticationError
from .session import SessionManager, Session
from ..core.game_engine import GameEngine
from ..core.event_bus import initialize_event_bus, shutdown_event_bus

logger = logging.getLogger(__name__)


class MudServer:
    """aiohttp 기반의 MUD 웹 서버"""

    def __init__(self, host: str = "localhost", port: int = 8080,
                 player_manager: Optional[PlayerManager] = None,
                 db_manager: Optional[Any] = None):
        """MudServer 초기화"""
        self.host: str = host
        self.port: int = port
        self.app: web.Application = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self.player_manager: PlayerManager = player_manager
        self.db_manager = db_manager
        self.session_manager: SessionManager = SessionManager()
        self.game_engine: Optional[GameEngine] = None

        logger.info("MudServer 초기화")
        self._setup_routes()

    def _setup_routes(self) -> None:
        """서버 라우팅 설정"""
        logger.info("라우팅 설정 중...")
        self.app.router.add_get("/", self.handle_index)
        self.app.router.add_get("/ws", self.websocket_handler)
        self.app.router.add_static("/static/", path="static", name="static")
        logger.info("라우팅 설정 완료")

    async def handle_index(self, request: web.Request) -> web.Response:
        """메인 페이지 핸들러"""
        return web.FileResponse("static/html/index.html")

    async def websocket_handler(self, request: web.Request) -> web.WebSocketResponse:
        """웹소켓 연결 및 메시지 처리 핸들러"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        # 새 세션 생성
        session = self.session_manager.add_session(ws, request)
        logger.info(f"새로운 클라이언트 연결: {session}")

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        logger.debug(f"세션 {session.session_id} 메시지 수신: {data}")

                        if not session.is_authenticated:  # 인증되지 않은 사용자
                            await self.handle_authentication(session, data)
                        else:  # 인증된 사용자
                            await self.handle_game_command(session, data)

                    except json.JSONDecodeError:
                        await session.send_error("잘못된 JSON 형식입니다.", "INVALID_JSON")
                    except AuthenticationError as e:
                        await session.send_error(str(e), "AUTH_ERROR")
                    except Exception as e:
                        logger.error(f"세션 {session.session_id} 메시지 처리 오류: {e}", exc_info=True)
                        await session.send_error("예상치 못한 오류가 발생했습니다.", "INTERNAL_ERROR")

                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"세션 {session.session_id} WebSocket 오류: {ws.exception()}")

        except asyncio.CancelledError:
            logger.info(f"세션 {session.session_id} WebSocket 핸들러 취소됨")
        finally:
            # 게임 엔진에 세션 제거 알림
            if self.game_engine and session.is_authenticated:
                await self.game_engine.remove_player_session(session, "연결 종료")

            # 세션 정리
            await self.session_manager.remove_session(session.session_id, "연결 종료")

        return ws

    async def handle_authentication(self, session: Session, data: dict) -> None:
        """인증 관련 메시지를 처리합니다."""
        command = data.get("command")
        username = data.get("username")
        password = data.get("password")

        if not all([command, username, password]):
            raise AuthenticationError("명령, 사용자 이름, 비밀번호는 필수입니다.")

        if command == "register":
            # 계정 생성
            player = await self.player_manager.create_account(username, password)
            await session.send_success(
                f"계정 '{username}'이(가) 생성되었습니다. 로그인해주세요.",
                {"action": "register_success", "username": username}
            )
            logger.info(f"새 계정 생성: {username}")

        elif command == "login":
            # 로그인 처리
            player = await self.player_manager.authenticate(username, password)

            # 세션에 플레이어 인증 정보 설정
            self.session_manager.authenticate_session(session.session_id, player)

            # 게임 엔진에 플레이어 세션 추가
            if self.game_engine:
                await self.game_engine.add_player_session(session, player)

            await session.send_success(
                f"'{username}'님, 환영합니다!",
                {
                    "action": "login_success",
                    "username": username,
                    "player_id": player.id,
                    "session_id": session.session_id
                }
            )
            logger.info(f"플레이어 로그인: {username} (세션: {session.session_id})")

        else:
            raise AuthenticationError("알 수 없는 인증 명령입니다.")

    async def handle_game_command(self, session: Session, data: dict) -> None:
        """인증된 사용자의 게임 관련 명령을 처리합니다."""
        command = data.get("command", "").strip()

        if not command:
            await session.send_error("명령어가 비어있습니다.", "EMPTY_COMMAND")
            return

        logger.info(f"플레이어 '{session.player.username}' 명령 수신: {command}")

        # 게임 엔진에 명령어 처리 위임
        if self.game_engine:
            await self.game_engine.handle_player_command(session, command)

        # 기본 명령어 처리
        if command.lower() == "help":
            await self.handle_help_command(session)
        elif command.lower() == "who":
            await self.handle_who_command(session)
        elif command.lower() == "quit":
            await self.handle_quit_command(session)
        elif command.lower() == "stats":
            await self.handle_stats_command(session)
        elif command.lower() == "engine":
            await self.handle_engine_command(session)
        else:
            # 일반 게임 명령어 (추후 구현)
            await session.send_message({
                "response": f"'{command}' 명령을 받았습니다.",
                "command": command,
                "timestamp": session.last_activity.isoformat()
            })

    async def handle_help_command(self, session: Session) -> None:
        """도움말 명령어 처리"""
        help_text = """
🎮 사용 가능한 명령어:
• help - 이 도움말을 표시합니다
• who - 접속 중인 플레이어 목록을 표시합니다
• stats - 서버 통계를 표시합니다
• engine - 게임 엔진 및 이벤트 버스 통계를 표시합니다
• quit - 게임을 종료합니다

더 많은 명령어가 곧 추가될 예정입니다!
        """.strip()

        await session.send_message({
            "response": help_text,
            "command": "help"
        })

    async def handle_who_command(self, session: Session) -> None:
        """접속자 목록 명령어 처리"""
        authenticated_sessions = self.session_manager.get_authenticated_sessions()

        if not authenticated_sessions:
            await session.send_message({
                "response": "현재 접속 중인 플레이어가 없습니다.",
                "command": "who"
            })
            return

        players = []
        for sess in authenticated_sessions.values():
            if sess.player:
                players.append({
                    "username": sess.player.username,
                    "session_time": (sess.last_activity - sess.created_at).total_seconds()
                })

        response = f"📋 접속 중인 플레이어 ({len(players)}명):\n"
        for player in players:
            session_time = int(player["session_time"])
            response += f"• {player['username']} (접속시간: {session_time}초)\n"

        await session.send_message({
            "response": response.strip(),
            "command": "who",
            "players": players
        })

    async def handle_quit_command(self, session: Session) -> None:
        """종료 명령어 처리"""
        await session.send_success("안전하게 게임을 종료합니다. 안녕히 가세요!")
        await self.session_manager.remove_session(session.session_id, "플레이어 요청으로 종료")

    async def handle_stats_command(self, session: Session) -> None:
        """서버 통계 명령어 처리"""
        stats = self.session_manager.get_stats()

        response = f"""
📊 서버 통계:
• 총 세션: {stats['total_sessions']}개
• 인증된 세션: {stats['authenticated_sessions']}개
• 활성 세션: {stats['active_sessions']}개
• 비활성 세션: {stats['inactive_sessions']}개
• 정리 주기: {stats['cleanup_interval']}초
        """.strip()

        await session.send_message({
            "response": response,
            "command": "stats",
            "stats": stats
        })

    async def handle_engine_command(self, session: Session) -> None:
        """게임 엔진 통계 명령어 처리"""
        if not self.game_engine:
            await session.send_error("게임 엔진이 초기화되지 않았습니다.")
            return

        engine_stats = self.game_engine.get_stats()
        event_stats = engine_stats.get("event_bus_stats", {})

        response = f"""
🎮 게임 엔진 통계:
• 실행 상태: {'실행 중' if engine_stats['running'] else '중지됨'}
• 가동 시간: {engine_stats.get('uptime_seconds', 0):.1f}초
• 시작 시간: {engine_stats.get('start_time', 'N/A')}

📡 이벤트 버스:
• 실행 상태: {'실행 중' if event_stats.get('running') else '중지됨'}
• 총 구독자: {event_stats.get('total_subscribers', 0)}개
• 이벤트 히스토리: {event_stats.get('event_history_size', 0)}개
• 큐 크기: {event_stats.get('queue_size', 0)}개

📋 이벤트 타입별 발생 횟수:
        """.strip()

        # 이벤트 타입별 카운트 추가
        event_counts = event_stats.get('event_type_counts', {})
        if event_counts:
            for event_type, count in event_counts.items():
                response += f"\n• {event_type}: {count}회"
        else:
            response += "\n• 발생한 이벤트 없음"

        await session.send_message({
            "response": response,
            "command": "engine",
            "engine_stats": engine_stats
        })

    async def start(self) -> None:
        """서버 시작"""
        logger.info(f"서버 시작 중... http://{self.host}:{self.port}")

        # 이벤트 버스 초기화
        event_bus = await initialize_event_bus()

        # 게임 엔진 초기화
        if self.player_manager and self.db_manager:
            self.game_engine = GameEngine(
                session_manager=self.session_manager,
                player_manager=self.player_manager,
                db_manager=self.db_manager,
                event_bus=event_bus
            )
            await self.game_engine.start()

        # 세션 관리자 정리 작업 시작
        await self.session_manager.start_cleanup_task()

        # 웹 서버 시작
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

        logger.info("서버가 성공적으로 시작되었습니다.")

    async def stop(self) -> None:
        """서버 중지"""
        if self.runner:
            logger.info("서버 종료 중...")

            # 게임 엔진 종료
            if self.game_engine:
                await self.game_engine.stop()

            # 모든 세션에 종료 알림 전송
            await self.session_manager.broadcast_to_all({
                "status": "server_shutdown",
                "message": "서버가 종료됩니다. 연결이 곧 끊어집니다."
            }, authenticated_only=False)

            # 모든 세션 정리
            sessions = list(self.session_manager.get_all_sessions().keys())
            for session_id in sessions:
                await self.session_manager.remove_session(session_id, "서버 종료")

            # 세션 관리자 정리 작업 중지
            await self.session_manager.stop_cleanup_task()

            # 이벤트 버스 종료
            await shutdown_event_bus()

            # 웹 서버 종료
            await self.runner.cleanup()
            logger.info("서버가 성공적으로 종료되었습니다.")

    def get_server_config(self) -> Dict[str, Any]:
        """서버 설정 정보 반환"""
        return {
            "host": self.host,
            "port": self.port,
            "session_stats": self.session_manager.get_stats()
        }

    def get_server_stats(self) -> Dict[str, Any]:
        """서버 통계 정보 반환"""
        return {
            "server_config": self.get_server_config(),
            "session_manager": self.session_manager.get_stats(),
            "is_running": self.runner is not None and not self.runner.closed
        }