#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""사용자 삭제 및 아이템 정리 스크립트"""

import asyncio
import sys
from src.mud_engine.database import get_database_manager


async def main():
    """메인 함수"""
    print("=== 사용자 삭제 스크립트 ===\n")

    if len(sys.argv) < 2:
        print("사용법: python delete_user.py <사용자명_또는_ID>")
        print("예시:")
        print("  python delete_user.py testuser")
        print("  python delete_user.py player_id_here")
        return 1

    target = sys.argv[1]

    db_manager = None
    try:
        db_manager = await get_database_manager()

        # 삭제할 사용자 찾기
        target_player = None

        # 먼저 사용자명으로 검색
        cursor = await db_manager.execute(
            "SELECT id, username, display_name, is_admin FROM players WHERE username = ?",
            (target,)
        )
        player_data = await cursor.fetchone()

        if not player_data:
            # ID로 검색
            cursor = await db_manager.execute(
                "SELECT id, username, display_name, is_admin FROM players WHERE id = ?",
                (target,)
            )
            player_data = await cursor.fetchone()

        if not player_data:
            print(f"❌ 사용자 '{target}'를 찾을 수 없습니다.")
            return 1

        player_id, username, display_name, is_admin = player_data

        print(f"삭제할 사용자:")
        print(f"  ID: {player_id}")
        print(f"  사용자명: {username}")
        print(f"  표시명: {display_name or '없음'}")
        print(f"  관리자: {'예' if is_admin else '아니오'}")

        # 관리자 계정 삭제 경고
        if is_admin:
            print("\n⚠️  경고: 이 계정은 관리자 계정입니다!")
            admin_confirm = input("정말로 관리자 계정을 삭제하시겠습니까? (DELETE_ADMIN 입력): ")
            if admin_confirm != "DELETE_ADMIN":
                print("관리자 계정 삭제가 취소되었습니다.")
                return 0

        # 확인 요청
        confirm = input(f"\n정말로 사용자 '{username}'를 삭제하시겠습니까? (yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            print("삭제가 취소되었습니다.")
            return 0

        print(f"\n=== 사용자 삭제 진행 ===")

        # 1. 사용자가 소유한 아이템들 확인 및 삭제
        print("1. 사용자 아이템 확인 중...")

        # 인벤토리 아이템 확인
        cursor = await db_manager.execute(
            "SELECT COUNT(*) FROM game_objects WHERE location_type = 'player' AND location_id = ?",
            (player_id,)
        )
        inventory_count = await cursor.fetchone()

        if inventory_count and inventory_count[0] > 0:
            print(f"  인벤토리 아이템: {inventory_count[0]}개")

            # 아이템 목록 표시
            cursor = await db_manager.execute(
                "SELECT name_ko, object_type, category FROM game_objects WHERE location_type = 'player' AND location_id = ?",
                (player_id,)
            )
            items = await cursor.fetchall()

            for name_ko, object_type, category in items[:10]:  # 처음 10개만 표시
                print(f"    - {name_ko} ({object_type}/{category})")

            if len(items) > 10:
                print(f"    ... 및 {len(items) - 10}개 더")

            # 인벤토리 아이템 삭제
            await db_manager.execute(
                "DELETE FROM game_objects WHERE location_type = 'player' AND location_id = ?",
                (player_id,)
            )
            print(f"    ✅ {inventory_count[0]}개 아이템 삭제 완료")
        else:
            print("  인벤토리에 아이템이 없습니다.")

        # 2. 장착된 아이템들 확인 및 삭제
        print("\n2. 장착된 아이템 확인 중...")

        cursor = await db_manager.execute(
            "SELECT COUNT(*) FROM game_objects WHERE location_type = 'equipped' AND location_id = ?",
            (player_id,)
        )
        equipped_count = await cursor.fetchone()

        if equipped_count and equipped_count[0] > 0:
            print(f"  장착된 아이템: {equipped_count[0]}개")

            # 장착된 아이템 목록 표시
            cursor = await db_manager.execute(
                "SELECT name_ko, equipment_slot FROM game_objects WHERE location_type = 'equipped' AND location_id = ?",
                (player_id,)
            )
            equipped_items = await cursor.fetchall()

            for name_ko, slot in equipped_items:
                print(f"    - {name_ko} ({slot})")

            # 장착된 아이템 삭제
            await db_manager.execute(
                "DELETE FROM game_objects WHERE location_type = 'equipped' AND location_id = ?",
                (player_id,)
            )
            print(f"    ✅ {equipped_count[0]}개 장착 아이템 삭제 완료")
        else:
            print("  장착된 아이템이 없습니다.")

        # 3. 사용자 관련 데이터 정리
        print("\n3. 사용자 관련 데이터 정리 중...")

        # 퀘스트 진행 상황 등 추가 데이터가 있다면 여기서 정리
        # (현재 스키마에서는 players 테이블에 모든 정보가 포함되어 있음)

        # 4. 캐릭터 테이블에서 삭제 (있다면)
        cursor = await db_manager.execute(
            "SELECT COUNT(*) FROM characters WHERE player_id = ?",
            (player_id,)
        )
        character_count = await cursor.fetchone()

        if character_count and character_count[0] > 0:
            print(f"  캐릭터 데이터: {character_count[0]}개")
            await db_manager.execute(
                "DELETE FROM characters WHERE player_id = ?",
                (player_id,)
            )
            print(f"    ✅ {character_count[0]}개 캐릭터 데이터 삭제 완료")

        # 5. 플레이어 테이블에서 삭제
        print("\n4. 플레이어 계정 삭제 중...")

        await db_manager.execute(
            "DELETE FROM players WHERE id = ?",
            (player_id,)
        )

        print(f"\n✅ 사용자 삭제 완료!")
        print(f"삭제된 사용자: {username} (ID: {player_id})")
        print(f"삭제된 아이템: 인벤토리 {inventory_count[0] if inventory_count else 0}개 + 장착 {equipped_count[0] if equipped_count else 0}개")

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