# -*- coding: utf-8 -*-
"""MUD 게임 서버의 핵심 클래스"""

import asyncio
import json
import logging
from typing import Optional, Dict

from aiohttp import web, WSMsgType

from ..game.managers import PlayerManager
from ..game.models import Player
from ..utils.exceptions import AuthenticationError

logger = logging.getLogger(__name__)


class MudServer:
    """aiohttp 기반의 MUD 웹 서버"""

    def __init__(self, host: str, port: int, player_manager: PlayerManager):
        """MudServer 초기화"""
        self.host: str = host
        self.port: int = port
        self.app: web.Application = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self.player_manager: PlayerManager = player_manager
        self.active_connections: Dict[str, web.WebSocketResponse] = {}
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
        logger.info("새로운 클라이언트가 연결되었습니다.")

        player: Optional[Player] = None

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        logger.debug(f"수신 메시지: {data}")

                        if player is None:  # 인증되지 않은 사용자
                            player = await self.handle_authentication(ws, data)
                        else:  # 인증된 사용자
                            await self.handle_game_command(player, ws, data)

                    except json.JSONDecodeError:
                        await ws.send_json({"error": "Invalid JSON format"})
                    except AuthenticationError as e:
                        await ws.send_json({"error": str(e)})
                    except Exception as e:
                        logger.error(f"메시지 처리 중 오류 발생: {e}", exc_info=True)
                        await ws.send_json({"error": "An unexpected error occurred."})

                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"웹소켓 연결 오류: {ws.exception()}")

        except asyncio.CancelledError:
            logger.info("웹소켓 핸들러가 취소되었습니다.")
        finally:
            if player:
                del self.active_connections[player.id]
                logger.info(f"플레이어 '{player.username}'의 연결이 종료되었습니다.")
            else:
                logger.info("인증되지 않은 클라이언트의 연결이 종료되었습니다.")

        return ws

    async def handle_authentication(self, ws: web.WebSocketResponse, data: dict) -> Optional[Player]:
        """인증 관련 메시지를 처리합니다."""
        command = data.get("command")
        username = data.get("username")
        password = data.get("password")

        if not all([command, username, password]):
            raise AuthenticationError("명령, 사용자 이름, 비밀번호는 필수입니다.")

        player: Optional[Player] = None
        if command == "register":
            player = await self.player_manager.create_account(username, password)
            await ws.send_json({"status": "success", "message": f"계정 '{username}'이(가) 생성되었습니다. 로그인해주세요."})
        elif command == "login":
            player = await self.player_manager.authenticate(username, password)
            self.active_connections[player.id] = ws
            await ws.send_json({"status": "success", "message": f"'{username}'님, 환영합니다!"})
            logger.info(f"플레이어 '{username}'이(가) 로그인했습니다.")
        else:
            raise AuthenticationError("알 수 없는 인증 명령입니다.")
        
        return player

    async def handle_game_command(self, player: Player, ws: web.WebSocketResponse, data: dict):
        """인증된 사용자의 게임 관련 명령을 처리합니다."""
        # TODO: 게임 명령어 처리 로직 구현
        logger.info(f"플레이어 '{player.username}'로부터 명령 수신: {data}")
        await ws.send_json({"response": f"'{data.get('command')}' 명령을 받았습니다."})

    async def start(self) -> None:
        """서버 시작"""
        logger.info(f"서버 시작 중... http://{self.host}:{self.port}")
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        logger.info("서버가 성공적으로 시작되었습니다.")

    async def stop(self) -> None:
        """서버 중지"""
        if self.runner:
            logger.info("서버 종료 중...")
            for ws in self.active_connections.values():
                await ws.close(code=1001, message='Server shutdown')
            await self.runner.cleanup()
            logger.info("서버가 성공적으로 종료되었습니다.")