#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""town_square 디버깅 스크립트"""

import asyncio
import sys
import json
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mud_engine.database import get_database_manager

async def debug_town_square():
    """town_square 상세 디버깅"""
    db_manager = None
    try:
        db_manager = await get_database_manager()

        print("=== town_square 상세 정보 ===")

        # town_square 전체 정보
        cursor = await db_manager.execute("SELECT * FROM rooms WHERE id='town_square'")
        result = await cursor.fetchone()
        if result:
            print(f"town_square 전체 데이터: {result}")
            exits = json.loads(result[3]) if result[3] else {}
            print(f"town_square 출구: {exits}")

            # 각 출구의 목적지 방 확인
            for direction, target_id in exits.items():
                cursor = await db_manager.execute("SELECT id, description_en, description_ko FROM rooms WHERE id=?", (target_id,))
                target_room = await cursor.fetchone()
                if target_room:
                    print(f"  {direction} -> {target_id}: {target_room[1][:50]}...")
                else:
                    print(f"  {direction} -> {target_id}: 방을 찾을 수 없음")

        print("\n=== church_1_0 정보 ===")
        cursor = await db_manager.execute("SELECT * FROM rooms WHERE id='church_1_0'")
        result = await cursor.fetchone()
        if result:
            print(f"church_1_0 전체 데이터: {result}")

        print("\n=== 새 플레이어 위치 확인 ===")
        cursor = await db_manager.execute("SELECT username, last_room_id FROM players WHERE username='tutorial_user'")
        result = await cursor.fetchone()
        if result:
            print(f"tutorial_user 위치: {result}")

        print("\n=== 0,0 좌표 방 확인 ===")
        cursor = await db_manager.execute("SELECT id, description_en FROM rooms WHERE x=0 AND y=0")
        result = await cursor.fetchone()
        if result:
            print(f"(0,0) 좌표 방: {result}")

            # 이 방의 출구 확인
            cursor = await db_manager.execute("SELECT exits FROM rooms WHERE id=?", (result[0],))
            exits_result = await cursor.fetchone()
            if exits_result:
                exits = json.loads(exits_result[0]) if exits_result[0] else {}
                print(f"(0,0) 방의 출구: {exits}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        if db_manager:
            await db_manager.close()

if __name__ == "__main__":
    asyncio.run(debug_town_square())