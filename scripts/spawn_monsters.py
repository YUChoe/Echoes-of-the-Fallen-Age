#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
범용 몬스터 스폰 스크립트

JSON 설정 파일을 기반으로 다양한 종류의 몬스터를 스폰합니다.
로밍 고정/활성화를 선택할 수 있습니다.

사용법:
    # 특정 몬스터 스폰
    python scripts/spawn_monsters.py --config configs/monsters/small_rats.json
    
    # 모든 몬스터 스폰
    python scripts/spawn_monsters.py --all
    
    # 기존 몬스터 삭제 후 스폰
    python scripts/spawn_monsters.py --config configs/monsters/small_rats.json --clean
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
    
    async def load_config(self, config_path: str) -> Dict[str, Any]:
        """JSON 설정 파일을 로드합니다."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"✅ 설정 파일 로드 완료: {config_path}")
            return config
        except Exception as e:
            print(f"❌ 설정 파일 로드 실패 ({config_path}): {e}")
            raise
    
    async def find_spawn_rooms(self, area_filter: Dict[str, Any]) -> List[Room]:
        """스폰 영역 필터에 맞는 방들을 찾습니다."""
        all_rooms = await self.room_repo.get_all()
        filtered_rooms = []
        
        # 특정 방 ID 필터
        if 'room_ids' in area_filter:
            room_ids = set(area_filter['room_ids'])
            for room in all_rooms:
                if room.id in room_ids:
                    filtered_rooms.append(room)
            return filtered_rooms
        
        # 이름 기반 필터
        name_contains = area_filter.get('name_contains')
        
        # 좌표 범위 필터
        x_range = area_filter.get('x_range')
        y_range = area_filter.get('y_range')
        min_x = area_filter.get('min_x')
        max_x = area_filter.get('max_x')
        min_y = area_filter.get('min_y')
        max_y = area_filter.get('max_y')
        
        for room in all_rooms:
            # 설명 필터 적용
            if name_contains:
                desc_ko = room.description.get('ko', '')
                if name_contains not in desc_ko:
                    continue
            
            # 좌표 필터 적용
            if room.x is None or room.y is None:
                continue
            
            if x_range and not (x_range[0] <= room.x <= x_range[1]):
                continue
            
            if y_range and not (y_range[0] <= room.y <= y_range[1]):
                continue
            
            if min_x is not None and room.x < min_x:
                continue
            
            if max_x is not None and room.x > max_x:
                continue
            
            if min_y is not None and room.y < min_y:
                continue
            
            if max_y is not None and room.y > max_y:
                continue
            
            filtered_rooms.append(room)
        
        return filtered_rooms
    
    async def create_template(self, config: Dict[str, Any]) -> Monster:
        """몬스터 템플릿을 생성합니다."""
        template_id = config['template_id']
        
        # 기존 템플릿 확인
        existing = await self.monster_repo.get_by_id(template_id)
        if existing:
            print(f"✅ 템플릿이 이미 존재합니다: {template_id}")
            return existing
        
        # 능력치 생성
        stats_data = config['stats']
        stats = MonsterStats(
            strength=stats_data['strength'],
            dexterity=stats_data['dexterity'],
            constitution=stats_data['constitution'],
            intelligence=stats_data['intelligence'],
            wisdom=stats_data['wisdom'],
            charisma=stats_data['charisma'],
            level=stats_data['level']
        )
        # current_hp는 __post_init__에서 자동으로 max_hp로 설정됨
        
        # 드롭 아이템 생성
        drop_items = []
        for item_data in config.get('drop_items', []):
            drop_items.append(DropItem(
                item_id=item_data['item_id'],
                drop_chance=item_data['drop_chance']
            ))
        
        # 몬스터 타입 변환
        monster_type = MonsterType[config['monster_type']]
        behavior = MonsterBehavior[config['behavior']]
        
        # 템플릿 생성
        template = Monster(
            id=template_id,
            name=config['name'],
            description=config['description'],
            monster_type=monster_type,
            behavior=behavior,
            stats=stats,
            experience_reward=config['experience_reward'],
            gold_reward=config['gold_reward'],
            drop_items=drop_items,
            spawn_room_id=None,
            current_room_id=None,
            respawn_time=config['respawn_time'],
            aggro_range=config['aggro_range'],
            roaming_range=config['roaming_range'],
            properties={
                'level': stats_data['level'],
                'is_template': True
            },
            created_at=datetime.now()
        )
        
        # 데이터베이스에 저장
        created = await self.monster_repo.create(template.to_dict())
        print(f"✅ 템플릿 생성 완료: {template_id}")
        
        return created
    
    async def spawn_monsters(self, config: Dict[str, Any]) -> List[Monster]:
        """설정에 따라 몬스터들을 스폰합니다."""
        spawn_config = config['spawn_config']
        count = spawn_config['count']
        global_max_count = spawn_config.get('global_max_count')
        area_filter = spawn_config.get('area_filter', {})
        distribution = spawn_config.get('distribution', 'random')
        roaming_config = spawn_config.get('roaming', {})
        
        # 글로벌 제한 확인
        if global_max_count is not None:
            template_id = config['template_id']
            all_monsters = await self.monster_repo.get_all()
            existing_count = sum(1 for m in all_monsters 
                               if m.get_property('template_id') == template_id and m.is_alive)
            
            if existing_count >= global_max_count:
                print(f"⚠️  글로벌 제한 도달: {existing_count}/{global_max_count}마리 (스폰 중단)")
                return []
            
            # 스폰 가능한 수량 조정
            available_count = global_max_count - existing_count
            if count > available_count:
                print(f"⚠️  글로벌 제한으로 스폰 수량 조정: {count} -> {available_count}마리")
                count = available_count
        
        # 스폰 가능한 방 찾기
        spawn_rooms = await self.find_spawn_rooms(area_filter)
        
        if not spawn_rooms:
            print("❌ 스폰 가능한 방이 없습니다.")
            return []
        
        print(f"\n📍 스폰 가능한 방: {len(spawn_rooms)}개")
        print(f"📍 스폰할 개체 수: {count}마리")
        if global_max_count is not None:
            print(f"📍 글로벌 최대 수량: {global_max_count}마리")
        print(f"📍 분배 방식: {distribution}")
        print(f"📍 로밍 활성화: {roaming_config.get('enabled', False)}")
        
        spawned_monsters = []
        
        # 능력치 데이터
        stats_data = config['stats']
        
        # 드롭 아이템
        drop_items = []
        for item_data in config.get('drop_items', []):
            drop_items.append(DropItem(
                item_id=item_data['item_id'],
                drop_chance=item_data['drop_chance']
            ))
        
        # 몬스터 타입
        monster_type = MonsterType[config['monster_type']]
        behavior = MonsterBehavior[config['behavior']]
        
        # 로밍 영역 계산
        roaming_area = None
        if roaming_config.get('enabled') and roaming_config.get('use_spawn_area'):
            roaming_area = {
                'min_x': min(room.x for room in spawn_rooms if room.x is not None),
                'max_x': max(room.x for room in spawn_rooms if room.x is not None),
                'min_y': min(room.y for room in spawn_rooms if room.y is not None),
                'max_y': max(room.y for room in spawn_rooms if room.y is not None)
            }
        
        # 몬스터 스폰
        import random
        for i in range(count):
            # 스폰 방 선택
            if distribution == 'fixed' and i < len(spawn_rooms):
                spawn_room = spawn_rooms[i]
            else:
                spawn_room = random.choice(spawn_rooms)
            
            # 능력치 생성
            stats = MonsterStats(
                strength=stats_data['strength'],
                dexterity=stats_data['dexterity'],
                constitution=stats_data['constitution'],
                intelligence=stats_data['intelligence'],
                wisdom=stats_data['wisdom'],
                charisma=stats_data['charisma'],
                level=stats_data['level']
            )
            # current_hp는 __post_init__에서 자동으로 max_hp로 설정됨
            
            # 몬스터 속성
            properties = {
                'level': stats_data['level'],
                'template_id': config['template_id']
            }
            
            # 로밍 설정 추가
            if roaming_config.get('enabled'):
                properties['roaming_config'] = {
                    'roam_chance': roaming_config.get('roam_chance', 0.5),
                    'roaming_area': roaming_area
                }
            
            # 몬스터 생성
            monster = Monster(
                id=str(uuid4()),
                name=config['name'].copy(),
                description=config['description'].copy(),
                monster_type=monster_type,
                behavior=behavior,
                stats=stats,
                experience_reward=config['experience_reward'],
                gold_reward=config['gold_reward'],
                drop_items=drop_items.copy(),
                spawn_room_id=spawn_room.id,
                current_room_id=spawn_room.id,
                respawn_time=config['respawn_time'],
                aggro_range=config['aggro_range'],
                roaming_range=config['roaming_range'],
                properties=properties,
                is_alive=True,
                created_at=datetime.now()
            )
            
            # 데이터베이스에 저장
            created_monster = await self.monster_repo.create(monster.to_dict())
            spawned_monsters.append(created_monster)
            
            monster_name = config['name'].get('ko', config['name'].get('en'))
            print(f"  🎯 {monster_name} #{i+1} 스폰됨: 좌표 ({spawn_room.x}, {spawn_room.y})")
        
        return spawned_monsters
    
    async def clean_monsters(self, template_id: str) -> int:
        """특정 템플릿의 몬스터들을 삭제합니다."""
        try:
            all_monsters = await self.monster_repo.get_all()
            deleted_count = 0
            
            for monster in all_monsters:
                if monster.get_property('template_id') == template_id:
                    await self.monster_repo.delete(monster.id)
                    deleted_count += 1
            
            print(f"🗑️  {template_id} 몬스터 {deleted_count}마리 삭제됨")
            return deleted_count
        except Exception as e:
            print(f"❌ 몬스터 삭제 실패: {e}")
            return 0
    
    async def cleanup_excess_monsters(self, template_id: str, global_max_count: int) -> int:
        """글로벌 제한을 초과하는 몬스터를 삭제합니다."""
        try:
            all_monsters = await self.monster_repo.get_all()
            template_monsters = [m for m in all_monsters 
                               if m.get_property('template_id') == template_id and m.is_alive]
            
            excess_count = len(template_monsters) - global_max_count
            if excess_count <= 0:
                print(f"✅ 초과 몬스터 없음: {template_id} ({len(template_monsters)}/{global_max_count})")
                return 0
            
            # 오래된 몬스터부터 삭제 (created_at 기준)
            template_monsters.sort(key=lambda m: m.created_at)
            monsters_to_delete = template_monsters[:excess_count]
            
            deleted_count = 0
            for monster in monsters_to_delete:
                await self.monster_repo.delete(monster.id)
                deleted_count += 1
                monster_name = monster.get_localized_name('ko')
                print(f"  🗑️  초과 몬스터 삭제: {monster_name} (ID: {monster.id[:8]}...)")
            
            print(f"✅ 초과 몬스터 정리 완료: {template_id} - {deleted_count}마리 삭제")
            return deleted_count
        except Exception as e:
            print(f"❌ 초과 몬스터 정리 실패: {e}")
            return 0


async def spawn_from_config(config_path: str, clean: bool = False):
    """설정 파일로부터 몬스터를 스폰합니다."""
    print("=" * 60)
    print(f"몬스터 스폰: {config_path}")
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
        
        # 설정 로드
        config = await spawner.load_config(config_path)
        
        # 기존 몬스터 삭제 (옵션)
        if clean:
            print("\n🗑️  기존 몬스터 삭제 중...")
            await spawner.clean_monsters(config['template_id'])
        
        # 템플릿 생성
        print("\n1️⃣ 템플릿 생성 중...")
        await spawner.create_template(config)
        
        # 글로벌 제한 초과 몬스터 정리
        global_max_count = config['spawn_config'].get('global_max_count')
        if global_max_count is not None:
            print(f"\n2️⃣ 글로벌 제한 초과 몬스터 정리 중... (최대: {global_max_count}마리)")
            await spawner.cleanup_excess_monsters(config['template_id'], global_max_count)
        
        # 몬스터 스폰
        print("\n3️⃣ 몬스터 스폰 중...")
        spawned = await spawner.spawn_monsters(config)
        
        print(f"\n✅ 총 {len(spawned)}마리의 몬스터가 스폰되었습니다!")
        
        # 요약 정보
        print("\n" + "=" * 60)
        print("📊 스폰 요약")
        print("=" * 60)
        monster_name = config['name'].get('ko', config['name'].get('en'))
        print(f"  - 몬스터: {monster_name}")
        print(f"  - 개체 수: {len(spawned)}마리")
        if global_max_count is not None:
            print(f"  - 글로벌 최대: {global_max_count}마리")
        print(f"  - 레벨: {config['stats']['level']}")
        print(f"  - 타입: {config['monster_type']}")
        print(f"  - 행동: {config['behavior']}")
        print(f"  - 경험치: {config['experience_reward']} exp")
        print(f"  - 골드: {config['gold_reward']} gold")
        
        roaming_config = config['spawn_config'].get('roaming', {})
        if roaming_config.get('enabled'):
            print(f"  - 로밍: 활성화 ({roaming_config.get('roam_chance', 0.5) * 100:.0f}% 확률)")
        else:
            print(f"  - 로밍: 비활성화 (고정)")
        
        print("=" * 60)
        
    finally:
        await db_manager.close()


async def spawn_all_configs(configs_dir: str = "configs/monsters", clean: bool = False):
    """모든 설정 파일로부터 몬스터를 스폰합니다."""
    configs_path = Path(configs_dir)
    
    if not configs_path.exists():
        print(f"❌ 설정 디렉토리가 존재하지 않습니다: {configs_dir}")
        return
    
    # JSON 파일 찾기
    config_files = list(configs_path.glob("*.json"))
    
    if not config_files:
        print(f"❌ 설정 파일이 없습니다: {configs_dir}")
        return
    
    print(f"📁 {len(config_files)}개의 설정 파일 발견")
    print()
    
    for config_file in config_files:
        try:
            await spawn_from_config(str(config_file), clean)
            print()
        except Exception as e:
            print(f"❌ 스폰 실패 ({config_file}): {e}")
            print()


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='범용 몬스터 스폰 스크립트')
    parser.add_argument('--config', type=str, help='몬스터 설정 파일 경로')
    parser.add_argument('--all', action='store_true', help='모든 설정 파일로부터 스폰')
    parser.add_argument('--clean', action='store_true', help='기존 몬스터 삭제 후 스폰')
    parser.add_argument('--configs-dir', type=str, default='configs/monsters', 
                       help='설정 파일 디렉토리 (기본: configs/monsters)')
    
    args = parser.parse_args()
    
    if args.all:
        asyncio.run(spawn_all_configs(args.configs_dir, args.clean))
    elif args.config:
        asyncio.run(spawn_from_config(args.config, args.clean))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
