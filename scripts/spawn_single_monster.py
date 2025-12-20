#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
특정 x,y 좌표에 단일 몬스터를 생성하는 스크립트
사용법: python spawn_single_monster.py <template_id> <x> <y>
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from uuid import uuid4

from src.mud_engine.database import get_database_manager
from src.mud_engine.game.monster import Monster, MonsterType, MonsterBehavior, MonsterStats, DropItem
from src.mud_engine.game.repositories import MonsterRepository


def load_template(template_id: str, templates_dir: str = "configs/monsters") -> Optional[Dict[str, Any]]:
    """템플릿 파일을 로드합니다."""
    templates_path = Path(templates_dir)

    for template_file in templates_path.glob("*.json"):
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
                if template_data.get('template_id') == template_id:
                    return template_data
        except Exception as e:
            print(f"❌ 템플릿 파일 읽기 실패 ({template_file}): {e}")

    return None


def create_monster_from_template(template_id: str, x: int, y: int) -> Optional[Monster]:
    """템플릿에서 몬스터를 생성합니다."""
    template = load_template(template_id)
    if not template:
        print(f"❌ 템플릿을 찾을 수 없습니다: {template_id}")
        return None

    try:
        # 기본 정보
        monster_data = {
            'id': str(uuid4()),
            'name': template['name'],
            'description': template['description'],
            'x': x,
            'y': y
        }

        # 몬스터 타입 및 행동 패턴
        if 'monster_type' in template:
            monster_data['monster_type'] = MonsterType(template['monster_type'].lower())

        if 'behavior' in template:
            monster_data['behavior'] = MonsterBehavior(template['behavior'].lower())

        # 능력치
        if 'stats' in template:
            stats_data = template['stats']
            monster_data['stats'] = MonsterStats(**stats_data)

        # 보상
        if 'gold_reward' in template:
            monster_data['gold_reward'] = template['gold_reward']

        # 드롭 아이템
        if 'drop_items' in template:
            drop_items = []
            for item_data in template['drop_items']:
                drop_item = DropItem(
                    item_id=item_data['item_id'],
                    drop_chance=item_data['drop_chance'],
                    min_quantity=item_data.get('min_quantity', 1),
                    max_quantity=item_data.get('max_quantity', 1)
                )
                drop_items.append(drop_item)
            monster_data['drop_items'] = drop_items

        # 기타 설정
        for field in ['respawn_time', 'aggro_range', 'roaming_range']:
            if field in template:
                monster_data[field] = template[field]

        # 몬스터 생성
        monster = Monster(**monster_data)
        return monster

    except Exception as e:
        print(f"❌ 몬스터 생성 실패: {e}")
        return None


async def spawn_monster(template_id: str, x: int, y: int) -> bool:
    """특정 위치에 몬스터를 스폰합니다."""
    print(f"🎯 {template_id} 몬스터를 ({x}, {y}) 위치에 생성 중...")

    # 몬스터 생성
    monster = create_monster_from_template(template_id, x, y)
    if not monster:
        return False

    print(f"✅ 몬스터 생성됨: {monster.get_localized_name('ko')}")

    # 데이터베이스에 저장
    db_manager = None
    try:
        db_manager = await get_database_manager()
        monster_repo = MonsterRepository(db_manager)

        created_monster = await monster_repo.create(monster.to_dict())
        if created_monster:
            print(f"✅ 데이터베이스 저장 완료: ID {created_monster.id}")
            print(f"📍 위치: ({created_monster.x}, {created_monster.y})")
            print(f"🏷️ 이름: {created_monster.get_localized_name('ko')} ({created_monster.get_localized_name('en')})")
            return True
        else:
            print("❌ 데이터베이스 저장 실패")
            return False

    except Exception as e:
        print(f"❌ 스폰 실패: {e}")
        return False
    finally:
        if db_manager:
            try:
                await db_manager.close()
            except Exception:
                pass


def list_available_templates():
    """사용 가능한 템플릿 목록을 출력합니다."""
    templates_path = Path("configs/monsters")
    templates = []

    for template_file in templates_path.glob("*.json"):
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
                template_id = template_data.get('template_id')
                name_ko = template_data.get('name', {}).get('ko', 'Unknown')
                if template_id:
                    templates.append((template_id, name_ko))
        except Exception:
            continue

    if templates:
        print("📋 사용 가능한 템플릿:")
        for template_id, name_ko in templates:
            print(f"  - {template_id}: {name_ko}")
    else:
        print("❌ 사용 가능한 템플릿이 없습니다.")


async def main():
    """메인 함수"""
    print("=== 단일 몬스터 스폰 스크립트 ===\n")

    # 인자 확인
    if len(sys.argv) != 4:
        print("사용법: python spawn_single_monster.py <template_id> <x> <y>")
        print("예시: python spawn_single_monster.py template_forest_goblin 5 7\n")
        list_available_templates()
        return 1

    template_id = sys.argv[1]
    try:
        x = int(sys.argv[2])
        y = int(sys.argv[3])
    except ValueError:
        print("❌ x, y 좌표는 정수여야 합니다.")
        return 1

    # 몬스터 스폰
    success = await spawn_monster(template_id, x, y)

    if success:
        print("\n✅ 몬스터 스폰 완료!")
        return 0
    else:
        print("\n❌ 몬스터 스폰 실패!")
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)