#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""플레이어를 관리자로 설정하는 스크립트"""

import asyncio
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mud_engine.database.connection import DatabaseManager
from src.mud_engine.game.repositories import PlayerRepository


async def make_admin(username: str):
    """플레이어를 관리자로 설정"""

    # 데이터베이스 매니저 초기화
    db_manager = DatabaseManager()
    await db_manager.initialize()

    try:
        # 플레이어 리포지토리 생성
        player_repo = PlayerRepository(db_manager)

        # 플레이어 조회
        player = await player_repo.get_by_username(username)

        if not player:
            print(f"❌ 플레이어 '{username}'을 찾을 수 없습니다.")
            return False

        # 이미 관리자인지 확인
        if player.is_admin:
            print(f"✅ 플레이어 '{username}'은 이미 관리자입니다.")
            return True

        # 데이터베이스 업데이트 (관리자 권한 부여)
        updated_player = await player_repo.update(player.id, {"is_admin": True})

        if updated_player:
            print(f"✅ 플레이어 '{username}'에게 관리자 권한을 부여했습니다.")
            return True
        else:
            print(f"❌ 플레이어 '{username}' 업데이트에 실패했습니다.")
            return False

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

    finally:
        # 데이터베이스 연결 종료
        await db_manager.close()


async def main():
    """메인 함수"""
    if len(sys.argv) != 2:
        print("사용법: python scripts/make_admin.py <사용자명>")
        print("예시: python scripts/make_admin.py pp")
        sys.exit(1)

    username = sys.argv[1]
    print(f"🔧 플레이어 '{username}'에게 관리자 권한을 부여합니다...")

    success = await make_admin(username)

    if success:
        print("🎉 관리자 권한 부여 완료!")
    else:
        print("💥 관리자 권한 부여 실패!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())