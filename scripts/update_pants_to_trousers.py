#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pants를 Trousers로 수정하는 스크립트"""

import asyncio
import sys
from src.mud_engine.database import get_database_manager


async def main():
    """Pants를 Trousers로 수정"""
    print("=== Pants를 Trousers로 수정 ===\n")

    db_manager = None
    try:
        db_manager = await get_database_manager()

        # 1. 현재 pants 관련 아이템 확인
        print("1. 현재 pants 관련 아이템 확인:")
        cursor = await db_manager.execute("""
            SELECT id, name_en, name_ko, object_type, location_type, location_id
            FROM game_objects
            WHERE name_en LIKE '%pants%' OR name_en LIKE '%Pants%'
            ORDER BY name_en
        """)
        pants_items = await cursor.fetchall()

        if not pants_items:
            print("  ❌ pants 관련 아이템을 찾을 수 없습니다.")
            return 1

        print(f"  📦 총 {len(pants_items)}개의 pants 아이템 발견:")
        for item in pants_items:
            item_id, name_en, name_ko, obj_type, loc_type, loc_id = item
            print(f"    • {name_en} ({name_ko}) - {obj_type} [{loc_type}] - ID: {item_id}")

        # 2. pants를 trousers로 업데이트
        print(f"\n2. pants를 trousers로 업데이트:")

        # Linen Pants -> Linen Trousers
        cursor = await db_manager.execute("""
            UPDATE game_objects
            SET name_en = 'Linen Trousers'
            WHERE name_en = 'Linen Pants'
        """)
        linen_updated = cursor.rowcount
        print(f"  ✅ Linen Pants → Linen Trousers: {linen_updated}개 업데이트")

        # 다른 pants 아이템들도 확인하고 업데이트
        for item in pants_items:
            item_id, name_en, name_ko, obj_type, loc_type, loc_id = item
            if "Pants" in name_en and name_en != "Linen Pants":  # 이미 위에서 처리됨
                new_name = name_en.replace("Pants", "Trousers")
                cursor = await db_manager.execute("""
                    UPDATE game_objects
                    SET name_en = ?
                    WHERE id = ?
                """, (new_name, item_id))
                print(f"  ✅ {name_en} → {new_name}: 업데이트 완료")

        # 3. 업데이트 결과 확인
        print(f"\n3. 업데이트 결과 확인:")
        cursor = await db_manager.execute("""
            SELECT id, name_en, name_ko, object_type, location_type, location_id
            FROM game_objects
            WHERE name_en LIKE '%trousers%' OR name_en LIKE '%Trousers%'
            ORDER BY name_en
        """)
        trousers_items = await cursor.fetchall()

        if trousers_items:
            print(f"  📦 총 {len(trousers_items)}개의 trousers 아이템:")
            for item in trousers_items:
                item_id, name_en, name_ko, obj_type, loc_type, loc_id = item
                print(f"    • {name_en} ({name_ko}) - {obj_type} [{loc_type}] - ID: {item_id}")
        else:
            print("  ❌ trousers 아이템을 찾을 수 없습니다.")

        # 4. 남은 pants 아이템 확인
        cursor = await db_manager.execute("""
            SELECT id, name_en, name_ko, object_type, location_type, location_id
            FROM game_objects
            WHERE name_en LIKE '%pants%' OR name_en LIKE '%Pants%'
            ORDER BY name_en
        """)
        remaining_pants = await cursor.fetchall()

        if remaining_pants:
            print(f"\n⚠️ 남은 pants 아이템 ({len(remaining_pants)}개):")
            for item in remaining_pants:
                item_id, name_en, name_ko, obj_type, loc_type, loc_id = item
                print(f"    • {name_en} ({name_ko}) - {obj_type} [{loc_type}] - ID: {item_id}")
        else:
            print(f"\n✅ 모든 pants 아이템이 trousers로 변경되었습니다.")

        print("\n✅ Pants → Trousers 업데이트 완료")
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