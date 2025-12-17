#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""플레이어 스폰 위치 수정 스크립트"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mud_engine.database import get_database_manager

async def fix_player_spawn():
    """플레이어 스폰 위치를 town_square로 수정"""
    db_manager = None
    try:
        db_manager = await get_database_manager()

        print("=== 플레이어 스폰 위치 수정 ===")

        # testuser의 현재 위치 확인
        cursor = await db_manager.execute("SELECT username, last_room_id FROM players WHERE username=?", ('testuser',))
        result = await cursor.fetchone()
        print(f"수정 전 testuser 위치: {result}")

        # testuser를 town_square로 이동
        await db_manager.execute("UPDATE players SET last_room_id = ? WHERE username = ?", ('town_square', 'testuser'))
        print("testuser를 town_square로 이동 완료")

        # 수정 결과 확인
        cursor = await db_manager.execute("SELECT username, last_room_id FROM players WHERE username=?", ('testuser',))
        result = await cursor.fetchone()
        print(f"수정 후 testuser 위치: {result}")

        # town_square가 (0,0) 좌표인지 확인하고 수정
        cursor = await db_manager.execute("SELECT id, x, y FROM rooms WHERE id='town_square'")
        result = await cursor.fetchone()
        print(f"town_square 좌표: {result}")

        if result and (result[1] != 0 or result[2] != 0):
            print("town_square를 (0,0) 좌표로 이동 중...")
            await db_manager.execute("UPDATE rooms SET x = 0, y = 0 WHERE id = 'town_square'")
            print("town_square 좌표 수정 완료")

        # 최종 확인
        cursor = await db_manager.execute("SELECT id, x, y FROM rooms WHERE id='town_square'")
        result = await cursor.fetchone()
        print(f"최종 town_square 좌표: {result}")

        print("\n✅ 플레이어 스폰 위치 수정 완료")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        if db_manager:
            await db_manager.close()

if __name__ == "__main__":
    asyncio.run(fix_player_spawn())