#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
몬스터 스폰 스크립트

템플릿 파일을 기반으로 지정된 좌표에 몬스터를 생성합니다.

사용법:
    # 특정 좌표에 몬스터 스폰
    python scripts/spawn_monster.py template_forest_goblin 5 7
    
    # 여러 몬스터 스폰
    python scripts/spawn_monster.py template_small_rat 0 0 --count 3
    
    # 모든 몬스터 템플릿 목록 보기
    python scripts/spawn_monster.py --list
"""

import asyncio
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from uuid import uuid4
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mud_engine.database.connection import DatabaseManager
from src.mud_engine.game.repositories import MonsterRepository, RoomRepository
from src.mud_engine.game.monster import Monster, MonsterType, MonsterBehavior, MonsterStats, DropItem
from src.mud_engine.game.models import Room


class MonsterSpawner:
    """몬스터 스폰을 담당하는 클래스"""
    
    def __init__(self, monster_repo: MonsterRepository, room_repo: RoomRepository):
        self.monster_repo = monster_repo
        self.room_repo = room_repo
        self.templates_dir = Path("configs/monsters")
    
    async def load_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """템플릿 파일을 로드합니다."""
        template_file = self.templates_dir / f"{template_id}.json"
        
        if not template_file.exists():
            print(f"❌ 템플릿 파일을 찾을 수 없습니다: {template_file}")
            return None
        
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                template = json.load(f)
            print(f"✅ 템플릿 로드 완료: {template_id}")
            return template
        except Exception as e:
            print(f"❌ 템플릿 로드 실패 ({template_file}): {e}")
            return None
    
    async def find_room_by_coordinates(self, x: int, y: int) -> Optional[Room]:
        """좌표로 방을 찾습니다."""
        all_rooms = await self.room_repo.get_all()
        
        for room in all_rooms:
            if room.x == x and room.y == y:
                return room
        
        return None
    
    def create_monster_from_template(self, template: Dict[str, Any], monster_id: str, room_id: str) -> Monster:
        """템플릿에서 몬스터 인스턴스를 생성합니다."""
        # 몬스터 타입 변환
        monster_type_str = template.get('monster_type', 'PASSIVE')
        monster_type = MonsterType[monster_type_str.upper()]

        # 행동 타입 변환
        behavior_str = template.get('behavior', 'STATIONARY')
        behavior = MonsterBehavior[behavior_str.upper()]

        # 스탯 생성
        stats_data = template.get('stats', {})
        stats = MonsterStats(
            strength=stats_data.get('strength', 10),
            dexterity=stats_data.get('dexterity', 10),
            constitution=stats_data.get('constitution', 10),
            intelligence=stats_data.get('intelligence', 10),
            wisdom=stats_data.get('wisdom', 10),
            charisma=stats_data.get('charisma', 10),
            level=stats_data.get('level', 1),
            current_hp=stats_data.get('current_hp', stats_data.get('constitution', 10) * 5)
        )

        # 드롭 아이템 생성
        drop_items = []
        for item_data in template.get('drop_items', []):
            drop_items.append(DropItem(
                item_id=item_data['item_id'],
                drop_chance=item_data['drop_chance']
            ))

        # 몬스터 생성
        monster = Monster(
            id=monster_id,
            name=template.get('name', {}),
            description=template.get('description', {}),
            monster_type=monster_type,
            behavior=behavior,
            stats=stats,
            gold_reward=template.get('gold_reward', 0),
            drop_items=drop_items,
            spawn_room_id=room_id,
            current_room_id=room_id,
            respawn_time=template.get('respawn_time', 300),
            aggro_range=template.get('aggro_range', 0),
            roaming_range=template.get('roaming_range', 0),
            faction_id=template.get('faction_id'),
            properties={'template_id': template.get('template_id'), 'is_template': False},
            is_alive=True,
            created_at=datetime.now()
        )

        return monster
    
    async def spawn_monsters(self, template_id: str, x: int, y: int, count: int = 1) -> List[Monster]:
        """지정된 좌표에 몬스터들을 스폰합니다."""
        # 템플릿 로드
        template = await self.load_template(template_id)
        if not template:
            return []
        
        # 방 찾기
        room = await self.find_room_by_coordinates(x, y)
        if not room:
            print(f"❌ 좌표 ({x}, {y})에 해당하는 방을 찾을 수 없습니다.")
            return []
        
        print(f"📍 스폰 위치: {room.id} - 좌표 ({x}, {y})")
        print(f"🐉 스폰할 몬스터: {template.get('name', {}).get('ko', template.get('name', {}).get('en', template_id))}")
        print(f"🐉 스폰 개수: {count}마리")
        
        spawned_monsters = []
        
        for i in range(count):
            # 고유 ID 생성
            monster_id = str(uuid4())
            
            # 몬스터 생성
            monster = self.create_monster_from_template(template, monster_id, room.id)
            
            # 데이터베이스에 저장
            try:
                created_monster = await self.monster_repo.create(monster.to_dict())
                spawned_monsters.append(created_monster)
                
                monster_name = template.get('name', {}).get('ko', template.get('name', {}).get('en', template_id))
                print(f"  ✅ {monster_name} #{i+1} 생성됨: ID {monster_id[:8]}...")
                
            except Exception as e:
                print(f"  ❌ 몬스터 생성 실패 #{i+1}: {e}")
        
        return spawned_monsters
    
    async def list_templates(self) -> List[str]:
        """사용 가능한 템플릿 목록을 반환합니다."""
        if not self.templates_dir.exists():
            print(f"❌ 템플릿 디렉토리가 존재하지 않습니다: {self.templates_dir}")
            return []
        
        template_files = list(self.templates_dir.glob("*.json"))
        templates = []
        
        print("🐉 사용 가능한 몬스터 템플릿:")
        print("=" * 50)
        
        for template_file in sorted(template_files):
            template_id = template_file.stem
            
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template = json.load(f)
                
                name_ko = template.get('name', {}).get('ko', template_id)
                name_en = template.get('name', {}).get('en', template_id)
                monster_type = template.get('monster_type', 'UNKNOWN')
                level = template.get('stats', {}).get('level', 1)
                
                print(f"• {template_id}")
                print(f"  이름: {name_ko} ({name_en})")
                print(f"  타입: {monster_type}, 레벨: {level}")
                print()
                
                templates.append(template_id)
                
            except Exception as e:
                print(f"❌ 템플릿 로드 실패 ({template_file}): {e}")
        
        print(f"총 {len(templates)}개의 템플릿이 사용 가능합니다.")
        print()
        print("사용법: python scripts/spawn_monster.py <template_id> <x> <y> [--count N]")
        
        return templates


async def spawn_monsters_main(template_id: str, x: int, y: int, count: int = 1):
    """몬스터 스폰 메인 함수"""
    print("=" * 60)
    print(f"몬스터 스폰: {template_id} - 좌표 ({x}, {y})")
    print("=" * 60)
    
    # 데이터베이스 연결
    db_manager = DatabaseManager("data/mud_engine.db")
    await db_manager.initialize()
    
    try:
        # 리포지토리 생성
        monster_repo = MonsterRepository(db_manager)
        room_repo = RoomRepository(db_manager)
        
        # 스포너 생성
        spawner = MonsterSpawner(monster_repo, room_repo)
        
        # 몬스터 스폰
        spawned = await spawner.spawn_monsters(template_id, x, y, count)
        
        if spawned:
            print(f"\n✅ 총 {len(spawned)}마리의 몬스터가 생성되었습니다!")
            
            # 요약 정보
            print("\n" + "=" * 60)
            print("📊 스폰 요약")
            print("=" * 60)
            template = await spawner.load_template(template_id)
            if template:
                monster_name = template.get('name', {}).get('ko', template.get('name', {}).get('en', template_id))
                print(f"  - 몬스터: {monster_name}")
                print(f"  - 개수: {len(spawned)}마리")
                print(f"  - 위치: 좌표 ({x}, {y})")
                print(f"  - 타입: {template.get('monster_type', 'UNKNOWN')}")
                print(f"  - 행동: {template.get('behavior', 'STATIONARY')}")
                print(f"  - 레벨: {template.get('stats', {}).get('level', 1)}")
                print(f"  - 골드: {template.get('gold_reward', 0)} gold")
            print("=" * 60)
        else:
            print("\n❌ 몬스터 생성에 실패했습니다.")
        
    finally:
        await db_manager.close()


async def list_templates_main():
    """템플릿 목록 표시 메인 함수"""
    # 데이터베이스 연결
    db_manager = DatabaseManager("data/mud_engine.db")
    await db_manager.initialize()
    
    try:
        # 리포지토리 생성
        monster_repo = MonsterRepository(db_manager)
        room_repo = RoomRepository(db_manager)
        
        # 스포너 생성
        spawner = MonsterSpawner(monster_repo, room_repo)
        
        # 템플릿 목록 표시
        await spawner.list_templates()
        
    finally:
        await db_manager.close()


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='몬스터 스폰 스크립트')
    parser.add_argument('template_id', nargs='?', help='몬스터 템플릿 ID')
    parser.add_argument('x', nargs='?', type=int, help='X 좌표')
    parser.add_argument('y', nargs='?', type=int, help='Y 좌표')
    parser.add_argument('--count', type=int, default=1, help='생성할 몬스터 개수 (기본: 1)')
    parser.add_argument('--list', action='store_true', help='사용 가능한 템플릿 목록 표시')
    
    args = parser.parse_args()
    
    if args.list:
        asyncio.run(list_templates_main())
    elif args.template_id and args.x is not None and args.y is not None:
        asyncio.run(spawn_monsters_main(args.template_id, args.x, args.y, args.count))
    else:
        parser.print_help()
        print("\n예시:")
        print("  python scripts/spawn_monster.py template_forest_goblin 5 7")
        print("  python scripts/spawn_monster.py template_small_rat 0 0 --count 3")
        print("  python scripts/spawn_monster.py --list")
        sys.exit(1)


if __name__ == "__main__":
    main()