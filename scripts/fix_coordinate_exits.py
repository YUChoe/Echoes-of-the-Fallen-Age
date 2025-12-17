#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""좌표 방 출구 수정 스크립트"""

import asyncio
import sys
import json
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mud_engine.database import get_database_manager

async def fix_coordinate_exits():
    """(0,0) 좌표 방의 출구를 교회로 연결하도록 수정"""
    db_manager = None
    try:
        db_manager = await get_database_manager()

        print("=== 좌표 방 출구 수정 ===")

        # (0,0) 좌표 방 찾기
        cursor = await db_manager.execute("SELECT id, exits FROM rooms WHERE x=0 AND y=0")
        result = await cursor.fetchone()

        if result:
            room_id, exits_json = result
            exits = json.loads(exits_json) if exits_json else {}

            print(f"수정 전 (0,0) 방 출구: {exits}")

            # 동쪽 출구를 교회로 변경
            exits['east'] = 'church_1_0'

            # 데이터베이스 업데이트
            await db_manager.execute("UPDATE rooms SET exits = ? WHERE id = ?", (json.dumps(exits), room_id))

            print(f"수정 후 (0,0) 방 출구: {exits}")
            print(f"✅ (0,0) 좌표 방 {room_id}의 동쪽 출구를 church_1_0으로 수정 완료")

        # 새 플레이어들을 (0,0) 좌표 방으로 이동
        cursor = await db_manager.execute("SELECT id FROM rooms WHERE x=0 AND y=0")
        result = await cursor.fetchone()

        if result:
            coordinate_room_id = result[0]

            # tutorial_user를 (0,0) 좌표 방으로 이동
            await db_manager.execute("UPDATE players SET last_room_id = ? WHERE username = ?", (coordinate_room_id, 'tutorial_user'))
            print(f"✅ tutorial_user를 (0,0) 좌표 방 {coordinate_room_id}로 이동 완료")

        print("\n=== 수정 결과 확인 ===")
        cursor = await db_manager.execute("SELECT id, exits FROM rooms WHERE x=0 AND y=0")
        result = await cursor.fetchone()
        if result:
            room_id, exits_json = result
            exits = json.loads(exits_json) if exits_json else {}
            print(f"최종 (0,0) 방 출구: {exits}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        if db_manager:
            await db_manager.close()

if __name__ == "__main__":
    asyncio.run(fix_coordinate_exits())