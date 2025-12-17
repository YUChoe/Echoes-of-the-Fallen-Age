#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""방 출구 정보 확인 스크립트"""

import asyncio
import sys
import json
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mud_engine.database import get_database_manager

async def check_exits():
    """방 출구 정보 확인"""
    db_manager = None
    try:
        db_manager = await get_database_manager()

        print("=== 방 출구 정보 ===")

        # town_square 출구 확인
        cursor = await db_manager.execute("SELECT id, exits FROM rooms WHERE id='town_square'")
        result = await cursor.fetchone()
        if result:
            exits = json.loads(result[1]) if result[1] else {}
            print(f"town_square 출구: {exits}")

        # church_1_0 출구 확인
        cursor = await db_manager.execute("SELECT id, exits FROM rooms WHERE id='church_1_0'")
        result = await cursor.fetchone()
        if result:
            exits = json.loads(result[1]) if result[1] else {}
            print(f"church_1_0 출구: {exits}")

        # 동쪽 방향으로 연결된 방 찾기
        cursor = await db_manager.execute("SELECT id, exits FROM rooms")
        rooms = await cursor.fetchall()

        print("\n=== 동쪽 출구가 있는 방들 ===")
        for room in rooms:
            room_id, exits_json = room
            exits = json.loads(exits_json) if exits_json else {}
            if 'east' in exits:
                print(f"{room_id} -> east: {exits['east']}")

        print("\n=== 교회로 연결되는 방들 ===")
        for room in rooms:
            room_id, exits_json = room
            exits = json.loads(exits_json) if exits_json else {}
            for direction, target in exits.items():
                if target == 'church_1_0':
                    print(f"{room_id} -> {direction}: {target}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        if db_manager:
            await db_manager.close()

if __name__ == "__main__":
    asyncio.run(check_exits())