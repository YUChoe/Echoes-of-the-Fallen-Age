#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""방 상태 확인 스크립트"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mud_engine.database import get_database_manager

async def check_room_status():
    """방 상태 확인"""
    db_manager = None
    try:
        db_manager = await get_database_manager()

        print("=== 현재 방 상태 확인 ===")

        # 1. 모든 좌표 (0,0), (1,0), (2,0) 확인
        coordinates = [(0, 0), (1, 0), (2, 0)]

        for x, y in coordinates:
            cursor = await db_manager.execute("SELECT id, description_ko FROM rooms WHERE x=? AND y=?", (x, y))
            result = await cursor.fetchone()
            if result:
                desc = result[1][:30] if result[1] else "설명 없음"
                print(f"({x},{y}): {result[0]} - {desc}...")
            else:
                print(f"({x},{y}): 방 없음")

        # 2. church_1_0 방 존재 여부 확인
        cursor = await db_manager.execute("SELECT x, y FROM rooms WHERE id = 'church_1_0'")
        result = await cursor.fetchone()
        if result:
            print(f"church_1_0 위치: ({result[0]}, {result[1]})")
        else:
            print("church_1_0 방이 존재하지 않음")

        # 3. 교회 수도사 위치 확인
        cursor = await db_manager.execute("SELECT current_room_id FROM npcs WHERE id = 'church_monk'")
        result = await cursor.fetchone()
        if result:
            monk_room = result[0]
            print(f"교회 수도사 위치: {monk_room}")

            # 수도사가 있는 방이 실제로 존재하는지 확인
            cursor = await db_manager.execute("SELECT x, y FROM rooms WHERE id = ?", (monk_room,))
            coord_result = await cursor.fetchone()
            if coord_result:
                print(f"수도사 방 좌표: ({coord_result[0]}, {coord_result[1]})")
            else:
                print("❌ 수도사가 있는 방이 존재하지 않음!")
        else:
            print("교회 수도사를 찾을 수 없음")

        # 4. (2,0) 근처 방들 확인
        print("\n=== (2,0) 근처 방들 확인 ===")
        cursor = await db_manager.execute("SELECT id, x, y, description_ko FROM rooms WHERE x BETWEEN 1 AND 3 AND y BETWEEN -1 AND 1")
        results = await cursor.fetchall()
        for result in results:
            room_id, x, y, desc = result
            desc_short = desc[:30] if desc else "설명 없음"
            print(f"({x},{y}): {room_id} - {desc_short}...")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        if db_manager:
            await db_manager.close()

if __name__ == "__main__":
    asyncio.run(check_room_status())