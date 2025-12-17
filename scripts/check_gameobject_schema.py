#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""게임 오브젝트 스키마 확인 스크립트"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mud_engine.database import get_database_manager

async def check_gameobject_schema():
    """게임 오브젝트 스키마 확인"""
    db_manager = None
    try:
        db_manager = await get_database_manager()

        print("=== 게임 오브젝트 테이블 스키마 확인 ===")

        # 게임 오브젝트 테이블 스키마 확인
        cursor = await db_manager.execute("PRAGMA table_info(game_objects)")
        columns = await cursor.fetchall()

        print("game_objects 테이블 컬럼:")
        for col in columns:
            cid, name, type_name, notnull, default_value, pk = col
            print(f"  {name}: {type_name} (null: {not notnull}, default: {default_value}, pk: {pk})")

        # 샘플 데이터 확인
        print("\n=== 샘플 게임 오브젝트 데이터 ===")
        cursor = await db_manager.execute("SELECT * FROM game_objects LIMIT 3")
        objects = await cursor.fetchall()

        if objects:
            # 컬럼명 가져오기
            cursor = await db_manager.execute("PRAGMA table_info(game_objects)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]

            for obj in objects:
                print(f"오브젝트: {obj[1] if len(obj) > 1 else 'unknown'}")  # name_en 또는 첫 번째 컬럼
                for i, value in enumerate(obj):
                    if i < len(column_names):
                        if isinstance(value, str) and len(value) > 50:
                            value = value[:50] + "..."
                        print(f"  {column_names[i]}: {value}")
                print()
        else:
            print("게임 오브젝트 데이터가 없습니다.")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        if db_manager:
            await db_manager.close()

if __name__ == "__main__":
    asyncio.run(check_gameobject_schema())