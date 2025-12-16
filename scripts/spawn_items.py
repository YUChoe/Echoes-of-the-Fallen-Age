#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
아이템 스폰 스크립트

템플릿 파일을 기반으로 지정된 좌표에 아이템을 생성합니다.

사용법:
    # 특정 좌표에 아이템 스폰
    python scripts/spawn_items.py torch 5 7
    
    # 여러 아이템 스폰
    python scripts/spawn_items.py bread 0 0 --count 3
    
    # 모든 아이템 템플릿 목록 보기
    python scripts/spawn_items.py --list
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
from src.mud_engine.game.repositories import GameObjectRepository, RoomRepository
from src.mud_engine.game.models import GameObject, Room


class ItemSpawner:
    """아이템 스폰을 담당하는 클래스"""
    
    def __init__(self, object_repo: GameObjectRepository, room_repo: RoomRepository):
        self.object_repo = object_repo
        self.room_repo = room_repo
        self.templates_dir = Path("configs/items")
    
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
    
    def create_item_from_template(self, template: Dict[str, Any], item_id: str, room_id: str) -> GameObject:
        """템플릿에서 아이템 인스턴스를 생성합니다."""
        # 이름과 설명을 딕셔너리 형태로 변환
        name = {}
        if template.get('name_en'):
            name['en'] = template['name_en']
        if template.get('name_ko'):
            name['ko'] = template['name_ko']
        
        # 이름이 비어있으면 기본값 설정
        if not name:
            template_id = template.get('template_id', 'unknown')
            name = {'ko': template_id, 'en': template_id}
        
        description = {}
        if template.get('description_en'):
            description['en'] = template['description_en']
        if template.get('description_ko'):
            description['ko'] = template['description_ko']
        
        # 설명이 비어있으면 기본값 설정
        if not description:
            template_id = template.get('template_id', 'unknown')
            description = {'ko': f'{template_id} 아이템입니다.', 'en': f'This is {template_id} item.'}

        # 아이템 생성
        item = GameObject(
            id=item_id,
            name=name,
            description=description,
            object_type=template.get('object_type', 'item'),
            location_type="room",
            location_id=room_id,
            properties=template.get('properties', {}),
            weight=template.get('weight', 1.0),
            category=template.get('category', 'misc'),
            equipment_slot=template.get('equipment_slot'),
            is_equipped=False,
            created_at=datetime.now()
        )

        # 템플릿 ID를 속성에 추가
        item.properties['template_id'] = template.get('template_id')
        item.properties['is_template'] = False

        # 스택 가능 정보 추가
        if template.get('stackable', False):
            item.properties['stackable'] = True
            item.properties['max_stack'] = template.get('max_stack', 1)

        return item
    
    async def spawn_items(self, template_id: str, x: int, y: int, count: int = 1) -> List[GameObject]:
        """지정된 좌표에 아이템들을 스폰합니다."""
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
        print(f"📦 스폰할 아이템: {template.get('name_ko', template.get('name_en', template_id))}")
        print(f"📦 스폰 개수: {count}개")
        
        spawned_items = []
        
        for i in range(count):
            # 고유 ID 생성
            item_id = str(uuid4())
            
            # 아이템 생성
            item = self.create_item_from_template(template, item_id, room.id)
            
            # 데이터베이스에 저장
            try:
                created_item = await self.object_repo.create(item.to_dict())
                spawned_items.append(created_item)
                
                item_name = template.get('name_ko', template.get('name_en', template_id))
                print(f"  ✅ {item_name} #{i+1} 생성됨: ID {item_id[:8]}...")
                
            except Exception as e:
                print(f"  ❌ 아이템 생성 실패 #{i+1}: {e}")
        
        return spawned_items
    
    async def list_templates(self) -> List[str]:
        """사용 가능한 템플릿 목록을 반환합니다."""
        if not self.templates_dir.exists():
            print(f"❌ 템플릿 디렉토리가 존재하지 않습니다: {self.templates_dir}")
            return []
        
        template_files = list(self.templates_dir.glob("*.json"))
        templates = []
        
        print("📦 사용 가능한 아이템 템플릿:")
        print("=" * 50)
        
        for template_file in sorted(template_files):
            template_id = template_file.stem
            
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template = json.load(f)
                
                name_ko = template.get('name_ko', template_id)
                name_en = template.get('name_en', template_id)
                object_type = template.get('object_type', 'item')
                category = template.get('category', 'misc')
                
                print(f"• {template_id}")
                print(f"  이름: {name_ko} ({name_en})")
                print(f"  타입: {object_type}, 카테고리: {category}")
                print()
                
                templates.append(template_id)
                
            except Exception as e:
                print(f"❌ 템플릿 로드 실패 ({template_file}): {e}")
        
        print(f"총 {len(templates)}개의 템플릿이 사용 가능합니다.")
        print()
        print("사용법: python scripts/spawn_items.py <template_id> <x> <y> [--count N]")
        
        return templates


async def spawn_items_main(template_id: str, x: int, y: int, count: int = 1):
    """아이템 스폰 메인 함수"""
    print("=" * 60)
    print(f"아이템 스폰: {template_id} - 좌표 ({x}, {y})")
    print("=" * 60)
    
    # 데이터베이스 연결
    db_manager = DatabaseManager("data/mud_engine.db")
    await db_manager.initialize()
    
    try:
        # 리포지토리 생성
        object_repo = GameObjectRepository(db_manager)
        room_repo = RoomRepository(db_manager)
        
        # 스포너 생성
        spawner = ItemSpawner(object_repo, room_repo)
        
        # 아이템 스폰
        spawned = await spawner.spawn_items(template_id, x, y, count)
        
        if spawned:
            print(f"\n✅ 총 {len(spawned)}개의 아이템이 생성되었습니다!")
            
            # 요약 정보
            print("\n" + "=" * 60)
            print("📊 스폰 요약")
            print("=" * 60)
            template = await spawner.load_template(template_id)
            if template:
                item_name = template.get('name_ko', template.get('name_en', template_id))
                print(f"  - 아이템: {item_name}")
                print(f"  - 개수: {len(spawned)}개")
                print(f"  - 위치: 좌표 ({x}, {y})")
                print(f"  - 타입: {template.get('object_type', 'item')}")
                print(f"  - 카테고리: {template.get('category', 'misc')}")
                print(f"  - 무게: {template.get('weight', 1.0)}")
                if template.get('stackable'):
                    print(f"  - 스택 가능: 최대 {template.get('max_stack', 1)}개")
                else:
                    print(f"  - 스택 불가")
            print("=" * 60)
        else:
            print("\n❌ 아이템 생성에 실패했습니다.")
        
    finally:
        await db_manager.close()


async def list_templates_main():
    """템플릿 목록 표시 메인 함수"""
    # 데이터베이스 연결
    db_manager = DatabaseManager("data/mud_engine.db")
    await db_manager.initialize()
    
    try:
        # 리포지토리 생성
        object_repo = GameObjectRepository(db_manager)
        room_repo = RoomRepository(db_manager)
        
        # 스포너 생성
        spawner = ItemSpawner(object_repo, room_repo)
        
        # 템플릿 목록 표시
        await spawner.list_templates()
        
    finally:
        await db_manager.close()


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='아이템 스폰 스크립트')
    parser.add_argument('template_id', nargs='?', help='아이템 템플릿 ID')
    parser.add_argument('x', nargs='?', type=int, help='X 좌표')
    parser.add_argument('y', nargs='?', type=int, help='Y 좌표')
    parser.add_argument('--count', type=int, default=1, help='생성할 아이템 개수 (기본: 1)')
    parser.add_argument('--list', action='store_true', help='사용 가능한 템플릿 목록 표시')
    
    args = parser.parse_args()
    
    if args.list:
        asyncio.run(list_templates_main())
    elif args.template_id and args.x is not None and args.y is not None:
        asyncio.run(spawn_items_main(args.template_id, args.x, args.y, args.count))
    else:
        parser.print_help()
        print("\n예시:")
        print("  python scripts/spawn_items.py torch 5 7")
        print("  python scripts/spawn_items.py bread 0 0 --count 3")
        print("  python scripts/spawn_items.py --list")
        sys.exit(1)


if __name__ == "__main__":
    main()