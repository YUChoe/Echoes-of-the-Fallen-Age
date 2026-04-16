#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WorldView 기반 14개 NPC 초기화 스크립트

잿빛 항구(Greyhaven Port) 세계관에 기반하여 14개 NPC를
monsters 테이블에 멱등적으로 INSERT한다.
거래 NPC(Smuggler)의 경우 game_objects에 silver_coin + 판매 아이템도 INSERT한다.

실행: ./script_test.sh init_worldview_npcs
"""

import asyncio
import json
import sys
from datetime import datetime

from src.mud_engine.database import get_database_manager

# ============================================================
# 14개 NPC UUID 상수 (매 실행마다 동일한 UUID 사용)
# ============================================================
KNIGHT_LIEUTENANT_ID = "c7a1e2b3-4d5f-6a7b-8c9d-0e1f2a3b4c5d"
KNIGHT_RECRUITER_ID = "d8b2f3c4-5e6a-7b8c-9d0e-1f2a3b4c5d6e"
DRUNKEN_REFUGEE_ID = "e9c3a4d5-6f7b-8c9d-0e1f-2a3b4c5d6e7f"
WANDERING_BARD_ID = "f0d4b5e6-7a8c-9d0e-1f2a-3b4c5d6e7f8a"
PRIEST_ID = "a1e5c6f7-8b9d-0e1f-2a3b-4c5d6e7f8a9b"
CRYPT_GUARD_MONK_ID = "b2f6d7a8-9c0e-1f2a-3b4c-5d6e7f8a9b0c"
GATE_WARDEN_ID = "c3a7e8b9-0d1f-2a3b-4c5d-6e7f8a9b0c1d"
REFUGEE_ID = "d4b8f9c0-1e2a-3b4c-5d6e-7f8a9b0c1d2e"
DISGRUNTLED_FARMER_ID = "e5c9a0d1-2f3b-4c5d-6e7f-8a9b0c1d2e3f"
FORMER_MERCHANT_ID = "f6d0b1e2-3a4c-5d6e-7f8a-9b0c1d2e3f4a"
ROYAL_ADVISER_ID = "a7e1c2f3-4b5d-6e7f-8a9b-0c1d2e3f4a5b"
ROYAL_GUARD_ID = "b8f2d3a4-5c6e-7f8a-9b0c-1d2e3f4a5b6c"
FISHERMAN_ID = "c9a3e4b5-6d7f-8a9b-0c1d-2e3f4a5b6c7d"
SMUGGLER_ID = "d0b4f5c6-7e8a-9b0c-1d2e-3f4a5b6c7d8e"

# Smuggler 인벤토리 아이템 UUID
SMUGGLER_SILVER_ID = "e1c5a6d7-8f9b-0c1d-2e3f-4a5b6c7d8e9f"
SMUGGLER_ROPE_ID = "f2d6b7e8-9a0c-1d2e-3f4a-5b6c7d8e9f0a"
SMUGGLER_TORCH_ID = "a3e7c8f9-0b1d-2e3f-4a5b-6c7d8e9f0a1b"
SMUGGLER_HEALTH_POTION_ID = "b4f8d9a0-1c2e-3f4a-5b6c-7d8e9f0a1b2c"


# ============================================================
# 14개 NPC 데이터 정의
# ============================================================
NPC_LIST = [
    # --- 구역 1: 잿빛 기사단 (동쪽 마을) ---
    {
        "id": KNIGHT_LIEUTENANT_ID,
        "name_en": "Knight Lieutenant",
        "name_ko": "기사단 부관",
        "description_en": (
            "A stern officer of the Ash Knights, clad in battered plate armour. "
            "His eyes scan the surroundings with practised vigilance, ever watchful "
            "for the goblin threat lurking within the walls."
        ),
        "description_ko": (
            "낡은 판금 갑옷을 입은 잿빛 기사단의 엄격한 장교. "
            "숙련된 경계심으로 주변을 살피며, 성벽 안에 숨어든 "
            "고블린 위협을 항상 주시하고 있다."
        ),
        "stats": json.dumps({
            "strength": 16, "dexterity": 12, "constitution": 15,
            "intelligence": 10, "wisdom": 12, "charisma": 11, "current_hp": 45
        }),
        "faction_id": "ash_knights", "x": 3, "y": 0,
        "properties": json.dumps({}),
    },
    {
        "id": KNIGHT_RECRUITER_ID,
        "name_en": "Knight Recruiter",
        "name_ko": "기사단 모병관",
        "description_en": (
            "A persuasive knight in polished chainmail, stationed near the square "
            "to recruit able-bodied folk into the Ash Knights. His voice carries "
            "both promise and warning."
        ),
        "description_ko": (
            "광장 근처에서 잿빛 기사단에 입단할 인재를 모집하는 설득력 있는 기사. "
            "그의 목소리에는 약속과 경고가 함께 담겨 있다."
        ),
        "stats": json.dumps({
            "strength": 14, "dexterity": 11, "constitution": 13,
            "intelligence": 12, "wisdom": 11, "charisma": 15, "current_hp": 38
        }),
        "faction_id": "ash_knights", "x": -1, "y": 0,
        "properties": json.dumps({}),
    },
    # --- 구역 2: 술집/여관 ---
    {
        "id": DRUNKEN_REFUGEE_ID,
        "name_en": "Drunken Refugee",
        "name_ko": "술에 취한 난민",
        "description_en": (
            "A haggard man slumped over a table, clutching a half-empty tankard. "
            "He mutters about a great sorcerer and a blinding light that "
            "no one can properly explain."
        ),
        "description_ko": (
            "반쯤 빈 술잔을 움켜쥔 채 탁자에 엎드린 초췌한 남자. "
            "아무도 제대로 설명하지 못하는 대마법사와 "
            "눈부신 빛에 대해 중얼거리고 있다."
        ),
        "stats": json.dumps({
            "strength": 9, "dexterity": 8, "constitution": 10,
            "intelligence": 10, "wisdom": 9, "charisma": 8, "current_hp": 15
        }),
        "faction_id": "ash_knights", "x": -8, "y": -1,
        "properties": json.dumps({}),
    },
    {
        "id": WANDERING_BARD_ID,
        "name_en": "Wandering Bard",
        "name_ko": "떠돌이 음유시인",
        "description_en": (
            "A weathered minstrel with a cracked lute, nursing a drink in the corner. "
            "He speaks of the Golden Age and the empire's fall with a melancholy "
            "that suggests he has seen more than most."
        ),
        "description_ko": (
            "금이 간 류트를 든 풍파에 시달린 음유시인이 구석에서 술을 홀짝이고 있다. "
            "황금의 시대와 제국의 몰락을 이야기하는 그의 목소리에는 "
            "남들보다 많은 것을 보았음을 암시하는 우수가 서려 있다."
        ),
        "stats": json.dumps({
            "strength": 8, "dexterity": 13, "constitution": 9,
            "intelligence": 14, "wisdom": 13, "charisma": 16, "current_hp": 18
        }),
        "faction_id": "ash_knights", "x": -8, "y": -1,
        "properties": json.dumps({}),
    },
    # --- 구역 3: 교회 ---
    {
        "id": PRIEST_ID,
        "name_en": "Priest",
        "name_ko": "사제",
        "description_en": (
            "An elderly priest in faded vestments, tending a small shrine to "
            "the forgotten gods. His quiet demeanour belies a deep unease about "
            "what stirs beneath the church."
        ),
        "description_ko": (
            "바랜 제의를 입은 노사제가 잊혀진 신들을 위한 작은 제단을 돌보고 있다. "
            "조용한 태도 이면에는 교회 지하에서 꿈틀거리는 것에 대한 "
            "깊은 불안이 숨어 있다."
        ),
        "stats": json.dumps({
            "strength": 8, "dexterity": 9, "constitution": 10,
            "intelligence": 14, "wisdom": 17, "charisma": 13, "current_hp": 20
        }),
        "faction_id": "ash_knights", "x": 2, "y": 0,
        "properties": json.dumps({}),
    },
    {
        "id": CRYPT_GUARD_MONK_ID,
        "name_en": "Crypt Guard Monk",
        "name_ko": "교회 지하 입구 경비 수도사",
        "description_en": (
            "A broad-shouldered monk standing before a heavy iron door, "
            "barring passage to the depths below. He warns all who approach "
            "that the necropolis is no place for the living."
        ),
        "description_ko": (
            "무거운 철문 앞에 서서 지하로의 통행을 막고 있는 떡벌어진 어깨의 수도사. "
            "다가오는 모든 이에게 네크로폴리스는 "
            "산 자가 갈 곳이 아니라고 경고한다."
        ),
        "stats": json.dumps({
            "strength": 14, "dexterity": 10, "constitution": 14,
            "intelligence": 11, "wisdom": 15, "charisma": 10, "current_hp": 35
        }),
        "faction_id": "ash_knights", "x": 2, "y": -1,
        "properties": json.dumps({}),
    },
    # --- 구역 4: 성문 ---
    {
        "id": GATE_WARDEN_ID,
        "name_en": "Gate Warden",
        "name_ko": "성문 관리인",
        "description_en": (
            "A weary official in a worn tabard, overseeing the western gate. "
            "He enforces the relocation order with reluctant duty, knowing full well "
            "the resentment it breeds beyond the walls."
        ),
        "description_ko": (
            "낡은 겉옷을 입은 지친 관리인이 서쪽 성문을 감독하고 있다. "
            "이주 명령이 성벽 밖에서 얼마나 큰 원한을 사는지 잘 알면서도 "
            "마지못해 임무를 수행한다."
        ),
        "stats": json.dumps({
            "strength": 12, "dexterity": 10, "constitution": 12,
            "intelligence": 11, "wisdom": 13, "charisma": 10, "current_hp": 28
        }),
        "faction_id": "ash_knights", "x": -10, "y": 0,
        "properties": json.dumps({}),
    },
    {
        "id": REFUGEE_ID,
        "name_en": "Refugee",
        "name_ko": "난민",
        "description_en": (
            "A gaunt woman wrapped in a threadbare shawl, lingering near the gate. "
            "Her hollow eyes betray sleepless nights spent wondering whether "
            "her family yet lives."
        ),
        "description_ko": (
            "해진 숄을 두른 수척한 여인이 성문 근처를 서성이고 있다. "
            "가족이 아직 살아 있는지 모르는 채 뜬눈으로 밤을 지새운 "
            "흔적이 텅 빈 눈에 드러난다."
        ),
        "stats": json.dumps({
            "strength": 8, "dexterity": 9, "constitution": 9,
            "intelligence": 10, "wisdom": 11, "charisma": 9, "current_hp": 12
        }),
        "faction_id": "ash_knights", "x": -9, "y": 0,
        "properties": json.dumps({}),
    },
    # --- 구역 5: 성벽 밖 ---
    {
        "id": DISGRUNTLED_FARMER_ID,
        "name_en": "Disgruntled Farmer",
        "name_ko": "불만 가득한 농부",
        "description_en": (
            "A sun-burnt farmer with calloused hands, seething with barely "
            "contained fury. Forced from his land by the relocation order, "
            "he harbours nothing but contempt for those safe behind the walls."
        ),
        "description_ko": (
            "굳은살이 박인 손의 햇볕에 그을린 농부가 간신히 억누른 분노로 부글거리고 있다. "
            "이주 명령으로 땅에서 쫓겨난 그는 성벽 안에서 안전한 자들에 대한 "
            "경멸밖에 남지 않았다."
        ),
        "stats": json.dumps({
            "strength": 13, "dexterity": 10, "constitution": 13,
            "intelligence": 9, "wisdom": 10, "charisma": 8, "current_hp": 22
        }),
        "faction_id": "ash_knights", "x": -14, "y": 0,
        "properties": json.dumps({}),
    },
    {
        "id": FORMER_MERCHANT_ID,
        "name_en": "Former Merchant",
        "name_ko": "전직 상인",
        "description_en": (
            "A once-prosperous trader now dressed in patched clothing, "
            "his cart long since plundered. He speaks bitterly of how honest "
            "merchants were driven to banditry by the endless raids."
        ),
        "description_ko": (
            "한때 번성했으나 이제는 기운 옷을 입은 상인. "
            "수레는 오래전에 약탈당했다. 끝없는 습격에 정직한 상인들이 "
            "어떻게 도적으로 내몰렸는지 씁쓸하게 이야기한다."
        ),
        "stats": json.dumps({
            "strength": 9, "dexterity": 12, "constitution": 10,
            "intelligence": 13, "wisdom": 12, "charisma": 14, "current_hp": 18
        }),
        "faction_id": "ash_knights", "x": -18, "y": 0,
        "properties": json.dumps({}),
    },
    # --- 구역 6: 성(Castle) ---
    {
        "id": ROYAL_ADVISER_ID,
        "name_en": "Royal Adviser",
        "name_ko": "왕의 조언자",
        "description_en": (
            "A sharp-eyed counsellor in fine but travel-stained robes, "
            "poring over documents in the castle hall. He speaks in guarded tones "
            "of the missing heir and the succession crisis that looms."
        ),
        "description_ko": (
            "고급스럽지만 여행으로 얼룩진 로브를 입은 날카로운 눈의 조언자가 "
            "성 홀에서 문서를 살피고 있다. 행방불명된 왕위 계승자와 "
            "다가오는 계승 위기에 대해 조심스럽게 이야기한다."
        ),
        "stats": json.dumps({
            "strength": 8, "dexterity": 10, "constitution": 9,
            "intelligence": 17, "wisdom": 16, "charisma": 15, "current_hp": 20
        }),
        "faction_id": "ash_knights", "x": 12, "y": -2,
        "properties": json.dumps({}),
    },
    {
        "id": ROYAL_GUARD_ID,
        "name_en": "Royal Guard",
        "name_ko": "왕실 경비병",
        "description_en": (
            "An imposing guard in gleaming half-plate, standing at rigid attention "
            "before the castle entrance. He permits no one to pass without "
            "proper authority."
        ),
        "description_ko": (
            "빛나는 반판금 갑옷을 입은 위풍당당한 경비병이 성 입구 앞에서 "
            "꼿꼿이 서 있다. 적절한 권한 없이는 "
            "누구도 통과시키지 않는다."
        ),
        "stats": json.dumps({
            "strength": 16, "dexterity": 12, "constitution": 16,
            "intelligence": 10, "wisdom": 12, "charisma": 11, "current_hp": 48
        }),
        "faction_id": "ash_knights", "x": 12, "y": -1,
        "properties": json.dumps({}),
    },
    # --- 구역 7: 항구 ---
    {
        "id": FISHERMAN_ID,
        "name_en": "Fisherman",
        "name_ko": "어부",
        "description_en": (
            "A weathered old salt mending nets by the cliff edge, "
            "his face carved by years of sea wind. He knows every rock "
            "along the northern cliffs and the ruined jetty to the south."
        ),
        "description_ko": (
            "절벽 가장자리에서 그물을 손질하는 풍파에 시달린 늙은 어부. "
            "오랜 세월 바닷바람에 깎인 얼굴의 그는 북쪽 절벽의 모든 바위와 "
            "남쪽의 폐허가 된 잔교를 꿰뚫고 있다."
        ),
        "stats": json.dumps({
            "strength": 11, "dexterity": 12, "constitution": 13,
            "intelligence": 9, "wisdom": 14, "charisma": 10, "current_hp": 22
        }),
        "faction_id": "ash_knights", "x": 0, "y": 8,
        "properties": json.dumps({}),
    },
    {
        "id": SMUGGLER_ID,
        "name_en": "Smuggler",
        "name_ko": "밀수업자",
        "description_en": (
            "A wiry figure in a salt-stained cloak, lurking in the shadows "
            "near the harbour. He deals in goods that most folk cannot easily "
            "come by — for the right price, of course."
        ),
        "description_ko": (
            "소금기 묻은 망토를 두른 마른 체격의 인물이 항구 근처 그늘에 숨어 있다. "
            "대부분의 사람들이 쉽게 구할 수 없는 물건을 거래한다 "
            "— 물론, 적절한 대가를 치른다면."
        ),
        "stats": json.dumps({
            "strength": 10, "dexterity": 15, "constitution": 11,
            "intelligence": 13, "wisdom": 12, "charisma": 14, "current_hp": 25
        }),
        "faction_id": "ash_knights", "x": 0, "y": 7,
        "properties": json.dumps({
            "exchange_config": {
                "initial_silver": 300,
                "buy_margin": 0.4
            }
        }),
    },
]

# Smuggler 판매 아이템 정의
SMUGGLER_ITEMS = [
    {
        "id": SMUGGLER_ROPE_ID,
        "name_en": "Rope",
        "name_ko": "밧줄",
        "description_en": "A sturdy length of hemp rope, useful for climbing or binding.",
        "description_ko": "튼튼한 삼베 밧줄. 등반이나 묶는 데 유용하다.",
        "properties": json.dumps({
            "template_id": "rope", "is_template": False,
            "category": "misc", "base_value": 15
        }),
        "weight": 1.5, "max_stack": 5,
    },
    {
        "id": SMUGGLER_TORCH_ID,
        "name_en": "Torch",
        "name_ko": "횃불",
        "description_en": "A pitch-soaked torch that burns for roughly an hour.",
        "description_ko": "송진을 먹인 횃불. 대략 한 시간 정도 탄다.",
        "properties": json.dumps({
            "template_id": "torch", "is_template": False,
            "category": "misc", "base_value": 5
        }),
        "weight": 0.5, "max_stack": 10,
    },
    {
        "id": SMUGGLER_HEALTH_POTION_ID,
        "name_en": "Health Potion",
        "name_ko": "체력 물약",
        "description_en": "A small vial of reddish liquid that restores a measure of vitality.",
        "description_ko": "활력을 어느 정도 회복시켜 주는 붉은빛 액체가 든 작은 병.",
        "properties": json.dumps({
            "template_id": "health_potion", "is_template": False,
            "category": "consumable", "base_value": 25
        }),
        "weight": 0.3, "max_stack": 20,
    },
]


# ============================================================
# 공통 NPC 속성 (비전투 NPC)
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


async def insert_npc(db_manager, npc: dict) -> bool:
    """NPC를 monsters 테이블에 멱등적으로 INSERT한다."""
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
            return True

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
        return True

    except Exception as e:
        print(f"  ERROR: {name_ko} ({npc_id}) — {e}")
        return False


async def insert_smuggler_items(db_manager) -> None:
    """Smuggler의 silver_coin 스택과 판매 아이템을 game_objects에 INSERT한다."""
    print("\n--- Smuggler 거래 아이템 INSERT ---")

    # 1) silver_coin 스택
    try:
        cursor = await db_manager.execute(
            "SELECT id FROM game_objects WHERE id = ?", (SMUGGLER_SILVER_ID,)
        )
        existing = await cursor.fetchone()
        if existing:
            print(f"  SKIP: 은화 스택 ({SMUGGLER_SILVER_ID}) — 이미 존재")
        else:
            await db_manager.execute(
                """INSERT INTO game_objects (
                    id, name_en, name_ko, description_en, description_ko,
                    location_type, location_id, properties, weight, max_stack,
                    equipment_slot, is_equipped
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    SMUGGLER_SILVER_ID,
                    "Silver Coin", "은화",
                    "A standard silver coin used for trade.",
                    "거래에 사용되는 표준 은화입니다.",
                    "inventory", SMUGGLER_ID,
                    json.dumps({
                        "template_id": "silver_coin",
                        "is_template": False,
                        "category": "currency",
                        "base_value": 1,
                        "quantity": 300,
                    }),
                    0.003, 9999, None, False,
                ),
            )
            await db_manager.commit()
            print(f"  INSERT: 은화 스택 (quantity=300)")
    except Exception as e:
        print(f"  ERROR: 은화 스택 — {e}")

    # 2) 판매 아이템
    for item in SMUGGLER_ITEMS:
        try:
            cursor = await db_manager.execute(
                "SELECT id FROM game_objects WHERE id = ?", (item["id"],)
            )
            existing = await cursor.fetchone()
            if existing:
                print(f"  SKIP: {item['name_ko']} ({item['id']}) — 이미 존재")
                continue

            await db_manager.execute(
                """INSERT INTO game_objects (
                    id, name_en, name_ko, description_en, description_ko,
                    location_type, location_id, properties, weight, max_stack,
                    equipment_slot, is_equipped
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item["id"],
                    item["name_en"], item["name_ko"],
                    item["description_en"], item["description_ko"],
                    "inventory", SMUGGLER_ID,
                    item["properties"],
                    item["weight"], item["max_stack"],
                    None, False,
                ),
            )
            await db_manager.commit()
            print(f"  INSERT: {item['name_ko']} ({item['id']})")
        except Exception as e:
            print(f"  ERROR: {item['name_ko']} — {e}")


async def main():
    """메인 함수"""
    print("=== WorldView NPC 초기화 스크립트 ===\n")

    db_manager = None
    try:
        db_manager = await get_database_manager()
    except Exception as e:
        print(f"❌ DB 연결 실패: {e}")
        return 1

    try:
        # 14개 NPC INSERT
        print("--- monsters 테이블 INSERT ---")
        success_count = 0
        for npc in NPC_LIST:
            if await insert_npc(db_manager, npc):
                success_count += 1

        print(f"\n결과: {success_count}/{len(NPC_LIST)} NPC 처리 완료")

        # Smuggler 거래 아이템 INSERT
        await insert_smuggler_items(db_manager)

        print("\n✅ 초기화 완료")
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
