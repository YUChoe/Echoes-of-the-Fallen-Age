#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WAL 파일 정리 스크립트"""

import asyncio
import sys
from src.mud_engine.database import get_database_manager


async def main():
    """WAL 체크포인트 실행하여 WAL 파일 정리"""
    print("=== WAL 파일 정리 시작 ===\n")

    db_manager = None
    try:
        db_manager = await get_database_manager()

        print("WAL 체크포인트 실행 중...")
        cursor = await db_manager.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        result = await cursor.fetchone()
        print(f"WAL 체크포인트 결과: {result}")

        await db_manager.commit()
        print("WAL 체크포인트 완료")

        # WAL 모드 상태 확인
        cursor = await db_manager.execute("PRAGMA journal_mode")
        journal_mode = await cursor.fetchone()
        print(f"저널 모드: {journal_mode}")

        print("\n✅ WAL 파일 정리 완료")
        return 0

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if db_manager:
            try:
                await db_manager.close()
            except Exception:
                pass


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)