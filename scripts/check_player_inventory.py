#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""플레이어 인벤토리 분석 스크립트"""

import asyncio
import sys
from src.mud_engine.database import get_database_manager


async def main():
    """메인 함수"""
    print("=== 플레이어 인벤토리 분석 ===\n")

    db_manager = None
    try:
        db_manager = await get_database_manager()

        # 1. player5426의 플레이어 ID 조회
        print("1. player5426 플레이어 정보:")
        cursor = await db_manager.execute(
            "SELECT id, username FROM players WHERE username = 'player5426'"
        )
        player_info = await cursor.fetchone()

        if not player_info:
            print("  - player5426을 찾을 수 없음")
            return 1

        player_id = player_info[0]
        print(f"  - ID: {player_id}")
        print(f"  - 사용자명: {player_info[1]}")

        # 2. 현재 인벤토리 아이템들 조회 (INVENTORY)
        print(f"\n2. 현재 인벤토리 아이템들 (location_type='INVENTORY'):")
        cursor = await db_manager.execute(
            "SELECT id, name_ko, location_type, location_id FROM game_objects WHERE location_type = 'INVENTORY' AND location_id = ?",
            (player_id,)
        )
        inventory_items = await cursor.fetchall()

        if inventory_items:
            for item in inventory_items:
                print(f"  - {item[1]} (ID: {item[0]}, 위치: {item[2]}:{item[3]})")
        else:
            print("  - 인벤토리가 비어있음")

        # 3. 모든 location_type으로 해당 플레이어 관련 아이템 검색
        print(f"\n3. 플레이어 관련 모든 아이템들:")
        cursor = await db_manager.execute(
            "SELECT id, name_ko, location_type, location_id FROM game_objects WHERE location_id = ?",
            (player_id,)
        )
        all_player_items = await cursor.fetchall()

        if all_player_items:
            for item in all_player_items:
                print(f"  - {item[1]} (ID: {item[0]}, 위치: {item[2]}:{item[3]})")
        else:
            print("  - 플레이어와 연결된 아이템이 없음")

        # 4. 최근에 생성된 아이템들 확인 (혹시 다른 플레이어에게 갔는지)
        print(f"\n4. 최근 생성된 아이템들 (상위 20개):")
        cursor = await db_manager.execute(
            "SELECT id, name_ko, location_type, location_id, created_at FROM game_objects ORDER BY created_at DESC LIMIT 20"
        )
        recent_items = await cursor.fetchall()

        for item in recent_items:
            print(f"  - {item[1]} (위치: {item[2]}:{item[3]}, 생성: {item[4]})")

        # 5. 골드, 곤봉, 생명의 정수 등 주요 아이템들 위치 확인
        print(f"\n5. 주요 아이템들 위치 확인:")
        main_items = ['골드', '곤봉', '나무 곤봉', '생명의 정수', '횃불', '리넨 상의', '리넨 하의', '성 열쇠']

        for item_name in main_items:
            cursor = await db_manager.execute(
                "SELECT COUNT(*), location_type, location_id FROM game_objects WHERE name_ko = ? GROUP BY location_type, location_id",
                (item_name,)
            )
            locations = await cursor.fetchall()

            if locations:
                print(f"  - {item_name}:")
                for loc in locations:
                    print(f"    * {loc[1]}:{loc[2]} - {loc[0]}개")
            else:
                print(f"  - {item_name}: 없음")

        print("\n✅ 분석 완료")
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