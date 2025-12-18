#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수도사 몬스터 이름 확인"""

import asyncio
import sys
import json
from src.mud_engine.database import get_database_manager
from src.mud_engine.game.repositories import MonsterRepository


async def main():
    """수도사 몬스터 이름 확인"""
    print("=== 수도사 몬스터 이름 확인 ===\n")

    db_manager = None
    try:
        db_manager = await get_database_manager()
        monster_repo = MonsterRepository(db_manager)

        # church_monk 조회
        monk = await monster_repo.get_by_id("church_monk")

        if monk:
            print(f"ID: {monk.id}")
            print(f"영어 이름: {monk.name.get('en', 'N/A')}")
            print(f"한글 이름: {monk.name.get('ko', 'N/A')}")
            print(f"레벨: {monk.level}")
            print(f"타입: {monk.monster_type}")
            print(f"행동: {monk.behavior}")
            print(f"팩션: {monk.faction_id}")
            print(f"좌표: ({monk.x}, {monk.y})")

            if monk.properties:
                print(f"\nProperties:")
                if isinstance(monk.properties, str):
                    props = json.loads(monk.properties)
                else:
                    props = monk.properties
                print(json.dumps(props, indent=2, ensure_ascii=False))
        else:
            print("❌ church_monk을 찾을 수 없습니다.")

        print("\n✅ 확인 완료")

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
