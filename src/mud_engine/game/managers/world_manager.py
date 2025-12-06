# -*- coding: utf-8 -*-
"""세계 관리자 모듈 - 통합 인터페이스"""
import logging
from typing import Dict, List, Optional, Any

from ..repositories import RoomRepository, GameObjectRepository, MonsterRepository, NPCRepository
from ..models import Room, GameObject, NPC
from ..monster import Monster

from .room_manager import RoomManager
from .object_manager import ObjectManager
from .monster_manager import MonsterManager

logger = logging.getLogger(__name__)


class WorldManager:
    """게임 세계 관리자 - 하위 매니저들을 통합하는 인터페이스"""

    def __init__(self, room_repo: RoomRepository, object_repo: GameObjectRepository, monster_repo: MonsterRepository, npc_repo: NPCRepository) -> None:
        """WorldManager를 초기화합니다."""
        self._room_manager = RoomManager(room_repo)
        self._object_manager = ObjectManager(object_repo)
        self._monster_manager = MonsterManager(monster_repo)
        self._npc_repo = npc_repo
        
        # MonsterManager에 RoomManager 참조 설정
        self._monster_manager.set_room_manager(self._room_manager)
        
        logger.info("WorldManager 초기화 완료")
    
    def set_game_engine(self, game_engine: Any) -> None:
        """GameEngine 참조를 설정합니다 (순환 참조 방지를 위해 초기화 후 설정)"""
        self._monster_manager.set_game_engine(game_engine)
        logger.debug("WorldManager에 GameEngine 참조 설정됨")

    # === 방 관리 위임 ===

    async def get_room(self, room_id: str) -> Optional[Room]:
        return await self._room_manager.get_room(room_id)

    async def create_room(self, room_data: Dict[str, Any]) -> Room:
        return await self._room_manager.create_room(room_data)

    async def update_room(self, room_id: str, updates: Dict[str, Any]) -> Optional[Room]:
        return await self._room_manager.update_room(room_id, updates)

    async def delete_room(self, room_id: str) -> bool:
        return await self._room_manager.delete_room(room_id, self._object_manager)

    async def get_all_rooms(self) -> List[Room]:
        return await self._room_manager.get_all_rooms()

    async def find_rooms_by_name(self, name_pattern: str, locale: str = 'en') -> List[Room]:
        return await self._room_manager.find_rooms_by_name(name_pattern, locale)

    async def get_connected_rooms(self, room_id: str) -> List[Room]:
        return await self._room_manager.get_connected_rooms(room_id)

    async def add_room_exit(self, room_id: str, direction: str, target_room_id: str) -> bool:
        return await self._room_manager.add_room_exit(room_id, direction, target_room_id)

    async def remove_room_exit(self, room_id: str, direction: str) -> bool:
        return await self._room_manager.remove_room_exit(room_id, direction)

    # === 게임 객체 관리 위임 ===

    async def get_game_object(self, object_id: str) -> Optional[GameObject]:
        return await self._object_manager.get_game_object(object_id)

    async def create_game_object(self, object_data: Dict[str, Any]) -> GameObject:
        return await self._object_manager.create_game_object(object_data)

    async def update_game_object(self, object_id: str, updates: Dict[str, Any]) -> Optional[GameObject]:
        return await self._object_manager.update_game_object(object_id, updates)

    async def delete_game_object(self, object_id: str) -> bool:
        return await self._object_manager.delete_game_object(object_id)

    async def get_room_objects(self, room_id: str) -> List[GameObject]:
        return await self._object_manager.get_room_objects(room_id)

    async def get_inventory_objects(self, character_id: str) -> List[GameObject]:
        return await self._object_manager.get_inventory_objects(character_id)

    async def move_object_to_room(self, object_id: str, room_id: str) -> bool:
        return await self._object_manager.move_object_to_room(object_id, room_id, self._room_manager)

    async def move_object_to_inventory(self, object_id: str, character_id: str) -> bool:
        return await self._object_manager.move_object_to_inventory(object_id, character_id)

    async def find_objects_by_name(self, name_pattern: str, locale: str = 'en') -> List[GameObject]:
        return await self._object_manager.find_objects_by_name(name_pattern, locale)

    async def get_objects_by_type(self, object_type: str) -> List[GameObject]:
        return await self._object_manager.get_objects_by_type(object_type)

    async def update_object(self, game_object: GameObject) -> bool:
        return await self._object_manager.update_object(game_object)

    async def remove_object(self, object_id: str) -> bool:
        return await self._object_manager.remove_object(object_id)

    async def get_equipped_objects(self, character_id: str) -> List[GameObject]:
        return await self._object_manager.get_equipped_objects(character_id)

    async def get_objects_by_category(self, character_id: str, category: str) -> List[GameObject]:
        return await self._object_manager.get_objects_by_category(character_id, category)

    # === 몬스터 관리 위임 ===

    async def get_monsters_in_room(self, room_id: str) -> List[Monster]:
        return await self._monster_manager.get_monsters_in_room(room_id)

    async def kill_monster(self, monster_id: str) -> bool:
        return await self._monster_manager.kill_monster(monster_id)

    async def get_monster(self, monster_id: str) -> Optional[Monster]:
        return await self._monster_manager.get_monster(monster_id)

    async def get_all_monsters(self) -> List[Monster]:
        return await self._monster_manager.get_all_monsters()

    async def create_monster(self, monster_data: Dict[str, Any]) -> Monster:
        return await self._monster_manager.create_monster(monster_data)

    async def update_monster(self, monster: Monster) -> bool:
        return await self._monster_manager.update_monster(monster)

    async def delete_monster(self, monster_id: str) -> bool:
        return await self._monster_manager.delete_monster(monster_id)

    async def move_monster_to_room(self, monster_id: str, room_id: str, game_engine=None) -> bool:
        return await self._monster_manager.move_monster_to_room(monster_id, room_id, self._room_manager, game_engine)

    async def find_monsters_by_name(self, name_pattern: str, locale: str = 'ko') -> List[Monster]:
        return await self._monster_manager.find_monsters_by_name(name_pattern, locale)

    # === 스폰 시스템 위임 ===

    async def start_spawn_scheduler(self) -> None:
        return await self._monster_manager.start_spawn_scheduler()

    async def stop_spawn_scheduler(self) -> None:
        return await self._monster_manager.stop_spawn_scheduler()

    async def add_spawn_point(self, room_id: str, monster_template_id: str, max_count: int = 1, spawn_chance: float = 1.0) -> None:
        return await self._monster_manager.add_spawn_point(room_id, monster_template_id, max_count, spawn_chance, self._room_manager)

    async def remove_spawn_point(self, room_id: str, monster_template_id: str) -> bool:
        return await self._monster_manager.remove_spawn_point(room_id, monster_template_id)

    async def get_spawn_points(self) -> Dict[str, List[Dict[str, Any]]]:
        return await self._monster_manager.get_spawn_points()

    async def get_room_spawn_points(self, room_id: str) -> List[Dict[str, Any]]:
        return await self._monster_manager.get_room_spawn_points(room_id)

    async def clear_spawn_points(self, room_id: Optional[str] = None) -> None:
        return await self._monster_manager.clear_spawn_points(room_id)

    def set_global_spawn_limit(self, template_id: str, max_count: int) -> None:
        return self._monster_manager.set_global_spawn_limit(template_id, max_count)

    def get_global_spawn_limit(self, template_id: str) -> Optional[int]:
        return self._monster_manager.get_global_spawn_limit(template_id)

    def get_all_global_spawn_limits(self) -> Dict[str, int]:
        return self._monster_manager.get_all_global_spawn_limits()

    async def cleanup_excess_monsters(self, template_id: str) -> int:
        return await self._monster_manager.cleanup_excess_monsters(template_id)

    async def cleanup_all_excess_monsters(self) -> Dict[str, int]:
        return await self._monster_manager.cleanup_all_excess_monsters()

    async def setup_default_spawn_points(self) -> None:
        return await self._monster_manager.setup_default_spawn_points(self._room_manager)

    async def check_aggressive_monsters(self, player_id: str, room_id: str, combat_system) -> Optional[Monster]:
        return await self._monster_manager.check_aggressive_monsters(player_id, room_id, combat_system)

    # === 위치 추적 및 요약 ===

    async def track_object_location(self, object_id: str) -> Optional[Dict[str, Any]]:
        """객체의 현재 위치 정보를 추적합니다."""
        try:
            obj = await self._object_manager.get_game_object(object_id)
            if not obj:
                return None

            location_info = {
                'object_id': object_id,
                'location_type': obj.location_type,
                'location_id': obj.location_id,
                'location_name': 'Unknown'
            }

            if obj.location_type == 'room' and obj.location_id:
                room = await self._room_manager.get_room(obj.location_id)
                if room:
                    location_info['location_name'] = room.id
            elif obj.location_type == 'inventory' and obj.location_id:
                location_info['location_name'] = f"Character {obj.location_id}"

            return location_info
        except Exception as e:
            logger.error(f"객체 위치 추적 실패 ({object_id}): {e}")
            raise

    async def get_location_summary(self, room_id: str, locale: str = 'en') -> Dict[str, Any]:
        """특정 방의 위치 요약 정보를 제공합니다."""
        try:
            room = await self._room_manager.get_room(room_id)
            if not room:
                return {}

            objects = await self._object_manager.get_room_objects(room_id)
            monsters = await self._monster_manager.get_monsters_in_room(room_id)
            npcs = await self._npc_repo.get_npcs_in_room(room_id)
            connected_rooms = await self._room_manager.get_connected_rooms(room_id)

            return {
                'room': room,
                'objects': objects,
                'monsters': monsters,
                'npcs': npcs,
                'exits': room.exits,
                'connected_rooms': connected_rooms
            }
        except Exception as e:
            logger.error(f"위치 요약 정보 조회 실패 ({room_id}): {e}")
            raise

    # === 세계 무결성 검증 ===

    async def validate_world_integrity(self) -> Dict[str, List[str]]:
        """게임 세계의 무결성을 검증합니다."""
        try:
            issues: Dict[str, List[str]] = {
                'invalid_exits': [],
                'orphaned_objects': [],
                'missing_rooms': []
            }

            all_rooms = await self._room_manager.get_all_rooms()
            room_ids = {room.id for room in all_rooms}

            for room in all_rooms:
                for direction, target_room_id in room.exits.items():
                    if target_room_id not in room_ids:
                        issues['invalid_exits'].append(f"{room.id}:{direction}->{target_room_id}")

            all_objects = await self._object_manager._object_repo.get_all()
            for obj in all_objects:
                if obj.location_type == 'room' and obj.location_id:
                    if obj.location_id not in room_ids:
                        issues['orphaned_objects'].append(obj.id)

            logger.info(f"세계 무결성 검증 완료: {len(issues['invalid_exits'])} 잘못된 출구, "
                       f"{len(issues['orphaned_objects'])} 고아 객체")
            return issues
        except Exception as e:
            logger.error(f"세계 무결성 검증 실패: {e}")
            raise

    async def repair_world_integrity(self) -> Dict[str, int]:
        """게임 세계의 무결성 문제를 자동으로 수정합니다."""
        try:
            repair_count = {'exits_fixed': 0, 'objects_moved': 0}
            issues = await self.validate_world_integrity()
            default_room_id = 'room_001'

            for invalid_exit in issues['invalid_exits']:
                room_id, direction_target = invalid_exit.split(':', 1)
                direction, _ = direction_target.split('->', 1)
                success = await self._room_manager.remove_room_exit(room_id, direction)
                if success:
                    repair_count['exits_fixed'] += 1

            for object_id in issues['orphaned_objects']:
                success = await self._object_manager.move_object_to_room(object_id, default_room_id, self._room_manager)
                if success:
                    repair_count['objects_moved'] += 1

            logger.info(f"세계 무결성 수정 완료: {repair_count}")
            return repair_count
        except Exception as e:
            logger.error(f"세계 무결성 수정 실패: {e}")
            raise

    # === 통계 조회 (관리자용) ===

    async def get_all_rooms_for_stats(self) -> List[Room]:
        """통계 조회를 위한 모든 방 목록 반환"""
        return await self._room_manager.get_all_rooms()

    async def get_all_objects_for_stats(self) -> List[GameObject]:
        """통계 조회를 위한 모든 객체 목록 반환"""
        return await self._object_manager._object_repo.get_all()

    # === NPC 관리 (몬스터 시스템 활용) ===

    async def get_npcs_in_room(self, room_id: str) -> List[NPC]:
        """특정 방에 있는 NPC들을 조회합니다."""
        return await self._npc_repo.get_npcs_in_room(room_id)
