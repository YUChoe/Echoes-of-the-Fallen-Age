#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수도사 이름에 monk 키워드 추가"""

import asyncio
import sys
from src.mud_engine.database import get_database_manager
from src.mud_engine.game.repositories import MonsterRepository


async def main():
    """수도사 이름에 monk 키워드 추가"""
    print("=== 수도사 이름에 monk 키워드 추가 ===\n")

    db_manager = None
    try:
        db_manager = await get_database_manager()
        monster_repo = MonsterRepository(db_manager)

        # church_monk 조회
        monk = await monster_repo.get_by_id("church_monk")

        if not monk:
            print("❌ church_monk을 찾을 수 없습니다.")
            return 1

        print(f"현재 이름:")
        print(f"  영어: {monk.name.get('en')}")
        print(f"  한글: {monk.name.get('ko')}")

        # 이름 업데이트 (monk 키워드 포함)
        updated_name_en = 'Brother Marcus (Monk)'
        updated_name_ko = '마르쿠스 수도사 (monk)'

        # 몬스터 업데이트
        update_data = {
            'name_en': updated_name_en,
            'name_ko': updated_name_ko
        }

        success = await monster_repo.update(monk.id, update_data)

        if success:
            print(f"\n✅ 수도사 이름 업데이트 완료:")
            print(f"  영어: {updated_name_en}")
            print(f"  한글: {updated_name_ko}")
        else:
            print("❌ 수도사 이름 업데이트 실패")
            return 1

        print("\n✅ 작업 완료")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # 데이터베이스 연결 확실히 종료
        if db_manager:
            try:
                await db_manager.close()
            except Exception:
                pass

    return 0


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)