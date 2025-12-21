#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""템플릿 location_type 확인 스크립트"""

import asyncio
import sys
from src.mud_engine.database import get_database_manager


async def main():
    """메인 함수"""
    print("=== 템플릿 location_type 확인 ===\n")

    db_manager = None
    try:
        db_manager = await get_database_manager()

        # 1. 모든 location_type 값들 조회
        print("1. 모든 location_type 값들:")
        cursor = await db_manager.execute(
            "SELECT DISTINCT location_type FROM game_objects ORDER BY location_type"
        )
        location_types = await cursor.fetchall()

        for loc_type in location_types:
            print(f"  - '{loc_type[0]}'")

        # 2. location_type별 개수 확인
        print(f"\n2. location_type별 개수:")
        cursor = await db_manager.execute(
            "SELECT location_type, COUNT(*) FROM game_objects GROUP BY location_type ORDER BY location_type"
        )
        type_counts = await cursor.fetchall()

        for type_count in type_counts:
            print(f"  - '{type_count[0]}': {type_count[1]}개")

        # 3. 템플릿 아이템들 확인 (location_type이 'template' 또는 'TEMPLATE'인 것들)
        print(f"\n3. 템플릿 아이템들:")
        cursor = await db_manager.execute(
            "SELECT id, name_ko, location_type, location_id FROM game_objects WHERE location_type LIKE '%template%' OR location_type LIKE '%TEMPLATE%'"
        )
        template_items = await cursor.fetchall()

        if template_items:
            for item in template_items:
                print(f"  - {item[1]} (ID: {item[0]}, 위치: {item[2]}:{item[3]})")
        else:
            print("  - 템플릿 아이템 없음")

        # 4. 각 location_type의 샘플 데이터 확인
        print(f"\n4. 각 location_type 샘플 데이터:")
        for loc_type in location_types:
            cursor = await db_manager.execute(
                "SELECT id, name_ko, location_id FROM game_objects WHERE location_type = ? LIMIT 3",
                (loc_type[0],)
            )
            samples = await cursor.fetchall()

            print(f"  - '{loc_type[0]}' 샘플:")
            for sample in samples:
                print(f"    * {sample[1]} (ID: {sample[0]}, location_id: {sample[2]})")

        print("\n✅ 확인 완료")
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