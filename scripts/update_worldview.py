#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
세계관 업데이트 스크립트

수정된 WorldView.md에 맞춰 기존 NPC를 UPDATE하고,
신규 NPC/방을 INSERT한다.

- 기존 NPC 2건 UPDATE (Crypt Guard Monk, Brother Marcus)
- 신규 NPC 3건 INSERT (마을 술집 주인, 자경단원, 쓰레기장 떠돌이)
- 신규 방 1건 INSERT (돌 제단)

멱등성 보장: 2회 연속 실행 시 동일한 DB 상태 유지.

실행: ./script_test.sh update_worldview
"""

import asyncio
import json
import sys

from src.mud_engine.database import get_database_manager

# ============================================================
# 기존 NPC UUID 상수
# ============================================================
CRYPT_GUARD_MONK_ID = "b2f6d7a8-9c0e-1f2a-3b4c-5d6e7f8a9b0c"
BROTHER_MARCUS_ID = "church_monk"

# ============================================================
# 신규 NPC UUID 상수
# ============================================================
TAVERN_KEEPER_ID = "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d"
VILLAGE_MILITIA_ID = "2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e"
JUNKYARD_DRIFTER_ID = "3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f"

# ============================================================
# 신규 방 UUID 상수
# ============================================================
STONE_ALTAR_ROOM_ID = "4d5e6f7a-8b9c-0d1e-2f3a-4b5c6d7e8f9a"


# ============================================================
# 기존 NPC UPDATE 데이터
# ============================================================
NPC_UPDATES = [
    {
        "id": CRYPT_GUARD_MONK_ID,
        "label": "Necropolis Monk (Crypt Guard Monk)",
        "fields": {
            "name_en": "Necropolis Monk",
            "name_ko": "네크로폴리스 수도승",
            "description_en": (
                "A gaunt monk in a threadbare robe stands motionless before "
                "the entrance to the necropolis. He does not speak; his hollow "
                "eyes and slow, deliberate gestures are the only guidance he "
                "offers to those who have just risen from death."
            ),
            "description_ko": (
                "해진 수도복을 입은 수척한 수도승이 네크로폴리스 입구 앞에 "
                "미동도 없이 서 있다. 그는 말을 하지 않는다. 텅 빈 눈과 "
                "느리고 의도적인 제스처만이 죽음에서 갓 일어난 자들에게 "
                "그가 제공하는 유일한 안내이다."
            ),
        },
    },
    {
        "id": BROTHER_MARCUS_ID,
        "label": "Brother Marcus (예배당 수도승)",
        "fields": {
            "description_en": (
                "A quiet monk tending the small chapel of Alva within the "
                "fortress walls. He chose a life apart from the everyday world "
                "to study the sun god in solitude. Before the remnants of the "
                "army arrived, he shared this space with only two homeless folk."
            ),
            "description_ko": (
                "요새 성벽 안의 작은 알바 예배당을 돌보는 조용한 수도승. "
                "일상과 떨어져 홀로 태양신을 공부하는 삶을 택했다. "
                "패잔병들이 들어오기 전에는 두어 명의 노숙자와 함께 "
                "이 공간을 나누어 쓰고 있었다."
            ),
        },
    },
]


# ============================================================
# 신규 NPC INSERT 데이터
# ============================================================
COMMON_NPC_FIELDS = {
    "monster_type": "neutral",
    "behavior": "stationary",
    "drop_items": "[]",
    "respawn_time": 0,
    "is_alive": 1,
    "aggro_range": 0,
    "roaming_range": 0,
}

NEW_NPCS = [
    {
        "id": TAVERN_KEEPER_ID,
        "name_en": "Village Tavern Keeper",
        "name_ko": "마을 술집 주인",
        "description_en": (
            "A stout woman with flour-dusted sleeves, wiping down the bar "
            "with a rag that has seen better days. She speaks bluntly of the "
            "relocation order and makes no effort to hide her contempt for "
            "those safe behind the castle walls."
        ),
        "description_ko": (
            "밀가루가 묻은 소매의 건장한 여인이 낡은 걸레로 술집 바를 "
            "닦고 있다. 이주 명령에 대해 거침없이 말하며, 성벽 안에서 "
            "안전한 자들에 대한 경멸을 숨기려 하지 않는다."
        ),
        "stats": json.dumps({
            "strength": 11, "dexterity": 10, "constitution": 12,
            "intelligence": 11, "wisdom": 12, "charisma": 13,
            "current_hp": 20,
        }),
        "faction_id": "ash_knights",
        "x": -16, "y": 0,
        "properties": json.dumps({}),
    },
    {
        "id": VILLAGE_MILITIA_ID,
        "name_en": "Village Militia",
        "name_ko": "자경단원",
        "description_en": (
            "A wiry man in mismatched leather armour, leaning on a battered "
            "spear. He keeps a watchful eye on the road, ever wary of the "
            "creatures that prowl beyond the village. The relocation order "
            "has only deepened his resentment towards the castle."
        ),
        "description_ko": (
            "짝이 맞지 않는 가죽 갑옷을 입은 마른 남자가 낡은 창에 "
            "기대어 서 있다. 마을 너머를 배회하는 괴물들을 경계하며 "
            "도로를 주시하고 있다. 이주 명령은 성에 대한 그의 반감을 "
            "더욱 깊게 만들었을 뿐이다."
        ),
        "stats": json.dumps({
            "strength": 13, "dexterity": 12, "constitution": 12,
            "intelligence": 9, "wisdom": 11, "charisma": 9,
            "current_hp": 25,
        }),
        "faction_id": "ash_knights",
        "x": -16, "y": 0,
        "properties": json.dumps({}),
    },
    {
        "id": JUNKYARD_DRIFTER_ID,
        "name_en": "Junkyard Drifter",
        "name_ko": "쓰레기장 떠돌이",
        "description_en": (
            "A ragged figure crouched amongst heaps of discarded furniture "
            "and refuse, picking through the rubbish for anything of use. "
            "He mutters about animals that come sniffing for scraps and a "
            "narrow gap between the rocks on the northern cliff."
        ),
        "description_ko": (
            "버려진 가구와 쓰레기 더미 사이에 쪼그리고 앉은 누더기 차림의 "
            "인물이 쓸 만한 것을 찾아 쓰레기를 뒤지고 있다. 음식 찌꺼기를 "
            "찾아오는 동물들과 북쪽 절벽 바위 사이의 좁은 틈에 대해 "
            "중얼거린다."
        ),
        "stats": json.dumps({
            "strength": 9, "dexterity": 11, "constitution": 10,
            "intelligence": 10, "wisdom": 10, "charisma": 7,
            "current_hp": 15,
        }),
        "faction_id": "ash_knights",
        "x": -12, "y": 1,
        "properties": json.dumps({}),
    },
]


# ============================================================
# 신규 방 INSERT 데이터
# ============================================================
NEW_ROOMS = [
    {
        "id": STONE_ALTAR_ROOM_ID,
        "x": -20,
        "y": 0,
        "description_en": (
            "A flat expanse of dry earth gives way to a carefully laid stone "
            "platform, roughly thirty centimetres thick, its slabs fitted "
            "together with ancient precision. At its centre stands a small "
            "stone table — an altar where offerings are placed for Alva, "
            "the sun god."
        ),
        "description_ko": (
            "마른 땅 위에 약 30센티미터 두께로 정밀하게 짜 맞춰진 돌바닥이 "
            "펼쳐져 있다. 그 한가운데에 작은 돌 상이 놓여 있다 — 태양신 "
            "알바에게 재물을 바치는 제단이다."
        ),
        "blocked_exits": "[]",
    },
]


# ============================================================
# UPDATE 함수
# ============================================================
async def update_existing_npcs(db_manager) -> int:
    """기존 NPC를 UPDATE한다. 성공 건수를 반환."""
    print("--- 기존 NPC UPDATE ---")
    success_count = 0

    for npc in NPC_UPDATES:
        npc_id = npc["id"]
        label = npc["label"]
        fields = npc["fields"]

        try:
            # SET 절 구성
            set_clauses = ", ".join(f"{k} = ?" for k in fields)
            values = list(fields.values()) + [npc_id]

            await db_manager.execute(
                f"UPDATE monsters SET {set_clauses} WHERE id = ?",
                tuple(values),
            )
            await db_manager.commit()
            print(f"  UPDATE: {label} ({npc_id})")
            success_count += 1

        except Exception as e:
            print(f"  ERROR: {label} ({npc_id}) — {e}")

    return success_count


# ============================================================
# INSERT 함수 (NPC)
# ============================================================
async def insert_new_npcs(db_manager) -> int:
    """신규 NPC를 멱등적으로 INSERT한다. 성공 건수를 반환."""
    print("\n--- 신규 NPC INSERT ---")
    success_count = 0

    for npc in NEW_NPCS:
        npc_id = npc["id"]
        name_ko = npc["name_ko"]

        try:
            # 존재 여부 확인
            cursor = await db_manager.execute(
                "SELECT id FROM monsters WHERE id = ?", (npc_id,)
            )
            existing = await cursor.fetchone()
            if existing:
                print(f"  SKIP: {name_ko} ({npc_id}) — 이미 존재")
                success_count += 1
                continue

            # INSERT
            await db_manager.execute(
                """INSERT INTO monsters (
                    id, name_en, name_ko, description_en, description_ko,
                    monster_type, behavior, stats, drop_items,
                    respawn_time, is_alive, aggro_range, roaming_range,
                    properties, faction_id, x, y
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    npc_id,
                    npc["name_en"], npc["name_ko"],
                    npc["description_en"], npc["description_ko"],
                    COMMON_NPC_FIELDS["monster_type"],
                    COMMON_NPC_FIELDS["behavior"],
                    npc["stats"],
                    COMMON_NPC_FIELDS["drop_items"],
                    COMMON_NPC_FIELDS["respawn_time"],
                    COMMON_NPC_FIELDS["is_alive"],
                    COMMON_NPC_FIELDS["aggro_range"],
                    COMMON_NPC_FIELDS["roaming_range"],
                    npc["properties"],
                    npc["faction_id"],
                    npc["x"], npc["y"],
                ),
            )
            await db_manager.commit()
            print(f"  INSERT: {name_ko} ({npc_id}) @ ({npc['x']}, {npc['y']})")
            success_count += 1

        except Exception as e:
            print(f"  ERROR: {name_ko} ({npc_id}) — {e}")

    return success_count


# ============================================================
# INSERT 함수 (방)
# ============================================================
async def insert_new_rooms(db_manager) -> int:
    """신규 방을 멱등적으로 INSERT한다. 성공 건수를 반환."""
    print("\n--- 신규 방 INSERT ---")
    success_count = 0

    for room in NEW_ROOMS:
        room_id = room["id"]
        x, y = room["x"], room["y"]

        try:
            # 동일 좌표 존재 여부 확인
            cursor = await db_manager.execute(
                "SELECT id FROM rooms WHERE x = ? AND y = ?", (x, y)
            )
            existing = await cursor.fetchone()
            if existing:
                print(f"  SKIP: 돌 제단 ({room_id}) @ ({x}, {y}) — "
                      f"해당 좌표에 방 이미 존재 ({existing[0]})")
                success_count += 1
                continue

            # INSERT
            await db_manager.execute(
                """INSERT INTO rooms (
                    id, x, y, description_en, description_ko, blocked_exits
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    room_id, x, y,
                    room["description_en"], room["description_ko"],
                    room["blocked_exits"],
                ),
            )
            await db_manager.commit()
            print(f"  INSERT: 돌 제단 ({room_id}) @ ({x}, {y})")
            success_count += 1

        except Exception as e:
            print(f"  ERROR: 돌 제단 ({room_id}) — {e}")

    return success_count


# ============================================================
# 메인 함수
# ============================================================
async def main():
    """메인 함수"""
    print("=== 세계관 업데이트 스크립트 ===\n")

    db_manager = None
    try:
        db_manager = await get_database_manager()
    except Exception as e:
        print(f"❌ DB 연결 실패: {e}")
        return 1

    try:
        # Phase 1: 기존 NPC UPDATE
        update_count = await update_existing_npcs(db_manager)
        print(f"\n결과: {update_count}/{len(NPC_UPDATES)} NPC UPDATE 처리 완료")

        # Phase 2: 신규 NPC INSERT
        insert_npc_count = await insert_new_npcs(db_manager)
        print(f"\n결과: {insert_npc_count}/{len(NEW_NPCS)} NPC INSERT 처리 완료")

        # Phase 3: 신규 방 INSERT
        insert_room_count = await insert_new_rooms(db_manager)
        print(f"\n결과: {insert_room_count}/{len(NEW_ROOMS)} 방 INSERT 처리 완료")

        print("\n✅ 세계관 업데이트 완료")
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


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
