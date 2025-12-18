#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수도사를 상인으로 변경하는 스크립트"""

import asyncio
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mud_engine.database.connection import DatabaseManager


async def update_monk_to_merchant():
    """수도사를 상인으로 변경"""
    print("=== 수도사를 상인으로 변경 ===\n")

    db_manager = None
    try:
        db_manager = DatabaseManager()
        await db_manager.initialize()

        # 수도사 몬스터 정보 조회
        cursor = await db_manager.execute(
            "SELECT * FROM monsters WHERE id = ?", ("church_monk",)
        )
        monk_data = await cursor.fetchone()

        if not monk_data:
            print("❌ 수도사 몬스터를 찾을 수 없습니다.")
            return 1

        print(f"✅ 수도사 발견: {monk_data[2]} ({monk_data[1]})")

        # 상인 속성 설정
        merchant_properties = {
            "merchant_type": "equipment_and_key",
            "shop_name": {
                "en": "Brother Marcus's Sacred Shop",
                "ko": "마르쿠스 수도사의 성물 상점"
            },
            "greeting": {
                "en": [
                    "Welcome to my humble shop, young adventurer.",
                    "I offer basic equipment for those starting their journey.",
                    "I also have a special key to the castle for those who prove their worth."
                ],
                "ko": [
                    "제 소박한 상점에 오신 것을 환영합니다, 젊은 모험가여.",
                    "여행을 시작하는 분들을 위한 기본 장비를 제공합니다.",
                    "또한 자신의 가치를 증명한 분들을 위한 특별한 성 열쇠도 있습니다."
                ]
            },
            "shop_items": [
                {
                    "item_id": "tutorial_club",
                    "price": 0,
                    "currency": "gold",
                    "stock": -1,  # 무제한
                    "description": {
                        "en": "A simple wooden club for beginners",
                        "ko": "초보자를 위한 간단한 나무 곤봉"
                    }
                },
                {
                    "item_id": "tutorial_linen_shirt",
                    "price": 0,
                    "currency": "gold",
                    "stock": -1,
                    "description": {
                        "en": "Basic linen shirt for protection",
                        "ko": "보호를 위한 기본 리넨 상의"
                    }
                },
                {
                    "item_id": "tutorial_linen_trousers",
                    "price": 0,
                    "currency": "gold",
                    "stock": -1,
                    "description": {
                        "en": "Simple linen trousers for comfort",
                        "ko": "편안함을 위한 간단한 리넨 하의"
                    }
                },
                {
                    "item_id": "castle_key",
                    "price": 10,
                    "currency": "essence_of_life",
                    "stock": -1,
                    "description": {
                        "en": "A mystical key that opens the path to the castle",
                        "ko": "성으로 가는 길을 여는 신비한 열쇠"
                    }
                }
            ],
            "dialogue": {
                "en": [
                    "Browse my wares, adventurer.",
                    "The basic equipment is free for all who need it.",
                    "The castle key... that requires proof of your dedication."
                ],
                "ko": [
                    "제 상품들을 둘러보세요, 모험가님.",
                    "기본 장비는 필요한 모든 분들께 무료로 드립니다.",
                    "성 열쇠는... 당신의 헌신에 대한 증명이 필요합니다."
                ]
            }
        }

        # 몬스터 속성 업데이트
        properties_json = json.dumps(merchant_properties, ensure_ascii=False, indent=2)

        await db_manager.execute("""
            UPDATE monsters
            SET properties = ?
            WHERE id = ?
        """, (properties_json, "church_monk"))

        print("✅ 수도사가 상인으로 변경되었습니다.")
        print("\n상점 정보:")
        print("- 기본 장비 (곤봉, 리넨 상의, 리넨 하의): 0 골드")
        print("- 성 열쇠: 10 생명의 정수")
        print("- 성 열쇠 구매 시 튜토리얼 퀘스트 완료")

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
    exit_code = asyncio.run(update_monk_to_merchant())
    sys.exit(exit_code)