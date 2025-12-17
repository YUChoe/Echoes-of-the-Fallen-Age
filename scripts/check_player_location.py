#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""플레이어 위치 및 방 정보 확인 스크립트"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mud_engine.database import get_database_manager

async def check_player_and_rooms():
    """플레이어 위치와 방 정보 확인"""
    db_manager = None
    try:
        db_manager = await get_database_manager()

        print("=== 플레이어 정보 ===")
        cursor = await db_manager.execute("SELECT username, last_room_id FROM players WHERE username=?", ('testuser',))
        result = await cursor.fetchone()
        print(f"testuser 위치: {result}")

        print("\n=== 방 정보 ===")
        cursor = await db_manager.execute("SELECT id, x, y FROM rooms WHERE x=0 AND y=0")
        result = await cursor.fetchone()
        print(f"(0,0) 좌표 방: {result}")

        cursor = await db_manager.execute("SELECT id FROM rooms WHERE id='town_square'")
        result = await cursor.fetchone()
        print(f"town_square: {result}")

        cursor = await db_manager.execute("SELECT id FROM rooms WHERE id='church_1_0'")
        result = await cursor.fetchone()
        print(f"church_1_0: {result}")

        print("\n=== 교회 방 상세 정보 ===")
        cursor = await db_manager.execute("SELECT * FROM rooms WHERE id='church_1_0'")
        result = await cursor.fetchone()
        if result:
            print(f"교회 방: {result}")
        else:
            print("교회 방을 찾을 수 없습니다")

        print("\n=== NPC 정보 ===")
        cursor = await db_manager.execute("SELECT id, current_room_id FROM npcs WHERE id='church_monk'")
        result = await cursor.fetchone()
        if result:
            print(f"교회 수도사: {result}")
        else:
            print("교회 수도사를 찾을 수 없습니다")

    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        if db_manager:
            await db_manager.close()

if __name__ == "__main__":
    asyncio.run(check_player_and_rooms())