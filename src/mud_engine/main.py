"""
MUD Engine 메인 실행 파일
"""

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv


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
    # 환경 변수 로드
    load_dotenv()

    # 로깅 설정
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("MUD Engine 시작 중...")

    # TODO: 서버 시작 로직 구현
    print("🎮 Python MUD Engine v0.1.0")
    print("🌐 서버 준비 중...")

    # 임시로 5초 대기
    await asyncio.sleep(5)
    print("✅ 기본 구조 설정 완료!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 MUD Engine 종료")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        logging.exception("예상치 못한 오류")