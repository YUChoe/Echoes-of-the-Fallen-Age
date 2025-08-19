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

    print("🎮 Python MUD Engine v0.1.0")
    print("🌐 서버 준비 중...")

    db_manager = None

    try:
        # 데이터베이스 초기화
        from .database import get_database_manager, close_database_manager

        print("📊 데이터베이스 초기화 중...")
        logger.info("데이터베이스 매니저 생성 시작")

        db_manager = await get_database_manager()
        logger.info("데이터베이스 매니저 생성 완료")

        # 헬스체크
        print("🔍 데이터베이스 연결 확인 중...")
        logger.info("헬스체크 시작")

        if await db_manager.health_check():
            print("✅ 데이터베이스 연결 성공")
            logger.info("헬스체크 성공")
        else:
            print("❌ 데이터베이스 연결 실패")
            logger.error("헬스체크 실패")
            return

        # 테이블 정보 출력
        print("📋 테이블 정보 확인 중...")
        tables = ['players', 'characters', 'rooms', 'game_objects', 'translations']
        for table in tables:
            try:
                logger.info(f"테이블 {table} 레코드 수 조회 시작")
                count_result = await db_manager.fetch_one(f"SELECT COUNT(*) as count FROM {table}")
                count = count_result['count'] if count_result else 0
                print(f"📋 {table}: {count}개 레코드")
                logger.info(f"테이블 {table}: {count}개 레코드")
            except Exception as e:
                print(f"⚠️  {table} 테이블 확인 실패: {e}")
                logger.warning(f"테이블 {table} 확인 실패: {e}")

        print("✅ 데이터베이스 초기화 완료!")
        print("🚀 MUD Engine 준비 완료!")
        logger.info("MUD Engine 초기화 완료")

        # 데모 실행 (3초로 단축)
        print("⏱️  3초 후 종료됩니다...")
        logger.info("데모 실행 중 (3초)")

        for i in range(3, 0, -1):
            print(f"⏰ {i}초...")
            await asyncio.sleep(1)

        print("🏁 데모 완료!")
        logger.info("데모 완료")

    except Exception as e:
        logger.error(f"초기화 실패: {e}")
        print(f"❌ 초기화 실패: {e}")
        raise

    finally:
        # 리소스 정리
        print("🧹 리소스 정리 중...")
        logger.info("리소스 정리 시작")

        try:
            from .database import close_database_manager
            await close_database_manager()
            logger.info("데이터베이스 연결 종료 완료")
            print("✅ 데이터베이스 연결 종료")
        except Exception as e:
            logger.error(f"데이터베이스 종료 실패: {e}")
            print(f"⚠️  데이터베이스 종료 실패: {e}")

        print("👋 MUD Engine 종료")
        logger.info("MUD Engine 정상 종료")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 MUD Engine 종료")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        logging.exception("예상치 못한 오류")