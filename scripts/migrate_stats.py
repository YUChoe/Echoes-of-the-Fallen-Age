#!/usr/bin/env python3
"""
능력치 시스템을 위한 데이터베이스 마이그레이션 스크립트
"""

import asyncio
import logging
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.mud_engine.database.connection import DatabaseManager
from src.mud_engine.database.schema import migrate_database

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def run_migration():
    """마이그레이션 실행"""
    logger.info("능력치 시스템 마이그레이션 시작")

    db_manager = None
    try:
        # DatabaseManager 초기화
        db_manager = DatabaseManager()
        await db_manager.initialize()

        logger.info("데이터베이스 연결 완료")

        # 마이그레이션 실행
        await migrate_database(db_manager)

        logger.info("능력치 시스템 마이그레이션 완료")

    except Exception as e:
        logger.error(f"마이그레이션 실패: {e}", exc_info=True)
        return False
    finally:
        if db_manager:
            await db_manager.close()

    return True


if __name__ == "__main__":
    success = asyncio.run(run_migration())
    if not success:
        sys.exit(1)

    print("✅ 능력치 시스템 마이그레이션이 성공적으로 완료되었습니다!")