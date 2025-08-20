#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""웹 서버 테스트 스크립트"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.mud_engine.database.connection import get_database_manager
from src.mud_engine.game.managers import PlayerManager
from src.mud_engine.server.server import MudServer

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_web_server():
    """웹 서버 테스트"""
    print("🌐 웹 서버 테스트 시작")

    try:
        # 데이터베이스 초기화
        print("📊 데이터베이스 초기화 중...")
        db_manager = await get_database_manager()

        # PlayerManager 초기화
        print("👤 PlayerManager 초기화 중...")
        player_manager = PlayerManager(db_manager)

        # 웹 서버 생성
        print("🚀 웹 서버 생성 중...")
        server = MudServer(
            host="localhost",
            port=8080,
            player_manager=player_manager
        )

        # 서버 시작
        print("▶️  서버 시작 중...")
        await server.start()

        print("✅ 웹 서버가 성공적으로 시작되었습니다!")
        print("🌐 서버 주소: http://localhost:8080")
        print("📝 브라우저에서 접속하여 테스트하세요.")
        print("⏹️  Ctrl+C를 눌러 서버를 종료하세요.")

        # 서버 실행 유지
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 서버 종료 신호를 받았습니다...")

    except Exception as e:
        logger.error(f"서버 테스트 중 오류 발생: {e}", exc_info=True)
        print(f"❌ 오류: {e}")
    finally:
        # 서버 정리
        if 'server' in locals():
            print("🧹 서버 정리 중...")
            await server.stop()

        # 데이터베이스 정리
        if 'db_manager' in locals():
            print("🗄️  데이터베이스 연결 종료 중...")
            await db_manager.close()

        print("👋 웹 서버 테스트 완료")


if __name__ == "__main__":
    asyncio.run(test_web_server())