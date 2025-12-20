#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""사용자 목록 조회 스크립트"""

import asyncio
import sys
from src.mud_engine.database import get_database_manager


async def main():
    """메인 함수"""
    print("=== 사용자 목록 조회 ===\n")

    db_manager = None
    try:
        db_manager = await get_database_manager()

        # 모든 사용자 목록 조회 (실제 방 좌표 포함)
        cursor = await db_manager.execute("""
            SELECT p.id, p.username, p.display_name, p.is_admin, p.gold, p.stat_level,
                   p.last_login, p.created_at,
                   COALESCE(r.x, 0) as room_x, COALESCE(r.y, 0) as room_y,
                   (SELECT COUNT(*) FROM game_objects WHERE location_type = 'player' AND location_id = p.id) as inventory_count,
                   (SELECT COUNT(*) FROM game_objects WHERE location_type = 'equipped' AND location_id = p.id) as equipped_count
            FROM players p
            LEFT JOIN rooms r ON p.last_room_id = r.id
            ORDER BY p.created_at DESC
        """)

        users = await cursor.fetchall()

        if not users:
            print("등록된 사용자가 없습니다.")
            return 0

        print(f"총 {len(users)}명의 사용자:")
        print("=" * 80)

        # 헤더 출력
        print(f"{'No':<3} {'사용자명':<12} {'표시명':<12} {'관리자':<4} {'Lv':<3} {'골드':<6} {'위치':<8} {'아이템':<8} {'로그인':<10}")
        print("-" * 80)

        for i, (user_id, username, display_name, is_admin, gold, level, last_login, created_at, x, y, inv_count, eq_count) in enumerate(users, 1):
            # 데이터 포맷팅
            username_short = username[:11] if len(username) > 11 else username
            display_short = (display_name[:11] if display_name and len(display_name) > 11 else display_name) or "없음"
            admin_mark = "관리" if is_admin else "일반"
            location = f"({x or 0},{y or 0})"
            items = f"{inv_count}+{eq_count}"

            # 로그인 날짜 포맷팅 (YYYY-MM-DD 형식으로 단축)
            if last_login:
                try:
                    login_date = last_login.split('T')[0] if 'T' in last_login else last_login.split()[0]
                except:
                    login_date = "오류"
            else:
                login_date = "없음"

            print(f"{i:<3} {username_short:<12} {display_short:<12} {admin_mark:<4} {level:<3} {gold:<6} {location:<8} {items:<8} {login_date:<10}")

        print("-" * 80)

        # 상세 정보 (선택적으로 표시)
        print("\n상세 정보:")
        for i, (user_id, username, display_name, is_admin, gold, level, last_login, created_at, x, y, inv_count, eq_count) in enumerate(users[:3], 1):  # 처음 3명만
            print(f"{i}. {username} (ID: {user_id[:8]}...)")
            print(f"   위치: ({x or 0}, {y or 0}), 아이템: 인벤토리 {inv_count}개 + 장착 {eq_count}개")
            print(f"   가입: {created_at.split('T')[0]}, 로그인: {last_login.split('T')[0] if last_login and 'T' in last_login else (last_login or '없음')}")

        if len(users) > 3:
            print(f"   ... 및 {len(users) - 3}명 더")

        print("\n사용자 삭제 명령어 예시:")
        if users:
            first_user = users[0]
            print(f"./script_test.sh delete_user {first_user[1]}")
            print(f"또는")
            print(f"./script_test.sh delete_user {first_user[0]}")

        print("\n✅ 조회 완료")
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