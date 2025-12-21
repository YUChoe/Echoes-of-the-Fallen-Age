"""
모델별 리포지토리 클래스들
"""

import logging
from typing import Dict, List, Optional

from ..database.repository import BaseRepository
from .models import Player, Character, Room, GameObject, NPC
from .monster import Monster

logger = logging.getLogger(__name__)


class PlayerRepository(BaseRepository[Player]):
    """플레이어 리포지토리"""

    def get_table_name(self) -> str:
        return "players"

    def get_model_class(self):
        return Player

    async def get_by_username(self, username: str) -> Optional[Player]:
        """사용자명으로 플레이어 조회"""
        try:
            results = await self.find_by(username=username)
            return results[0] if results else None
        except Exception as e:
            logger.error(f"사용자명으로 플레이어 조회 실패 ({username}): {e}")
            raise

    async def username_exists(self, username: str) -> bool:
        """사용자명 중복 확인"""
        try:
            player = await self.get_by_username(username)
            return player is not None
        except Exception as e:
            logger.error(f"사용자명 중복 확인 실패 ({username}): {e}")
            raise

    async def update_last_login(self, player_id: str) -> Optional[Player]:
        """마지막 로그인 시간 업데이트"""
        from datetime import datetime
        try:
            return await self.update(player_id, {'last_login': datetime.now().isoformat()})
        except Exception as e:
            logger.error(f"마지막 로그인 시간 업데이트 실패 ({player_id}): {e}")
            raise


class CharacterRepository(BaseRepository[Character]):
    """캐릭터 리포지토리"""

    def get_table_name(self) -> str:
        return "characters"

    def get_model_class(self):
        return Character

    async def get_by_player_id(self, player_id: str) -> List[Character]:
        """플레이어 ID로 캐릭터 목록 조회"""
        try:
            return await self.find_by(player_id=player_id)
        except Exception as e:
            logger.error(f"플레이어 캐릭터 조회 실패 ({player_id}): {e}")
            raise

    async def get_by_name(self, name: str) -> Optional[Character]:
        """캐릭터 이름으로 조회"""
        try:
            results = await self.find_by(name=name)
            return results[0] if results else None
        except Exception as e:
            logger.error(f"캐릭터 이름으로 조회 실패 ({name}): {e}")
            raise

    async def name_exists(self, name: str) -> bool:
        """캐릭터 이름 중복 확인"""
        try:
            character = await self.get_by_name(name)
            return character is not None
        except Exception as e:
            logger.error(f"캐릭터 이름 중복 확인 실패 ({name}): {e}")
            raise

    async def get_characters_in_room(self, room_id: str) -> List[Character]:
        """특정 방에 있는 캐릭터들 조회"""
        try:
            return await self.find_by(current_room_id=room_id)
        except Exception as e:
            logger.error(f"방 내 캐릭터 조회 실패 ({room_id}): {e}")
            raise

    async def move_to_room(self, character_id: str, room_id: str) -> Optional[Character]:
        """캐릭터를 특정 방으로 이동"""
        try:
            return await self.update(character_id, {'current_room_id': room_id})
        except Exception as e:
            logger.error(f"캐릭터 이동 실패 ({character_id} -> {room_id}): {e}")
            raise


class RoomRepository(BaseRepository[Room]):
    """방 리포지토리"""

    def get_table_name(self) -> str:
        return "rooms"

    def get_model_class(self):
        return Room

    async def get_room_by_coordinates(self, x: int, y: int) -> Optional[Room]:
        """좌표로 방 조회"""
        try:
            db_manager = await self.get_db_manager()
            cursor = await db_manager.execute(
                "SELECT * FROM rooms WHERE x = ? AND y = ?",
                (x, y)
            )
            row = await cursor.fetchone()
            if row:
                # SQLite row를 딕셔너리로 변환
                columns = [description[0] for description in cursor.description]
                row_dict = dict(zip(columns, row))
                return Room.from_dict(row_dict)
            return None
        except Exception as e:
            logger.error(f"좌표 기반 방 조회 실패 ({x}, {y}): {e}")
            raise

    async def get_connected_rooms(self, room_id: str) -> List[Room]:
        """연결된 방들 조회 (좌표 기반)"""
        try:
            room = await self.get_by_id(room_id)
            if not room or room.x is None or room.y is None:
                return []

            from ...utils.coordinate_utils import Direction, calculate_new_coordinates
            connected_rooms = []

            # 모든 방향의 인접 좌표 확인
            for direction in Direction:
                target_x, target_y = calculate_new_coordinates(room.x, room.y, direction)

                # 해당 좌표에 방이 있는지 확인
                db_manager = await self.get_db_manager()
                cursor = await db_manager.execute(
                    "SELECT * FROM rooms WHERE x = ? AND y = ?",
                    (target_x, target_y)
                )
                row = await cursor.fetchone()
                if row:
                    connected_room = Room.from_dict(dict(row))
                    connected_rooms.append(connected_room)

            return connected_rooms
        except Exception as e:
            logger.error(f"연결된 방 조회 실패 ({room_id}): {e}")
            raise

    async def find_rooms_by_name(self, name_pattern: str, locale: str = 'en') -> List[Room]:
        """이름 패턴으로 방 검색 (부분 일치)"""
        try:
            # 모든 방을 가져와서 이름으로 필터링 (SQLite LIKE 쿼리 대신)
            all_rooms = await self.get_all()
            matching_rooms = []

            for room in all_rooms:
                # 방 설명으로 검색
                room_desc = room.get_localized_description(locale).lower()
                if name_pattern.lower() in room_desc:
                    matching_rooms.append(room)

            return matching_rooms
        except Exception as e:
            logger.error(f"방 이름 검색 실패 ({name_pattern}): {e}")
            raise

    async def get_rooms_with_exits_to(self, target_room_id: str) -> List[Room]:
        """특정 방으로 출구가 있는 방들 조회 (좌표 기반)"""
        try:
            target_room = await self.get_by_id(target_room_id)
            if not target_room or target_room.x is None or target_room.y is None:
                return []

            from ...utils.coordinate_utils import Direction, calculate_new_coordinates
            rooms_with_exits = []

            # 대상 방의 인접 좌표들 확인
            for direction in Direction:
                source_x, source_y = calculate_new_coordinates(target_room.x, target_room.y, direction)

                # 해당 좌표에 방이 있는지 확인
                db_manager = await self.get_db_manager()
                cursor = await db_manager.execute(
                    "SELECT * FROM rooms WHERE x = ? AND y = ?",
                    (source_x, source_y)
                )
                row = await cursor.fetchone()
                if row:
                    source_room = Room.from_dict(dict(row))
                    rooms_with_exits.append(source_room)

            return rooms_with_exits
        except Exception as e:
            logger.error(f"출구 대상 방 조회 실패 ({target_room_id}): {e}")
            raise


class GameObjectRepository(BaseRepository[GameObject]):
    """게임 객체 리포지토리"""

    def get_table_name(self) -> str:
        return "game_objects"

    def get_model_class(self):
        return GameObject

    async def get_objects_in_room(self, room_id: str) -> List[GameObject]:
        """특정 방에 있는 객체들 조회"""
        try:
            # 대소문자 모두 검색
            room_objects = await self.find_by(location_type='ROOM', location_id=room_id)
            room_objects_lower = await self.find_by(location_type='room', location_id=room_id)
            return room_objects + room_objects_lower
        except Exception as e:
            logger.error(f"방 내 객체 조회 실패 ({room_id}): {e}")
            raise

    async def get_objects_in_inventory(self, character_id: str) -> List[GameObject]:
        """특정 캐릭터의 인벤토리 객체들 조회"""
        try:
            # 대소문자 모두 검색
            inventory_objects = await self.find_by(location_type='INVENTORY', location_id=character_id)
            inventory_objects_lower = await self.find_by(location_type='inventory', location_id=character_id)
            return inventory_objects + inventory_objects_lower
        except Exception as e:
            logger.error(f"인벤토리 객체 조회 실패 ({character_id}): {e}")
            raise

    async def get_objects_by_type(self, object_type: str) -> List[GameObject]:
        """타입별 객체 조회 (object_type 필드 제거됨 - 모든 객체 반환)"""
        try:
            # object_type 필드가 제거되었으므로 모든 객체를 반환
            return await self.get_all()
        except Exception as e:
            logger.error(f"객체 조회 실패: {e}")
            raise

    async def move_object_to_room(self, object_id: str, room_id: str) -> Optional[GameObject]:
        """객체를 방으로 이동"""
        try:
            return await self.update(object_id, {
                'location_type': 'ROOM',
                'location_id': room_id
            })
        except Exception as e:
            logger.error(f"객체 방 이동 실패 ({object_id} -> {room_id}): {e}")
            raise

    async def move_object_to_inventory(self, object_id: str, character_id: str) -> Optional[GameObject]:
        """객체를 인벤토리로 이동"""
        try:
            return await self.update(object_id, {
                'location_type': 'inventory',
                'location_id': character_id
            })
        except Exception as e:
            logger.error(f"객체 인벤토리 이동 실패 ({object_id} -> {character_id}): {e}")
            raise

    async def find_objects_by_name(self, name_pattern: str, locale: str = 'en') -> List[GameObject]:
        """이름 패턴으로 객체 검색 (부분 일치)"""
        try:
            # 모든 객체를 가져와서 이름으로 필터링
            all_objects = await self.get_all()
            matching_objects = []

            for obj in all_objects:
                obj_name = obj.get_localized_name(locale).lower()
                if name_pattern.lower() in obj_name:
                    matching_objects.append(obj)

            return matching_objects
        except Exception as e:
            logger.error(f"객체 이름 검색 실패 ({name_pattern}): {e}")
            raise

    async def get_objects_in_container(self, container_id: str) -> List[GameObject]:
        """컨테이너 내부의 객체들 조회"""
        try:
            # 대소문자 모두 검색
            container_objects = await self.find_by(location_type='CONTAINER', location_id=container_id)
            container_objects_lower = await self.find_by(location_type='container', location_id=container_id)
            return container_objects + container_objects_lower
        except Exception as e:
            logger.error(f"컨테이너 내 객체 조회 실패 ({container_id}): {e}")
            raise

    async def move_object_to_container(self, object_id: str, container_id: str) -> Optional[GameObject]:
        """객체를 컨테이너로 이동"""
        try:
            return await self.update(object_id, {
                'location_type': 'container',
                'location_id': container_id
            })
        except Exception as e:
            logger.error(f"객체 컨테이너 이동 실패 ({object_id} -> {container_id}): {e}")
            raise


class NPCRepository(BaseRepository[NPC]):
    """NPC 리포지토리"""

    def get_table_name(self) -> str:
        return "npcs"

    def get_model_class(self):
        return NPC

    async def get_npcs_at_coordinates(self, x: int, y: int) -> List[NPC]:
        """특정 좌표에 있는 NPC들 조회"""
        try:
            return await self.find_by(x=x, y=y, is_active=True)
        except Exception as e:
            logger.error(f"좌표 내 NPC 조회 실패 ({x}, {y}): {e}")
            raise

    async def get_npcs_in_room(self, room_id: str) -> List[NPC]:
        """특정 방에 있는 NPC들 조회 (하위 호환성)"""
        try:
            # 방 ID로부터 좌표 추출
            db_manager = await self.get_db_manager()
            cursor = await db_manager.execute(
                "SELECT x, y FROM rooms WHERE id = ?", (room_id,)
            )
            room_data = await cursor.fetchone()

            if not room_data:
                return []

            x, y = room_data
            # 해당 좌표의 NPC들 조회
            return await self.get_npcs_at_coordinates(x, y)
        except Exception as e:
            logger.error(f"방 내 NPC 조회 실패 ({room_id}): {e}")
            raise

    async def get_npcs_by_type(self, npc_type: str) -> List[NPC]:
        """타입별 NPC 조회"""
        try:
            return await self.find_by(npc_type=npc_type, is_active=True)
        except Exception as e:
            logger.error(f"타입별 NPC 조회 실패 ({npc_type}): {e}")
            raise

    async def get_merchants(self) -> List[NPC]:
        """상인 NPC들 조회"""
        try:
            return await self.get_npcs_by_type('merchant')
        except Exception as e:
            logger.error(f"상인 NPC 조회 실패: {e}")
            raise

    async def move_npc_to_coordinates(self, npc_id: str, x: int, y: int) -> Optional[NPC]:
        """NPC를 특정 좌표로 이동"""
        try:
            return await self.update(npc_id, {'x': x, 'y': y})
        except Exception as e:
            logger.error(f"NPC 이동 실패 ({npc_id} -> {x},{y}): {e}")
            raise

    async def deactivate_npc(self, npc_id: str) -> Optional[NPC]:
        """NPC 비활성화"""
        try:
            return await self.update(npc_id, {'is_active': False})
        except Exception as e:
            logger.error(f"NPC 비활성화 실패 ({npc_id}): {e}")
            raise

    async def activate_npc(self, npc_id: str) -> Optional[NPC]:
        """NPC 활성화"""
        try:
            return await self.update(npc_id, {'is_active': True})
        except Exception as e:
            logger.error(f"NPC 활성화 실패 ({npc_id}): {e}")
            raise

    async def find_npcs_by_name(self, name_pattern: str, locale: str = 'en') -> List[NPC]:
        """이름 패턴으로 NPC 검색 (부분 일치)"""
        try:
            all_npcs = await self.find_by(is_active=True)
            matching_npcs = []

            for npc in all_npcs:
                npc_name = npc.get_localized_name(locale).lower()
                if name_pattern.lower() in npc_name:
                    matching_npcs.append(npc)

            return matching_npcs
        except Exception as e:
            logger.error(f"NPC 이름 검색 실패 ({name_pattern}): {e}")
            raise


class ModelManager:
    """모델 매니저 - 모든 리포지토리를 통합 관리"""

    def __init__(self, db_manager=None):
        """ModelManager 초기화"""
        self.players = PlayerRepository(db_manager)
        self.characters = CharacterRepository(db_manager)
        self.rooms = RoomRepository(db_manager)
        self.game_objects = GameObjectRepository(db_manager)
        self.npcs = NPCRepository(db_manager)

        logger.info("ModelManager 초기화 완료")

    async def validate_character_room_reference(self, character_id: str) -> bool:
        """캐릭터의 방 참조 무결성 검증"""
        try:
            character = await self.characters.get_by_id(character_id)
            if not character or not character.current_room_id:
                return True  # 방이 설정되지 않은 경우는 유효

            room = await self.rooms.get_by_id(character.current_room_id)
            return room is not None
        except Exception as e:
            logger.error(f"캐릭터 방 참조 검증 실패 ({character_id}): {e}")
            return False

    async def validate_object_location_reference(self, object_id: str) -> bool:
        """객체의 위치 참조 무결성 검증"""
        try:
            obj = await self.game_objects.get_by_id(object_id)
            if not obj or not obj.location_id:
                return True  # 위치가 설정되지 않은 경우는 유효

            if obj.location_type == 'room':
                room = await self.rooms.get_by_id(obj.location_id)
                return room is not None
            elif obj.location_type == 'inventory':
                character = await self.characters.get_by_id(obj.location_id)
                return character is not None

            return False
        except Exception as e:
            logger.error(f"객체 위치 참조 검증 실패 ({object_id}): {e}")
            return False

    async def cleanup_orphaned_references(self) -> Dict[str, int]:
        """고아 참조 정리"""
        cleanup_count = {
            'characters_moved': 0,
            'objects_moved': 0
        }

        try:
            # 존재하지 않는 방을 참조하는 캐릭터들을 기본 방으로 이동
            all_characters = await self.characters.get_all()
            default_room_id = 'town_square'  # 기본 방 ID

            for character in all_characters:
                if character.current_room_id:
                    room_exists = await self.validate_character_room_reference(character.id)
                    if not room_exists:
                        await self.characters.move_to_room(character.id, default_room_id)
                        cleanup_count['characters_moved'] += 1
                        logger.warning(f"캐릭터 {character.id}를 기본 방으로 이동")

            # 존재하지 않는 위치를 참조하는 객체들을 기본 방으로 이동
            all_objects = await self.game_objects.get_all()

            for obj in all_objects:
                if obj.location_id:
                    location_exists = await self.validate_object_location_reference(obj.id)
                    if not location_exists:
                        await self.game_objects.move_object_to_room(obj.id, default_room_id)
                        cleanup_count['objects_moved'] += 1
                        logger.warning(f"객체 {obj.id}를 기본 방으로 이동")

            logger.info(f"고아 참조 정리 완료: {cleanup_count}")
            return cleanup_count

        except Exception as e:
            logger.error(f"고아 참조 정리 실패: {e}")
            raise

class MonsterRepository(BaseRepository):
    """몬스터 리포지토리"""

    def get_table_name(self) -> str:
        return "monsters"

    def get_model_class(self):
        from .monster import Monster
        return Monster

    async def get_monsters_at_coordinates(self, x: int, y: int) -> List[Monster]:
        """특정 좌표에 있는 살아있는 몬스터들을 조회합니다."""
        try:
            monsters = await self.find_by(x=x, y=y, is_alive=True)
            logger.debug(f"좌표 ({x}, {y})에서 {len(monsters)}마리 몬스터 조회")
            return monsters
        except Exception as e:
            logger.error(f"좌표 내 몬스터 조회 실패 ({x}, {y}): {e}")
            return []

    async def get_monsters_in_room(self, room_id: str) -> List[Monster]:
        """특정 방에 있는 살아있는 몬스터들을 조회합니다 (레거시 호환용)."""
        try:
            # room_id로 방의 좌표를 찾아서 해당 좌표의 몬스터들을 조회
            from .managers.room_manager import RoomManager
            # 임시로 빈 리스트 반환 (좌표 기반으로 변경 필요)
            logger.warning(f"get_monsters_in_room은 더 이상 사용되지 않습니다. get_monsters_at_coordinates를 사용하세요.")
            return []
        except Exception as e:
            logger.error(f"방 내 몬스터 조회 실패 ({room_id}): {e}")
            return []

    async def kill_monster(self, monster_id: str) -> bool:
        """몬스터 사망 처리"""
        try:
            from datetime import datetime
            current_time = datetime.now().isoformat()

            db_manager = await self.get_db_manager()
            await db_manager.execute(
                "UPDATE monsters SET is_alive = FALSE, last_death_time = ? WHERE id = ?",
                (current_time, monster_id)
            )
            await db_manager.commit()

            logger.info(f"몬스터 {monster_id} 사망 처리 완료")
            return True

        except Exception as e:
            logger.error(f"몬스터 사망 처리 실패: {e}")
            db_manager = await self.get_db_manager()
            await db_manager.rollback()
            return False

    async def respawn_monster(self, monster_id: str) -> bool:
        """몬스터 리스폰 처리"""
        try:
            import json

            # 몬스터 정보 조회
            monster = await self.get_by_id(monster_id)
            if not monster:
                logger.error(f"몬스터 {monster_id}를 찾을 수 없습니다")
                return False

            # 좌표는 그대로 유지 (원래 스폰 위치에서 리스폰)

            # 능력치를 최대치로 복구
            monster.stats.current_hp = monster.stats.max_hp
            stats_json = json.dumps(monster.stats.to_dict(), ensure_ascii=False)

            db_manager = await self.get_db_manager()
            await db_manager.execute("""
                UPDATE monsters
                SET is_alive = TRUE,
                    last_death_time = NULL,
                    stats = ?
                WHERE id = ?
            """, (stats_json, monster_id))

            await db_manager.commit()

            logger.info(f"몬스터 {monster_id} 리스폰 완료")
            return True

        except Exception as e:
            logger.error(f"몬스터 리스폰 실패: {e}")
            db_manager = await self.get_db_manager()
            await db_manager.rollback()
            return False

    async def move_object_to_container(self, object_id: str, container_id: str) -> Optional[GameObject]:
        """객체를 컨테이너로 이동"""
        try:
            return await self.update(object_id, {
                'location_type': 'CONTAINER',
                'location_id': container_id
            })
        except Exception as e:
            logger.error(f"객체 컨테이너 이동 실패 ({object_id} -> {container_id}): {e}")
            raise