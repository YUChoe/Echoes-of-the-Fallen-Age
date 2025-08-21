#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""정상적인 종료가 가능한 웹 서버 테스트 스크립트"""

import asyncio
import logging
import sys
import os
import signal
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.mud_engine.database.connection import get_database_manager
from src.mud_engine.game.managers import PlayerManager
from src.mud_engine.server import MudServer

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 전역 종료 이벤트
shutdown_event = asyncio.Event()


def signal_handler(signum, frame):
    """시그널 핸들러 - 정상적인 종료"""
    print(f"\n🛑 종료 신호 수신 (시그널: {signum})")
    print("🤔 정말로 서버를 종료하시겠습니까? (Ctrl+C를 다시 누르면 강제 종료)")

    try:
        response = input("종료하려면 'yes' 입력: ").strip().lower()
        if response in ['yes', 'y', '예']:
            print("✅ 정상적인 종료를 시작합니다...")
            shutdown_event.set()
        else:
            print("📝 서버가 계속 실행됩니다.")
    except (EOFError, KeyboardInterrupt):
        print("\n🚨 강제 종료 신호를 받았습니다. 즉시 종료합니다.")
        shutdown_event.set()


async def test_web_server():
    """웹 서버 테스트"""
    print("🌐 웹 서버 테스트 시작")

    server = None
    db_manager = None

    try:
        # 시그널 핸들러 등록
        signal.signal(signal.SIGINT, signal_handler)

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
        print("💡 명령어:")
        print("   - Ctrl+C: 정상 종료 (확인 후)")
        print("   - Ctrl+C 두 번: 강제 종료")

        # 서버 실행 유지
        print("\n🔄 서버 실행 중... (종료하려면 Ctrl+C)")

        while not shutdown_event.is_set():
            await asyncio.sleep(1)

        print("🛑 정상적인 종료 절차를 시작합니다...")

    except Exception as e:
        logger.error(f"서버 테스트 중 오류 발생: {e}", exc_info=True)
        print(f"❌ 오류: {e}")
    finally:
        # 서버 정리
        if server:
            print("🧹 서버 정리 중...")
            try:
                await server.stop()
            except Exception as e:
                logger.error(f"서버 종료 중 오류: {e}")

        # 데이터베이스 정리
        if db_manager:
            print("🗄️  데이터베이스 연결 종료 중...")
            try:
                await db_manager.close()
            except Exception as e:
                logger.error(f"데이터베이스 종료 중 오류: {e}")

        print("👋 웹 서버 테스트 완료")


async def main():
    """메인 함수"""
    try:
        await test_web_server()
    except KeyboardInterrupt:
        print("\n🚨 강제 종료됨")
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}", exc_info=True)
    finally:
        print("🏁 프로그램 종료")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🚨 프로그램이 강제 종료되었습니다.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"프로그램 실행 중 오류: {e}", exc_info=True)
        sys.exit(1)

    sys.exit(0)  # 정상 종료