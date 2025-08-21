#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""웹 서버 테스트 스크립트"""

import asyncio
import logging
import sys
import os
import threading
import time
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
        print("⏹️  'Q' 키를 눌러 서버를 종료하세요.")
        print("💡 'H' 키를 눌러 도움말을 확인하세요.")

        # 서버 실행 유지 및 종료 처리
        shutdown_event = asyncio.Event()

        def input_monitor():
            """키 입력 모니터링 (별도 스레드)"""
            try:
                while not shutdown_event.is_set():
                    try:
                        user_input = input().strip().lower()
                        if user_input == 'q':
                            # 종료 확인
                            confirm = input("🤔 정말로 서버를 종료하시겠습니까? (yes/no): ").strip().lower()
                            if confirm in ['yes', 'y', '예', 'ㅇ']:
                                print("🛑 서버 종료를 시작합니다...")
                                shutdown_event.set()
                                break
                            else:
                                print("📝 서버가 계속 실행됩니다. 'Q'를 눌러 다시 종료할 수 있습니다.")
                        elif user_input == 'help' or user_input == 'h':
                            print("\n📋 사용 가능한 명령어:")
                            print("  Q - 서버 종료")
                            print("  H - 이 도움말 표시")
                            print("  S - 서버 상태 표시")
                            print("  R - 서버 통계 새로고침")
                        elif user_input == 's':
                            # 서버 상태 표시
                            print(f"📊 서버 상태: 실행 중 (http://localhost:8080)")
                            print(f"⏰ 실행 시간: {time.time() - start_time:.1f}초")
                        elif user_input == 'r':
                            print("🔄 서버 통계를 새로고침합니다...")
                            # 통계 정보는 서버 객체에서 가져와야 하므로 간단한 메시지만
                            print("📈 세션 관리자가 활성화되어 있습니다.")
                        elif user_input:
                            print(f"❓ 알 수 없는 명령어: '{user_input}'. 'H'를 눌러 도움말을 확인하세요.")
                    except EOFError:
                        # 입력 스트림이 닫힌 경우 (예: IDE에서 실행)
                        print("\n📝 입력 스트림이 닫혔습니다. 서버는 계속 실행됩니다.")
                        break
                    except Exception as e:
                        logger.error(f"입력 처리 중 오류: {e}")
            except Exception as e:
                logger.error(f"입력 모니터 오류: {e}")

        # 시작 시간 기록
        start_time = time.time()

        # 입력 모니터링 스레드 시작
        input_thread = threading.Thread(target=input_monitor, daemon=True)
        input_thread.start()

        # 서버 실행 유지
        try:
            while not shutdown_event.is_set():
                await asyncio.sleep(0.1)  # 더 빠른 응답을 위해 짧은 간격
        except Exception as e:
            logger.error(f"서버 실행 중 오류: {e}")
            print(f"❌ 서버 실행 중 오류가 발생했습니다: {e}")

        print("🛑 정상적인 종료 절차를 시작합니다...")

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