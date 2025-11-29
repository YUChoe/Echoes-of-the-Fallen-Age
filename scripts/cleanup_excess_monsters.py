#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""초과 스폰된 몬스터 정리 스크립트"""

import asyncio
import sys
import os
from datetime import datetime
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.mud_engine.database.connection import DatabaseManager


async def cleanup_excess_monsters(db_manager: DatabaseManager):
    """글로벌 제한 및 방별 초기 스폰 수를 초과한 몬스터 삭제"""
    
    # 글로벌 최대 수량 (전체 맵)
    global_limits = {
        'template_small_rat': 20,      # 작은 쥐: 전체 최대 20마리
        'template_forest_goblin': 10,  # 숲 고블린: 전체 최대 10마리
        'template_town_guard': 4        # 마을 경비병: 전체 최대 4마리
    }
    
    # 각 템플릿별 방당 최대 수
    room_limits = {
        'template_small_rat': 5,      # 작은 쥐: 방당 최대 5마리
        'template_forest_goblin': 3,  # 숲 고블린: 방당 최대 3마리
        'template_town_guard': 1       # 마을 경비병: 방당 최대 1마리
    }
    
    total_deleted = 0
    
    # 1단계: 글로벌 제한 초과 몬스터 정리
    print("=" * 60)
    print("1단계: 글로벌 제한 초과 몬스터 정리")
    print("=" * 60)
    
    import json
    for template_id, global_limit in global_limits.items():
        # 해당 템플릿의 모든 살아있는 몬스터 조회
        cursor = await db_manager.execute("""
            SELECT id, name_ko, properties, created_at, current_room_id
            FROM monsters 
            WHERE is_alive = 1
            ORDER BY created_at ASC
        """)
        
        all_monsters = await cursor.fetchall()
        template_monsters = []
        
        for monster_id, monster_name, properties_str, created_at, room_id in all_monsters:
            try:
                properties = json.loads(properties_str) if properties_str else {}
                if properties.get('template_id') == template_id:
                    template_monsters.append({
                        'id': monster_id,
                        'name': monster_name,
                        'created_at': created_at,
                        'room_id': room_id
                    })
            except:
                pass
        
        if len(template_monsters) > global_limit:
            excess_count = len(template_monsters) - global_limit
            # 오래된 것부터 삭제
            monsters_to_delete = template_monsters[:excess_count]
            
            print(f"\n🔍 {template_id}: {len(template_monsters)}마리 → {global_limit}마리")
            for monster in monsters_to_delete:
                await db_manager.execute("DELETE FROM monsters WHERE id = ?", (monster['id'],))
                total_deleted += 1
                print(f"  🗑️  삭제: {monster['name']} (ID: {monster['id'][:8]}...)")
            
            print(f"✅ {excess_count}마리 삭제 완료")
        else:
            print(f"✓ {template_id}: {len(template_monsters)}/{global_limit}마리 (정상)")
    
    print("\n" + "=" * 60)
    print("2단계: 방별 제한 초과 몬스터 정리")
    print("=" * 60 + "\n")
    
    # 모든 방 조회
    cursor = await db_manager.execute("""
        SELECT id, name_ko FROM rooms 
        WHERE x IS NOT NULL AND y IS NOT NULL
        ORDER BY id
    """)
    all_rooms = await cursor.fetchall()
    
    print(f"전체 방 {len(all_rooms)}개 확인\n")
    
    for room_id, room_name in all_rooms:
        # 해당 방의 모든 몬스터 조회
        cursor = await db_manager.execute("""
            SELECT id, name_ko, properties, created_at 
            FROM monsters 
            WHERE current_room_id = ?
            ORDER BY created_at DESC
        """, (room_id,))
        
        monsters = await cursor.fetchall()
        
        if not monsters:
            continue
        
        # 템플릿별로 그룹화
        import json
        monsters_by_template = {}
        for monster_id, monster_name, properties_str, created_at in monsters:
            try:
                properties = json.loads(properties_str) if properties_str else {}
                template_id = properties.get('template_id', 'unknown')
                
                if template_id not in monsters_by_template:
                    monsters_by_template[template_id] = []
                
                monsters_by_template[template_id].append({
                    'id': monster_id,
                    'name': monster_name,
                    'created_at': created_at
                })
            except:
                pass
        
        # 각 템플릿별로 초과 확인 및 삭제
        room_deleted = 0
        for template_id, monster_list in monsters_by_template.items():
            max_count = room_limits.get(template_id, 1)
            
            if len(monster_list) > max_count:
                excess_count = len(monster_list) - max_count
                # 오래된 것부터 삭제 (최신 것 유지)
                monsters_to_delete = monster_list[max_count:]
                
                for monster in monsters_to_delete:
                    await db_manager.execute("DELETE FROM monsters WHERE id = ?", (monster['id'],))
                    room_deleted += 1
                    total_deleted += 1
                
                print(f"✅ {room_name} - {template_id}: {len(monster_list)}마리 → {max_count}마리 ({excess_count}마리 삭제)")
        
        if room_deleted == 0 and len(monsters) > 0:
            print(f"✓ {room_name}: {len(monsters)}마리 (정상)")
    
    return total_deleted


async def main():
    """메인 실행 함수"""
    print("=== 초과 몬스터 정리 시작 ===\n")
    
    # 백업 생성
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"data/mud_engine.db.backup_{timestamp}"
    shutil.copy2("data/mud_engine.db", backup_file)
    print(f"✅ 백업 생성: {backup_file}\n")
    
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    try:
        total_deleted = await cleanup_excess_monsters(db_manager)
        
        print(f"\n=== 정리 완료 ===")
        print(f"총 {total_deleted}마리 삭제")
        print(f"백업: {backup_file}")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await db_manager.close()
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
