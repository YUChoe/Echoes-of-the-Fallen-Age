#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""npcs 테이블 구조 확인 스크립트"""

import asyncio
import sys
from src.mud_engine.database import get_database_manager


async def main():
    """메인 함수"""
    print("=== npcs 테이블 구조 확인 ===\n")

    db_manager = None
    try:
        db_manager = await get_database_manager()

        # npcs 테이블 존재 여부 확인
        cursor = await db_manager.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='npcs'
        """)
        table_exists = await cursor.fetchone()

        if not table_exists:
            print("❌ npcs 테이블이 존재하지 않습니다.")
            return 1

        print("✅ npcs 테이블이 존재합니다.")

        # 테이블 구조 확인
        cursor = await db_manager.execute("PRAGMA table_info(npcs)")
        columns = await cursor.fetchall()

        print("\n📋 npcs 테이블 컬럼 정보:")
        for col in columns:
            cid, name, type_name, notnull, default_value, pk = col
            print(f"  - {name}: {type_name} (NOT NULL: {bool(notnull)}, DEFAULT: {default_value}, PK: {bool(pk)})")

        # 데이터 개수 확인
        cursor = await db_manager.execute("SELECT COUNT(*) FROM npcs")
        count = await cursor.fetchone()
        print(f"\n📊 npcs 테이블 데이터 개수: {count[0]}개")

        # 샘플 데이터 확인 (있다면)
        if count[0] > 0:
            cursor = await db_manager.execute("SELECT * FROM npcs LIMIT 3")
            samples = await cursor.fetchall()
            print("\n📋 샘플 데이터:")
            for i, sample in enumerate(samples, 1):
                print(f"  {i}. {sample}")

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