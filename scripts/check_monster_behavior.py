#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""몬스터 behavior 값 확인 스크립트"""

import asyncio
import sys
from src.mud_engine.database import get_database_manager


async def main():
    """메인 함수"""
    print("=== 몬스터 behavior 값 확인 ===\n")

    db_manager = None
    try:
        db_manager = await get_database_manager()

        # 모든 몬스터의 behavior 값 확인
        cursor = await db_manager.execute(
            "SELECT id, name_ko, behavior FROM monsters"
        )
        monsters = await cursor.fetchall()

        print(f"총 {len(monsters)}개의 몬스터 발견\n")

        behavior_counts = {}
        for monster_id, name_ko, behavior in monsters:
            print(f"- {name_ko} ({monster_id}): behavior = '{behavior}'")
            behavior_counts[behavior] = behavior_counts.get(behavior, 0) + 1

        print(f"\n=== Behavior 값 통계 ===")
        for behavior, count in behavior_counts.items():
            print(f"  {behavior}: {count}개")

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
