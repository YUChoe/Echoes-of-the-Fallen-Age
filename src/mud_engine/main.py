"""
MUD Engine 메인 실행 파일
"""

import asyncio
import logging
import os

from dotenv import load_dotenv

from .database import get_database_manager, close_database_manager
from .game.managers import PlayerManager
from .server.server import MudServer


def setup_logging():
    """로깅 설정"""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("mud_engine.log", encoding="utf-8")
        ]
    )


async def main():
    """메인 함수"""
    load_dotenv()
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("MUD Engine 시작 중...")
    print("🎮 Python MUD Engine v0.1.0")

    server = None
    try:
        # 데이터베이스 초기화
        logger.info("데이터베이스 매니저 생성 중...")
        db_manager = await get_database_manager()
        logger.info("데이터베이스 매니저 생성 완료.")

        # 관리자 클래스 초기화
        logger.info("게임 관리자 클래스 초기화 중...")
        player_repo = db_manager.get_repository("players")
        player_manager = PlayerManager(player_repo)
        logger.info("게임 관리자 클래스 초기화 완료.")

        # 서버 초기화 및 시작
        host = os.getenv("SERVER_HOST", "127.0.0.1")
        port = int(os.getenv("SERVER_PORT", "8080"))
        server = MudServer(host, port, player_manager)
        await server.start()

        print(f"🌐 서버가 http://{host}:{port} 에서 실행 중입니다.")
        print("Ctrl+C를 눌러 서버를 종료할 수 있습니다.")

        # 서버가 계속 실행되도록 유지
        await asyncio.Event().wait()

    except Exception as e:
        logger.error(f"초기화 또는 실행 중 오류 발생: {e}", exc_info=True)
        print(f"❌ 치명적인 오류 발생: {e}")
    finally:
        logger.info("MUD Engine 종료 절차 시작...")
        if server:
            await server.stop()
        
        await close_database_manager()
        logger.info("MUD Engine이 성공적으로 종료되었습니다.")
        print("👋 MUD Engine 종료.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass # main 함수의 finally 블록에서 종료 처리를 하므로 여기서는 pass
