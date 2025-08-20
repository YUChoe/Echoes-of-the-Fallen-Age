# -*- coding: utf-8 -*-
"""MUD 게임 서버의 핵심 클래스"""

import logging
from typing import Optional

from aiohttp import web

logger = logging.getLogger(__name__)


class MudServer:
    """aiohttp 기반의 MUD 웹 서버"""

    def __init__(self, host: str, port: int):
        """MudServer 초기화"""
        self.host: str = host
        self.port: int = port
        self.app: web.Application = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self._setup_routes()

    def _setup_routes(self) -> None:
        """서버 라우팅 설정"""
        logger.info("라우팅 설정 중...")
        self.app.router.add_get("/", self.handle_index)
        self.app.router.add_static("/static/", path="static", name="static")
        logger.info("라우팅 설정 완료")

    async def handle_index(self, request: web.Request) -> web.Response:
        """메인 페이지 핸들러"""
        return web.FileResponse("static/html/index.html")

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
            await self.runner.cleanup()
            logger.info("서버가 성공적으로 종료되었습니다.")
