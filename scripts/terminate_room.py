#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""방 삭제 및 주변 연결 정리 스크립트"""

import asyncio
import sys
from src.mud_engine.database import get_database_manager


async def main():
    """메인 함수"""
    print("=== 방 삭제 스크립트 ===\n")

    if len(sys.argv) < 2:
        print("사용법: python terminate_room.py <방_ID_또는_좌표>")
        print("예시:")
        print("  python terminate_room.py room_id_here")
        print("  python terminate_room.py 5,7")
        return 1

    target = sys.argv[1]

    db_manager = None
    try:
        db_manager = await get_database_manager()

        from src.mud_engine.game.repositories import RoomRepository
        room_repo = RoomRepository(db_manager)

        # 삭제할 방 찾기
        target_room = None
        target_x, target_y = None, None

        if ',' in target:
            # 좌표로 검색
            try:
                x_str, y_str = target.split(',')
                target_x, target_y = int(x_str.strip()), int(y_str.strip())

                cursor = await db_manager.execute(
                    "SELECT id FROM rooms WHERE x = ? AND y = ?",
                    (target_x, target_y)
                )
                room_data = await cursor.fetchone()

                if room_data:
                    target_room = await room_repo.get_by_id(room_data[0])
                    print(f"좌표 ({target_x}, {target_y})에서 방을 찾았습니다.")
                else:
                    print(f"❌ 좌표 ({target_x}, {target_y})에 방이 없습니다.")
                    return 1

            except ValueError:
                print("❌ 좌표 형식이 올바르지 않습니다. 예: 5,7")
                return 1
        else:
            # ID로 검색
            target_room = await room_repo.get_by_id(target)
            if target_room:
                target_x, target_y = target_room.x, target_room.y
                print(f"ID '{target}'로 방을 찾았습니다.")
            else:
                print(f"❌ ID '{target}'인 방을 찾을 수 없습니다.")
                return 1

        if not target_room:
            print("❌ 삭제할 방을 찾을 수 없습니다.")
            return 1

        print(f"삭제할 방: {target_room.get_localized_description('ko')}")
        print(f"좌표: ({target_x}, {target_y})")

        # 확인 요청
        confirm = input("\n정말로 이 방을 삭제하시겠습니까? (yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            print("삭제가 취소되었습니다.")
            return 0

        print(f"\n=== 방 삭제 진행 ===")

        # 1. 주변 방들 찾기 및 출구 정리
        print("1. 주변 방들의 출구 정리 중...")
        print("   (좌표 기반 시스템이므로 자동으로 처리됩니다)")

        # 2. 방에 있는 플레이어들 이동
        print("\n2. 방에 있는 플레이어들 확인 중...")
        cursor = await db_manager.execute(
            "SELECT id, username FROM players WHERE last_room_id = ?",
            (target_room.id,)
        )
        players_in_room = await cursor.fetchall()

        if players_in_room:
            print(f"  방에 {len(players_in_room)}명의 플레이어가 있습니다:")

            # 안전한 대피 장소 찾기 (0,0 좌표의 마을 광장)
            cursor = await db_manager.execute(
                "SELECT id FROM rooms WHERE x = 0 AND y = 0"
            )
            safe_room_data = await cursor.fetchone()

            if safe_room_data:
                safe_room_id = safe_room_data[0]
                for player_id, username in players_in_room:
                    await db_manager.execute(
                        "UPDATE players SET last_room_id = ?, last_room_x = 0, last_room_y = 0 WHERE id = ?",
                        (safe_room_id, player_id)
                    )
                    print(f"    - {username} -> 마을 광장으로 이동")
            else:
                print("  ❌ 안전한 대피 장소를 찾을 수 없습니다!")
                return 1
        else:
            print("  방에 플레이어가 없습니다.")

        # 3. 방에 있는 게임 오브젝트들 처리
        print("\n3. 방에 있는 게임 오브젝트들 확인 중...")
        cursor = await db_manager.execute(
            "SELECT COUNT(*) FROM game_objects WHERE location_id = ? AND location_type = 'room'",
            (target_room.id,)
        )
        object_count = await cursor.fetchone()

        if object_count and object_count[0] > 0:
            print(f"  방에 {object_count[0]}개의 게임 오브젝트가 있습니다.")

            # 오브젝트들을 마을 광장으로 이동
            cursor = await db_manager.execute(
                "SELECT id FROM rooms WHERE x = 0 AND y = 0"
            )
            safe_room_data = await cursor.fetchone()

            if safe_room_data:
                safe_room_id = safe_room_data[0]
                await db_manager.execute(
                    "UPDATE game_objects SET location_id = ? WHERE location_id = ? AND location_type = 'room'",
                    (safe_room_id, target_room.id)
                )
                print(f"    - 모든 오브젝트를 마을 광장으로 이동했습니다.")
        else:
            print("  방에 게임 오브젝트가 없습니다.")

        # 4. 방에 있는 몬스터들 처리
        print("\n4. 방에 있는 몬스터들 확인 중...")
        cursor = await db_manager.execute(
            "SELECT COUNT(*) FROM monsters WHERE x = ? AND y = ?",
            (target_x, target_y)
        )
        monster_count = await cursor.fetchone()

        if monster_count and monster_count[0] > 0:
            print(f"  방에 {monster_count[0]}마리의 몬스터가 있습니다.")
            print("    - 몬스터들을 제거합니다.")

            await db_manager.execute(
                "DELETE FROM monsters WHERE x = ? AND y = ?",
                (target_x, target_y)
            )
        else:
            print("  방에 몬스터가 없습니다.")

        # 5. NPC들 처리
        print("\n5. 방에 있는 NPC들 확인 중...")
        cursor = await db_manager.execute(
            "SELECT COUNT(*) FROM npcs WHERE x = ? AND y = ?",
            (target_x, target_y)
        )
        npc_count = await cursor.fetchone()

        if npc_count and npc_count[0] > 0:
            print(f"  방에 {npc_count[0]}명의 NPC가 있습니다.")

            # NPC들을 마을 광장으로 이동
            await db_manager.execute(
                "UPDATE npcs SET x = 0, y = 0 WHERE x = ? AND y = ?",
                (target_x, target_y)
            )
            print(f"    - 모든 NPC를 마을 광장으로 이동했습니다.")
        else:
            print("  방에 NPC가 없습니다.")

        # 6. 방 삭제
        print(f"\n6. 방 삭제 중...")
        await db_manager.execute("DELETE FROM rooms WHERE id = ?", (target_room.id,))

        print(f"\n✅ 방 삭제 완료!")
        print(f"삭제된 방: ({target_x}, {target_y}) - {target_room.get_localized_description('ko')}")
        print(f"주변 방들의 출구가 자동으로 정리되었습니다.")

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