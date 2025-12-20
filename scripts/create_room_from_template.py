#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""템플릿 JSON을 사용하여 특정 좌표에 방을 생성하는 유틸리티"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any

from src.mud_engine.database import get_database_manager
from src.mud_engine.game.models import Room


async def load_template(template_path: str) -> Dict[str, Any]:
    """템플릿 JSON 파일 로드"""
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = json.load(f)

        # 필수 필드 검증
        required_fields = ['description']
        for field in required_fields:
            if field not in template:
                raise ValueError(f"템플릿에 필수 필드 '{field}'가 없습니다")

        if not isinstance(template['description'], dict):
            raise ValueError("description은 딕셔너리 형태여야 합니다")

        return template
    except FileNotFoundError:
        raise FileNotFoundError(f"템플릿 파일을 찾을 수 없습니다: {template_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 파싱 오류: {e}")


async def check_room_exists(db_manager, x: int, y: int) -> bool:
    """방 존재 여부 확인 (좌표 기준)"""
    cursor = await db_manager.execute(
        "SELECT id FROM rooms WHERE x = ? AND y = ?", (x, y)
    )
    if await cursor.fetchone():
        return True

    return False


async def create_room_from_template(template_path: str, x: int, y: int) -> bool:
    """템플릿을 사용하여 방 생성"""
    print(f"=== 방 생성 시작 ===")
    print(f"템플릿: {template_path}")
    print(f"좌표: ({x}, {y})")

    db_manager = None
    try:
        # 템플릿 로드
        template = await load_template(template_path)
        print(f"템플릿 로드 완료")

        # 데이터베이스 연결
        db_manager = await get_database_manager()

        # 중복 확인 (좌표 기준)
        if await check_room_exists(db_manager, x, y):
            print(f"❌ 좌표 ({x}, {y})에 방이 이미 존재합니다")
            return False

        # Room 객체 생성 (ID는 자동 생성)
        room_data = {
            'description': template['description'],
            'x': x,
            'y': y
        }

        room = Room.from_dict(room_data)

        # 데이터베이스에 저장
        await db_manager.execute("""
            INSERT INTO rooms (id, description_en, description_ko, x, y)
            VALUES (?, ?, ?, ?, ?)
        """, (
            room.id,
            room.description.get('en', ''),
            room.description.get('ko', ''),
            room.x,
            room.y
        ))

        await db_manager.commit()

        print(f"✅ 방 생성 완료!")
        print(f"   ID: {room.id}")
        print(f"   좌표: ({room.x}, {room.y})")
        print(f"   설명(EN): {room.description.get('en', 'N/A')}")
        print(f"   설명(KO): {room.description.get('ko', 'N/A')}")

        return True

    except Exception as e:
        print(f"❌ 방 생성 실패: {e}")
        if db_manager:
            await db_manager.rollback()
        return False
    finally:
        if db_manager:
            await db_manager.close()


def print_usage():
    """사용법 출력"""
    print("사용법:")
    print("  python scripts/create_room_from_template.py <템플릿파일> <x좌표> <y좌표>")
    print()
    print("예시:")
    print("  python scripts/create_room_from_template.py configs/rooms/forest_clearing.json 5 3")
    print("  python scripts/create_room_from_template.py configs/room_template.json -2 8")
    print()
    print("템플릿 파일 형식:")
    print('  {')
    print('    "description": {')
    print('      "en": "English description",')
    print('      "ko": "한국어 설명"')
    print('    }')
    print('  }')
    print()
    print("참고:")
    print("  - 방 ID는 UUID로 자동 생성됩니다")
    print("  - 좌표 중복 시 생성이 거부됩니다")


async def main():
    """메인 함수"""
    if len(sys.argv) < 4:
        print_usage()
        return 1

    template_path = sys.argv[1]

    try:
        x = int(sys.argv[2])
        y = int(sys.argv[3])
    except ValueError:
        print("❌ 좌표는 정수여야 합니다")
        return 1

    # 템플릿 파일 존재 확인
    if not Path(template_path).exists():
        print(f"❌ 템플릿 파일이 존재하지 않습니다: {template_path}")
        return 1

    success = await create_room_from_template(template_path, x, y)
    return 0 if success else 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)