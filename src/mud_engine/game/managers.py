# -*- coding: utf-8 -*-
"""게임의 핵심 관리자(Manager) 클래스들을 정의합니다."""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .repositories import PlayerRepository, RoomRepository, GameObjectRepository, MonsterRepository
from ..game.auth import AuthService
from ..game.models import Player, Room, GameObject
from .monster import Monster, MonsterType, MonsterBehavior, MonsterStats

logger = logging.getLogger(__name__)


class PlayerManager:
    """플레이어 관련 로직을 총괄하는 관리자 클래스입니다."""

    def __init__(self, player_repo: PlayerRepository) -> None:
        """PlayerManager를 초기화합니다."""
        self._player_repo: PlayerRepository = player_repo
        self._auth_service: AuthService = AuthService(player_repo)

    async def create_account(self, username: str, password: str) -> Player:
        """새로운 플레이어 계정을 생성합니다.

        AuthService를 통해 계정 생성 로직을 위임받아 처리합니다.
        """
        return await self._auth_service.create_account(username, password)

    async def authenticate(self, username: str, password: str) -> Player:
        """사용자를 인증합니다.

        AuthService에 인증 로직을 위임합니다.
        """
        return await self._auth_service.authenticate(username, password)

    async def get_player(self, player_id: str) -> Optional[Player]:
        """플레이어 ID로 플레이어 정보를 가져옵니다."""
        return await self._player_repo.get_by_id(player_id)

    async def save_player(self, player: Player) -> None:
        """플레이어 정보를 저장합니다."""
        await self._player_repo.update(player.id, player.to_dict_with_password())


class WorldManager:
    """게임 세계 관리자 클래스 - 방과 게임 객체를 총괄 관리합니다."""

    def __init__(self, room_repo: RoomRepository, object_repo: GameObjectRepository, monster_repo: MonsterRepository) -> None:
        """WorldManager를 초기화합니다."""
        self._room_repo: RoomRepository = room_repo
        self._object_repo: GameObjectRepository = object_repo
        self._monster_repo: MonsterRepository = monster_repo
        self._spawn_scheduler_task: Optional[asyncio.Task] = None
        self._spawn_points: Dict[str, List[Dict[str, Any]]] = {}  # room_id -> spawn_configs
        self._global_spawn_limits: Dict[str, int] = {}  # template_id -> max_count (글로벌 제한)
        logger.info("WorldManager 초기화 완료")

    # === 방 관리 기능 ===

    async def get_room(self, room_id: str) -> Optional[Room]:
        """방 ID로 방 정보를 조회합니다."""
        try:
            return await self._room_repo.get_by_id(room_id)
        except Exception as e:
            logger.error(f"방 조회 실패 ({room_id}): {e}")
            raise

    async def create_room(self, room_data: Dict[str, Any]) -> Room:
        """새로운 방을 생성합니다.

        Args:
            room_data: 방 생성 데이터
                - id: str - 방 ID
                - name: Dict[str, str] - 다국어 방 이름 {'en': 'name', 'ko': '이름'}
                - description: Dict[str, str] - 다국어 방 설명
                - exits: Dict[str, str] - 출구 정보 {'north': 'room_id'}

        Returns:
            Room: 생성된 방 객체
        """
        try:
            # Room 모델 생성 (유효성 검증 포함)
            room = Room(
                id=room_data.get('id'),
                name=room_data.get('name', {}),
                description=room_data.get('description', {}),
                exits=room_data.get('exits', {}),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

            # 데이터베이스에 저장 (Room 객체를 딕셔너리로 변환)
            created_room = await self._room_repo.create(room.to_dict())
            logger.info(f"새 방 생성됨: {created_room.id}")
            return created_room

        except Exception as e:
            logger.error(f"방 생성 실패: {e}")
            raise

    async def update_room(self, room_id: str, updates: Dict[str, Any]) -> Optional[Room]:
        """기존 방의 정보를 수정합니다.

        Args:
            room_id: 수정할 방 ID
            updates: 수정할 데이터 딕셔너리

        Returns:
            Room: 수정된 방 객체 또는 None (방이 존재하지 않는 경우)
        """
        try:
            # 기존 방 조회
            existing_room = await self.get_room(room_id)
            if not existing_room:
                logger.warning(f"수정하려는 방이 존재하지 않음: {room_id}")
                return None

            # Room 객체에 업데이트 적용
            for key, value in updates.items():
                if hasattr(existing_room, key):
                    if key == 'exits' and isinstance(value, dict):
                        # 출구는 기존 출구와 병합
                        existing_exits = existing_room.exits.copy()
                        existing_exits.update(value)
                        setattr(existing_room, key, existing_exits)
                    else:
                        setattr(existing_room, key, value)

            # 업데이트 시간 설정
            existing_room.updated_at = datetime.now()

            # 데이터베이스 업데이트 (Room 객체를 딕셔너리로 변환)
            updated_room = await self._room_repo.update(room_id, existing_room.to_dict())
            if updated_room:
                logger.info(f"방 정보 수정됨: {room_id}")

            return updated_room

        except Exception as e:
            logger.error(f"방 수정 실패 ({room_id}): {e}")
            raise



    async def delete_room(self, room_id: str) -> bool:
        """방을 삭제합니다.

        Args:
            room_id: 삭제할 방 ID

        Returns:
            bool: 삭제 성공 여부
        """
        try:
            # 방에 있는 객체들을 다른 곳으로 이동 (기본 방으로)
            objects_in_room = await self.get_room_objects(room_id)
            default_room_id = 'town_square'  # 기본 방 ID

            for obj in objects_in_room:
                await self.move_object_to_room(obj.id, default_room_id)
                logger.info(f"객체 {obj.id}를 기본 방으로 이동")

            # 다른 방들의 출구에서 이 방으로의 연결 제거
            await self._remove_exits_to_room(room_id)

            # 방 삭제
            success = await self._room_repo.delete(room_id)
            if success:
                logger.info(f"방 삭제됨: {room_id}")

            return success

        except Exception as e:
            logger.error(f"방 삭제 실패 ({room_id}): {e}")
            raise

    async def get_all_rooms(self) -> List[Room]:
        """모든 방 목록을 조회합니다."""
        try:
            return await self._room_repo.get_all()
        except Exception as e:
            logger.error(f"전체 방 목록 조회 실패: {e}")
            raise

    async def find_rooms_by_name(self, name_pattern: str, locale: str = 'en') -> List[Room]:
        """이름 패턴으로 방을 검색합니다."""
        try:
            return await self._room_repo.find_rooms_by_name(name_pattern, locale)
        except Exception as e:
            logger.error(f"방 이름 검색 실패 ({name_pattern}): {e}")
            raise

    async def get_connected_rooms(self, room_id: str) -> List[Room]:
        """특정 방과 연결된 방들을 조회합니다."""
        try:
            return await self._room_repo.get_connected_rooms(room_id)
        except Exception as e:
            logger.error(f"연결된 방 조회 실패 ({room_id}): {e}")
            raise

    async def add_room_exit(self, room_id: str, direction: str, target_room_id: str) -> bool:
        """방에 새로운 출구를 추가합니다."""
        try:
            room = await self.get_room(room_id)
            if not room:
                return False

            # 대상 방이 존재하는지 확인
            target_room = await self.get_room(target_room_id)
            if not target_room:
                logger.warning(f"대상 방이 존재하지 않음: {target_room_id}")
                return False

            # 출구 추가
            room.add_exit(direction, target_room_id)

            # 데이터베이스 업데이트
            updated_room = await self.update_room(room_id, {
                'exits': room.exits,
                'updated_at': datetime.now()
            })

            success = updated_room is not None
            if success:
                logger.info(f"방 {room_id}에 출구 추가: {direction} -> {target_room_id}")

            return success

        except Exception as e:
            logger.error(f"출구 추가 실패 ({room_id}, {direction}, {target_room_id}): {e}")
            raise

    async def remove_room_exit(self, room_id: str, direction: str) -> bool:
        """방에서 출구를 제거합니다."""
        try:
            room = await self.get_room(room_id)
            if not room:
                return False

            # 출구 제거
            removed = room.remove_exit(direction)
            if not removed:
                return False

            # 데이터베이스 업데이트
            updated_room = await self.update_room(room_id, {
                'exits': room.exits,
                'updated_at': datetime.now()
            })

            success = updated_room is not None
            if success:
                logger.info(f"방 {room_id}에서 출구 제거: {direction}")

            return success

        except Exception as e:
            logger.error(f"출구 제거 실패 ({room_id}, {direction}): {e}")
            raise

    # === 게임 객체 관리 기능 ===

    async def get_game_object(self, object_id: str) -> Optional[GameObject]:
        """게임 객체 ID로 객체 정보를 조회합니다."""
        try:
            return await self._object_repo.get_by_id(object_id)
        except Exception as e:
            logger.error(f"게임 객체 조회 실패 ({object_id}): {e}")
            raise

    async def create_game_object(self, object_data: Dict[str, Any]) -> GameObject:
        """새로운 게임 객체를 생성합니다.

        Args:
            object_data: 객체 생성 데이터
                - name: Dict[str, str] - 다국어 객체 이름
                - description: Dict[str, str] - 다국어 객체 설명
                - object_type: str - 객체 타입 ('item', 'npc', 'furniture' 등)
                - location_type: str - 위치 타입 ('room', 'inventory')
                - location_id: str - 위치 ID
                - properties: Dict[str, Any] - 객체 속성

        Returns:
            GameObject: 생성된 게임 객체
        """
        try:
            # GameObject 모델 생성 (유효성 검증 포함)
            game_object = GameObject(
                id=object_data.get('id'),
                name=object_data.get('name', {}),
                description=object_data.get('description', {}),
                object_type=object_data.get('object_type', 'item'),
                location_type=object_data.get('location_type', 'room'),
                location_id=object_data.get('location_id'),
                properties=object_data.get('properties', {}),
                created_at=datetime.now()
            )

            # 데이터베이스에 저장 (GameObject 객체를 딕셔너리로 변환)
            created_object = await self._object_repo.create(game_object.to_dict())
            logger.info(f"새 게임 객체 생성됨: {created_object.id}")
            return created_object

        except Exception as e:
            logger.error(f"게임 객체 생성 실패: {e}")
            raise

    async def update_game_object(self, object_id: str, updates: Dict[str, Any]) -> Optional[GameObject]:
        """게임 객체 정보를 수정합니다."""
        try:
            # 기존 객체 조회
            existing_object = await self.get_game_object(object_id)
            if not existing_object:
                logger.warning(f"수정하려는 객체가 존재하지 않음: {object_id}")
                return None

            # GameObject 객체에 업데이트 적용
            for key, value in updates.items():
                if hasattr(existing_object, key):
                    setattr(existing_object, key, value)

            # 데이터베이스 업데이트 (GameObject 객체를 딕셔너리로 변환)
            updated_object = await self._object_repo.update(object_id, existing_object.to_dict())
            if updated_object:
                logger.info(f"게임 객체 정보 수정됨: {object_id}")

            return updated_object

        except Exception as e:
            logger.error(f"게임 객체 수정 실패 ({object_id}): {e}")
            raise

    async def delete_game_object(self, object_id: str) -> bool:
        """게임 객체를 삭제합니다."""
        try:
            success = await self._object_repo.delete(object_id)
            if success:
                logger.info(f"게임 객체 삭제됨: {object_id}")

            return success

        except Exception as e:
            logger.error(f"게임 객체 삭제 실패 ({object_id}): {e}")
            raise

    async def get_room_objects(self, room_id: str) -> List[GameObject]:
        """특정 방에 있는 모든 객체를 조회합니다."""
        try:
            return await self._object_repo.get_objects_in_room(room_id)
        except Exception as e:
            logger.error(f"방 내 객체 조회 실패 ({room_id}): {e}")
            raise

    async def get_inventory_objects(self, character_id: str) -> List[GameObject]:
        """특정 캐릭터의 인벤토리 객체들을 조회합니다."""
        try:
            return await self._object_repo.get_objects_in_inventory(character_id)
        except Exception as e:
            logger.error(f"인벤토리 객체 조회 실패 ({character_id}): {e}")
            raise

    async def move_object_to_room(self, object_id: str, room_id: str) -> bool:
        """객체를 특정 방으로 이동시킵니다."""
        try:
            # 대상 방이 존재하는지 확인
            room = await self.get_room(room_id)
            if not room:
                logger.warning(f"대상 방이 존재하지 않음: {room_id}")
                return False

            # 객체 이동
            updated_object = await self._object_repo.move_object_to_room(object_id, room_id)
            success = updated_object is not None

            if success:
                logger.info(f"객체 {object_id}를 방 {room_id}로 이동")

            return success

        except Exception as e:
            logger.error(f"객체 방 이동 실패 ({object_id} -> {room_id}): {e}")
            raise

    async def move_object_to_inventory(self, object_id: str, character_id: str) -> bool:
        """객체를 특정 캐릭터의 인벤토리로 이동시킵니다."""
        try:
            # 객체 이동
            updated_object = await self._object_repo.move_object_to_inventory(object_id, character_id)
            success = updated_object is not None

            if success:
                logger.info(f"객체 {object_id}를 캐릭터 {character_id}의 인벤토리로 이동")

            return success

        except Exception as e:
            logger.error(f"객체 인벤토리 이동 실패 ({object_id} -> {character_id}): {e}")
            raise

    async def find_objects_by_name(self, name_pattern: str, locale: str = 'en') -> List[GameObject]:
        """이름 패턴으로 게임 객체를 검색합니다."""
        try:
            return await self._object_repo.find_objects_by_name(name_pattern, locale)
        except Exception as e:
            logger.error(f"객체 이름 검색 실패 ({name_pattern}): {e}")
            raise

    async def get_objects_by_type(self, object_type: str) -> List[GameObject]:
        """특정 타입의 모든 객체를 조회합니다."""
        try:
            return await self._object_repo.get_objects_by_type(object_type)
        except Exception as e:
            logger.error(f"타입별 객체 조회 실패 ({object_type}): {e}")
            raise

    async def update_object(self, game_object: GameObject) -> bool:
        """게임 객체를 업데이트합니다."""
        try:
            updated_object = await self._object_repo.update(game_object.id, game_object.to_dict())
            if updated_object:
                logger.info(f"게임 객체 업데이트됨: {game_object.id}")
                return True
            return False
        except Exception as e:
            logger.error(f"게임 객체 업데이트 실패 ({game_object.id}): {e}")
            raise

    async def remove_object(self, object_id: str) -> bool:
        """게임 객체를 제거합니다."""
        try:
            success = await self._object_repo.delete(object_id)
            if success:
                logger.info(f"게임 객체 제거됨: {object_id}")
            return success
        except Exception as e:
            logger.error(f"게임 객체 제거 실패 ({object_id}): {e}")
            raise

    async def get_equipped_objects(self, character_id: str) -> List[GameObject]:
        """특정 캐릭터가 착용 중인 장비들을 조회합니다."""
        try:
            inventory_objects = await self.get_inventory_objects(character_id)
            return [obj for obj in inventory_objects if obj.is_equipped]
        except Exception as e:
            logger.error(f"착용 장비 조회 실패 ({character_id}): {e}")
            raise

    async def get_objects_by_category(self, character_id: str, category: str) -> List[GameObject]:
        """특정 캐릭터의 인벤토리에서 카테고리별 객체들을 조회합니다."""
        try:
            inventory_objects = await self.get_inventory_objects(character_id)
            return [obj for obj in inventory_objects if obj.category == category]
        except Exception as e:
            logger.error(f"카테고리별 객체 조회 실패 ({character_id}, {category}): {e}")
            raise

    # === 위치 추적 시스템 ===

    async def track_object_location(self, object_id: str) -> Optional[Dict[str, Any]]:
        """객체의 현재 위치 정보를 추적합니다.

        Returns:
            Dict: 위치 정보
                - object_id: str
                - location_type: str ('room' 또는 'inventory')
                - location_id: str
                - location_name: str (방 이름 또는 캐릭터 이름)
        """
        try:
            obj = await self.get_game_object(object_id)
            if not obj:
                return None

            location_info = {
                'object_id': object_id,
                'location_type': obj.location_type,
                'location_id': obj.location_id,
                'location_name': 'Unknown'
            }

            if obj.location_type == 'room' and obj.location_id:
                room = await self.get_room(obj.location_id)
                if room:
                    location_info['location_name'] = room.get_localized_name('en')
            elif obj.location_type == 'inventory' and obj.location_id:
                # 캐릭터 이름을 가져오려면 CharacterRepository가 필요하지만
                # 순환 참조를 피하기 위해 ID만 표시
                location_info['location_name'] = f"Character {obj.location_id}"

            return location_info

        except Exception as e:
            logger.error(f"객체 위치 추적 실패 ({object_id}): {e}")
            raise

    async def get_location_summary(self, room_id: str, locale: str = 'en') -> Dict[str, Any]:
        """특정 방의 위치 요약 정보를 제공합니다.

        Returns:
            Dict: 위치 요약 정보
                - room: Room 객체
                - objects: List[GameObject] - 방에 있는 객체들
                - monsters: List[Monster] - 방에 있는 몬스터들
                - exits: Dict[str, str] - 출구 정보
                - connected_rooms: List[Room] - 연결된 방들
        """
        try:
            room = await self.get_room(room_id)
            if not room:
                return {}

            objects = await self.get_room_objects(room_id)
            monsters = await self.get_monsters_in_room(room_id)
            connected_rooms = await self.get_connected_rooms(room_id)

            return {
                'room': room,
                'objects': objects,
                'monsters': monsters,
                'exits': room.exits,
                'connected_rooms': connected_rooms
            }

        except Exception as e:
            logger.error(f"위치 요약 정보 조회 실패 ({room_id}): {e}")
            raise

    # === 내부 헬퍼 메서드 ===

    async def _remove_exits_to_room(self, target_room_id: str) -> None:
        """특정 방으로의 모든 출구를 제거합니다 (방 삭제 시 사용)."""
        try:
            rooms_with_exits = await self._room_repo.get_rooms_with_exits_to(target_room_id)

            for room in rooms_with_exits:
                # 해당 방으로의 출구들을 찾아서 제거
                exits_to_remove = []
                for direction, room_id in room.exits.items():
                    if room_id == target_room_id:
                        exits_to_remove.append(direction)

                # 출구 제거
                for direction in exits_to_remove:
                    room.remove_exit(direction)

                # 데이터베이스 업데이트
                await self.update_room(room.id, {
                    'exits': room.exits,
                    'updated_at': datetime.now()
                })

                logger.info(f"방 {room.id}에서 삭제된 방 {target_room_id}로의 출구 제거")

        except Exception as e:
            logger.error(f"방으로의 출구 제거 실패 ({target_room_id}): {e}")
            raise

    # === 실시간 세계 편집 지원 ===

    async def validate_world_integrity(self) -> Dict[str, List[str]]:
        """게임 세계의 무결성을 검증합니다.

        Returns:
            Dict: 검증 결과
                - invalid_exits: List[str] - 잘못된 출구들
                - orphaned_objects: List[str] - 고아 객체들
                - missing_rooms: List[str] - 누락된 방들
        """
        try:
            issues: Dict[str, List[str]] = {
                'invalid_exits': [],
                'orphaned_objects': [],
                'missing_rooms': []
            }

            # 모든 방 조회
            all_rooms = await self.get_all_rooms()
            room_ids = {room.id for room in all_rooms}

            # 잘못된 출구 검사
            for room in all_rooms:
                for direction, target_room_id in room.exits.items():
                    if target_room_id not in room_ids:
                        issues['invalid_exits'].append(f"{room.id}:{direction}->{target_room_id}")

            # 고아 객체 검사
            all_objects = await self._object_repo.get_all()
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
        """게임 세계의 무결성 문제를 자동으로 수정합니다.

        Returns:
            Dict: 수정 결과
                - exits_fixed: int - 수정된 출구 수
                - objects_moved: int - 이동된 객체 수
        """
        try:
            repair_count = {
                'exits_fixed': 0,
                'objects_moved': 0
            }

            # 무결성 검증
            issues = await self.validate_world_integrity()
            default_room_id = 'town_square'  # 기본 방 ID

            # 잘못된 출구 수정
            for invalid_exit in issues['invalid_exits']:
                room_id, direction_target = invalid_exit.split(':', 1)
                direction, _ = direction_target.split('->', 1)

                success = await self.remove_room_exit(room_id, direction)
                if success:
                    repair_count['exits_fixed'] += 1

            # 고아 객체를 기본 방으로 이동
            for object_id in issues['orphaned_objects']:
                success = await self.move_object_to_room(object_id, default_room_id)
                if success:
                    repair_count['objects_moved'] += 1

            logger.info(f"세계 무결성 수정 완료: {repair_count}")
            return repair_count

        except Exception as e:
            logger.error(f"세계 무결성 수정 실패: {e}")
            raise

    # === 몬스터 스폰 시스템 ===

    async def start_spawn_scheduler(self) -> None:
        """몬스터 스폰 스케줄러를 시작합니다."""
        if self._spawn_scheduler_task and not self._spawn_scheduler_task.done():
            logger.warning("스폰 스케줄러가 이미 실행 중입니다")
            return

        logger.info("몬스터 스폰 스케줄러 시작")
        self._spawn_scheduler_task = asyncio.create_task(self._spawn_scheduler_loop())

    async def stop_spawn_scheduler(self) -> None:
        """몬스터 스폰 스케줄러를 중지합니다."""
        if self._spawn_scheduler_task:
            self._spawn_scheduler_task.cancel()
            try:
                await self._spawn_scheduler_task
            except asyncio.CancelledError:
                pass
            logger.info("몬스터 스폰 스케줄러 중지")

    async def _spawn_scheduler_loop(self) -> None:
        """스폰 스케줄러 메인 루프"""
        try:
            while True:
                await self._process_respawns()
                await self._process_initial_spawns()
                await self._process_monster_roaming()
                await asyncio.sleep(30)  # 30초마다 체크
        except asyncio.CancelledError:
            logger.info("스폰 스케줄러 루프 종료")
            raise
        except Exception as e:
            logger.error(f"스폰 스케줄러 오류: {e}")
            # 오류 발생 시 5초 후 재시도
            await asyncio.sleep(5)

    async def _process_respawns(self) -> None:
        """리스폰 대기 중인 몬스터들을 처리합니다."""
        try:
            # 사망한 몬스터들 조회
            dead_monsters = await self._monster_repo.find_by(is_alive=False)

            for monster in dead_monsters:
                if monster.is_ready_to_respawn():
                    await self._respawn_monster(monster)

        except Exception as e:
            logger.error(f"리스폰 처리 실패: {e}")

    async def _process_initial_spawns(self) -> None:
        """초기 스폰이 필요한 방들을 처리합니다."""
        try:
            for room_id, spawn_configs in self._spawn_points.items():
                for spawn_config in spawn_configs:
                    await self._check_and_spawn_monster(room_id, spawn_config)

        except Exception as e:
            logger.error(f"초기 스폰 처리 실패: {e}")

    async def _check_and_spawn_monster(self, room_id: str, spawn_config: Dict[str, Any]) -> None:
        """특정 방에 몬스터 스폰이 필요한지 확인하고 스폰합니다.
        
        주의: 
        1. 방별 초기 스폰 수(max_count)를 초과하지 않도록 제한
        2. 글로벌 최대 수량 제한을 초과하지 않도록 제한
        """
        try:
            monster_template_id = spawn_config.get('monster_template_id')
            max_count = spawn_config.get('max_count', 1)
            spawn_chance = spawn_config.get('spawn_chance', 1.0)

            # 글로벌 제한 확인
            global_limit = self._global_spawn_limits.get(monster_template_id)
            if global_limit is not None:
                # 전체 맵에서 해당 템플릿의 살아있는 몬스터 수 확인
                all_monsters = await self.get_all_monsters()
                global_count = sum(1 for m in all_monsters 
                                 if m.get_property('template_id') == monster_template_id and m.is_alive)
                
                if global_count >= global_limit:
                    logger.debug(f"글로벌 스폰 제한 도달: {monster_template_id} ({global_count}/{global_limit})")
                    return

            # 현재 방에 있는 해당 몬스터 수 확인 (살아있는 것만)
            current_monsters = await self._monster_repo.get_monsters_in_room(room_id)
            template_monsters = [m for m in current_monsters if m.get_property('template_id') == monster_template_id and m.is_alive]

            # 방별 초기 스폰 수보다 작은 경우에만 스폰
            if len(template_monsters) < max_count:
                # 스폰 확률 체크
                import random
                if random.random() <= spawn_chance:
                    await self._spawn_monster_from_template(room_id, monster_template_id)
                    logger.info(f"몬스터 자동 스폰: {room_id}, 현재 {len(template_monsters)+1}/{max_count}")

        except Exception as e:
            logger.error(f"몬스터 스폰 체크 실패 ({room_id}): {e}")

    async def _spawn_monster_from_template(self, room_id: str, template_id: str) -> Optional[Monster]:
        """템플릿을 기반으로 몬스터를 스폰합니다."""
        try:
            # 몬스터 템플릿 조회
            template = await self._monster_repo.get_by_id(template_id)
            if not template:
                logger.error(f"몬스터 템플릿을 찾을 수 없음: {template_id}")
                return None

            # 새 몬스터 인스턴스 생성
            from uuid import uuid4
            new_monster = Monster(
                id=str(uuid4()),
                name=template.name.copy(),
                description=template.description.copy(),
                monster_type=template.monster_type,
                behavior=template.behavior,
                stats=MonsterStats(
                    strength=template.stats.strength,
                    dexterity=template.stats.dexterity,
                    constitution=template.stats.constitution,
                    intelligence=template.stats.intelligence,
                    wisdom=template.stats.wisdom,
                    charisma=template.stats.charisma,
                    level=template.stats.level,
                    current_hp=template.stats.get_max_hp()
                ),
                experience_reward=template.experience_reward,
                gold_reward=template.gold_reward,
                drop_items=template.drop_items.copy(),
                spawn_room_id=room_id,
                current_room_id=room_id,
                respawn_time=template.respawn_time,
                is_alive=True,
                aggro_range=template.aggro_range,
                roaming_range=template.roaming_range,
                properties={'template_id': template_id},
                created_at=datetime.now()
            )

            # 데이터베이스에 저장
            created_monster = await self._monster_repo.create(new_monster.to_dict())
            if created_monster:
                logger.info(f"몬스터 스폰됨: {created_monster.get_localized_name()} (방: {room_id})")
                return created_monster

        except Exception as e:
            logger.error(f"몬스터 스폰 실패 ({template_id} -> {room_id}): {e}")

        return None

    async def _respawn_monster(self, monster: Monster) -> bool:
        """몬스터를 리스폰합니다."""
        try:
            success = await self._monster_repo.respawn_monster(monster.id)
            if success:
                logger.info(f"몬스터 리스폰됨: {monster.get_localized_name()} (방: {monster.spawn_room_id})")
            return success

        except Exception as e:
            logger.error(f"몬스터 리스폰 실패 ({monster.id}): {e}")
            return False

    async def add_spawn_point(self, room_id: str, monster_template_id: str, max_count: int = 1, spawn_chance: float = 1.0) -> None:
        """방에 몬스터 스폰 포인트를 추가합니다."""
        try:
            # 방이 존재하는지 확인
            room = await self.get_room(room_id)
            if not room:
                logger.error(f"스폰 포인트 추가 실패: 방이 존재하지 않음 ({room_id})")
                return

            # 몬스터 템플릿이 존재하는지 확인
            template = await self._monster_repo.get_by_id(monster_template_id)
            if not template:
                logger.error(f"스폰 포인트 추가 실패: 몬스터 템플릿이 존재하지 않음 ({monster_template_id})")
                return

            if room_id not in self._spawn_points:
                self._spawn_points[room_id] = []

            spawn_config = {
                'monster_template_id': monster_template_id,
                'max_count': max_count,
                'spawn_chance': spawn_chance
            }

            self._spawn_points[room_id].append(spawn_config)
            logger.info(f"스폰 포인트 추가됨: {room_id} -> {monster_template_id} (최대 {max_count}마리)")

        except Exception as e:
            logger.error(f"스폰 포인트 추가 실패: {e}")

    async def remove_spawn_point(self, room_id: str, monster_template_id: str) -> bool:
        """방에서 몬스터 스폰 포인트를 제거합니다."""
        try:
            if room_id not in self._spawn_points:
                return False

            original_count = len(self._spawn_points[room_id])
            self._spawn_points[room_id] = [
                config for config in self._spawn_points[room_id]
                if config.get('monster_template_id') != monster_template_id
            ]

            removed = len(self._spawn_points[room_id]) < original_count
            if removed:
                logger.info(f"스폰 포인트 제거됨: {room_id} -> {monster_template_id}")

            # 빈 리스트가 되면 방 자체를 제거
            if not self._spawn_points[room_id]:
                del self._spawn_points[room_id]

            return removed

        except Exception as e:
            logger.error(f"스폰 포인트 제거 실패: {e}")
            return False

    async def get_spawn_points(self) -> Dict[str, List[Dict[str, Any]]]:
        """모든 스폰 포인트 정보를 반환합니다."""
        return self._spawn_points.copy()

    async def get_room_spawn_points(self, room_id: str) -> List[Dict[str, Any]]:
        """특정 방의 스폰 포인트 정보를 반환합니다."""
        return self._spawn_points.get(room_id, []).copy()

    async def clear_spawn_points(self, room_id: Optional[str] = None) -> None:
        """스폰 포인트를 정리합니다."""
        try:
            if room_id:
                if room_id in self._spawn_points:
                    del self._spawn_points[room_id]
                    logger.info(f"방 {room_id}의 스폰 포인트 정리됨")
            else:
                self._spawn_points.clear()
                logger.info("모든 스폰 포인트 정리됨")

        except Exception as e:
            logger.error(f"스폰 포인트 정리 실패: {e}")

    def set_global_spawn_limit(self, template_id: str, max_count: int) -> None:
        """특정 몬스터 템플릿의 글로벌 최대 스폰 수를 설정합니다.
        
        Args:
            template_id: 몬스터 템플릿 ID
            max_count: 전체 맵에서 허용되는 최대 수량
        """
        self._global_spawn_limits[template_id] = max_count
        logger.info(f"글로벌 스폰 제한 설정: {template_id} -> {max_count}마리")

    def get_global_spawn_limit(self, template_id: str) -> Optional[int]:
        """특정 몬스터 템플릿의 글로벌 최대 스폰 수를 조회합니다."""
        return self._global_spawn_limits.get(template_id)

    def get_all_global_spawn_limits(self) -> Dict[str, int]:
        """모든 글로벌 스폰 제한 설정을 반환합니다."""
        return self._global_spawn_limits.copy()

    async def cleanup_excess_monsters(self, template_id: str) -> int:
        """글로벌 제한을 초과하는 몬스터를 DB에서 삭제합니다.
        
        Args:
            template_id: 몬스터 템플릿 ID
            
        Returns:
            int: 삭제된 몬스터 수
        """
        try:
            global_limit = self._global_spawn_limits.get(template_id)
            if global_limit is None:
                logger.warning(f"글로벌 제한이 설정되지 않음: {template_id}")
                return 0

            # 해당 템플릿의 모든 몬스터 조회 (살아있는 것만)
            all_monsters = await self.get_all_monsters()
            template_monsters = [m for m in all_monsters 
                               if m.get_property('template_id') == template_id and m.is_alive]

            # 초과 수량 계산
            excess_count = len(template_monsters) - global_limit
            if excess_count <= 0:
                logger.info(f"초과 몬스터 없음: {template_id} ({len(template_monsters)}/{global_limit})")
                return 0

            # 오래된 몬스터부터 삭제 (created_at 기준)
            template_monsters.sort(key=lambda m: m.created_at)
            monsters_to_delete = template_monsters[:excess_count]

            deleted_count = 0
            for monster in monsters_to_delete:
                success = await self.delete_monster(monster.id)
                if success:
                    deleted_count += 1
                    logger.info(f"초과 몬스터 삭제: {monster.id} ({monster.get_localized_name('ko')})")

            logger.info(f"초과 몬스터 정리 완료: {template_id} - {deleted_count}마리 삭제")
            return deleted_count

        except Exception as e:
            logger.error(f"초과 몬스터 정리 실패 ({template_id}): {e}")
            return 0

    async def cleanup_all_excess_monsters(self) -> Dict[str, int]:
        """모든 템플릿에 대해 글로벌 제한을 초과하는 몬스터를 정리합니다.
        
        Returns:
            Dict[str, int]: 템플릿별 삭제된 몬스터 수
        """
        try:
            result = {}
            for template_id in self._global_spawn_limits.keys():
                deleted_count = await self.cleanup_excess_monsters(template_id)
                if deleted_count > 0:
                    result[template_id] = deleted_count

            logger.info(f"전체 초과 몬스터 정리 완료: {result}")
            return result

        except Exception as e:
            logger.error(f"전체 초과 몬스터 정리 실패: {e}")
            return {}

    async def get_monsters_in_room(self, room_id: str) -> List[Monster]:
        """특정 방에 있는 모든 살아있는 몬스터를 조회합니다."""
        try:
            all_monsters = await self._monster_repo.get_monsters_in_room(room_id)
            # 살아있는 몬스터만 반환
            return [monster for monster in all_monsters if monster.is_alive]
        except Exception as e:
            logger.error(f"방 내 몬스터 조회 실패 ({room_id}): {e}")
            return []

    async def kill_monster(self, monster_id: str) -> bool:
        """몬스터를 사망 처리합니다."""
        try:
            return await self._monster_repo.kill_monster(monster_id)
        except Exception as e:
            logger.error(f"몬스터 사망 처리 실패 ({monster_id}): {e}")
            return False

    async def setup_default_spawn_points(self) -> None:
        """기본 스폰 포인트들을 설정합니다."""
        try:
            # 작은 쥐 템플릿 확인
            small_rat_template = await self._monster_repo.get_by_id('template_small_rat')
            if not small_rat_template:
                logger.info("작은 쥐 템플릿이 없습니다. 스폰 포인트 설정을 건너뜁니다.")
                return

            # 평원 방들 찾기
            all_rooms = await self._room_repo.get_all()
            plains_rooms = []
            for room in all_rooms:
                name_ko = room.name.get('ko', '')
                if '평원' in name_ko and room.x is not None and room.y is not None:
                    # 북쪽 평원 (y >= -2)만 선택
                    if room.y >= -2:
                        plains_rooms.append(room)

            if not plains_rooms:
                logger.info("평원 방을 찾을 수 없습니다.")
                return

            # 각 평원 방에 스폰 포인트 설정
            spawn_count = 0
            for room in plains_rooms[:10]:  # 최대 10개 방에만 설정
                await self.add_spawn_point(
                    room_id=room.id,
                    monster_template_id='template_small_rat',
                    max_count=5,
                    spawn_chance=0.5
                )
                spawn_count += 1

            logger.info(f"작은 쥐 스폰 포인트 {spawn_count}개 설정 완료")

        except Exception as e:
            logger.error(f"기본 스폰 포인트 설정 실패: {e}")

    # === 선공 시스템 ===

    async def check_aggressive_monsters(self, player_id: str, room_id: str, combat_system) -> Optional['Monster']:
        """방에 입장한 플레이어에 대해 선공형 몬스터의 자동 공격을 확인합니다."""
        try:
            # 이미 전투 중인 플레이어는 제외
            if combat_system.is_in_combat(player_id):
                return None

            # 방에 있는 살아있는 몬스터들 조회
            monsters = await self.get_monsters_in_room(room_id)

            for monster in monsters:
                # 선공형 몬스터만 확인
                if monster.monster_type != MonsterType.AGGRESSIVE:
                    continue

                # 이미 다른 플레이어와 전투 중인 몬스터는 제외
                if self._is_monster_in_combat(monster.id, combat_system):
                    continue

                # 어그로 범위 내에 있는지 확인 (현재는 같은 방이면 어그로)
                if monster.current_room_id == room_id:
                    logger.info(f"선공형 몬스터 {monster.get_localized_name('ko')}가 플레이어 {player_id}를 공격합니다")

                    # 플레이어 정보 조회 필요 - 이는 호출하는 쪽에서 처리하도록 콜백으로 전달
                    # 여기서는 몬스터 ID만 반환하고 실제 전투 시작은 상위에서 처리
                    return monster

            return None

        except Exception as e:
            logger.error(f"선공형 몬스터 확인 실패: {e}")
            return None

    def _is_monster_in_combat(self, monster_id: str, combat_system) -> bool:
        """몬스터가 현재 전투 중인지 확인합니다."""
        try:
            for combat in combat_system.active_combats.values():
                if combat.monster.id == monster_id:
                    return True
            return False
        except Exception as e:
            logger.error(f"몬스터 전투 상태 확인 실패: {e}")
            return False

    # === 몬스터 관리 기능 ===

    async def get_monster(self, monster_id: str) -> Optional[Monster]:
        """몬스터 ID로 몬스터 정보를 조회합니다."""
        try:
            return await self._monster_repo.get_by_id(monster_id)
        except Exception as e:
            logger.error(f"몬스터 조회 실패 ({monster_id}): {e}")
            raise



    async def get_all_monsters(self) -> List[Monster]:
        """모든 몬스터를 조회합니다."""
        try:
            return await self._monster_repo.get_all()
        except Exception as e:
            logger.error(f"전체 몬스터 조회 실패: {e}")
            raise

    async def create_monster(self, monster_data: Dict[str, Any]) -> Monster:
        """새로운 몬스터를 생성합니다."""
        try:
            # Monster 모델 생성 (유효성 검증 포함)
            monster = Monster(
                id=monster_data.get('id'),
                name=monster_data.get('name', {}),
                description=monster_data.get('description', {}),
                monster_type=monster_data.get('monster_type', MonsterType.PASSIVE),
                behavior=monster_data.get('behavior', MonsterBehavior.STATIONARY),
                stats=monster_data.get('stats', MonsterStats()),
                experience_reward=monster_data.get('experience_reward', 50),
                gold_reward=monster_data.get('gold_reward', 10),
                drop_items=monster_data.get('drop_items', []),
                spawn_room_id=monster_data.get('spawn_room_id'),
                current_room_id=monster_data.get('current_room_id'),
                respawn_time=monster_data.get('respawn_time', 300),
                aggro_range=monster_data.get('aggro_range', 1),
                roaming_range=monster_data.get('roaming_range', 2),
                properties=monster_data.get('properties', {})
            )

            # 데이터베이스에 저장
            created_monster = await self._monster_repo.create(monster.to_dict())
            logger.info(f"새 몬스터 생성됨: {created_monster.id}")
            return created_monster

        except Exception as e:
            logger.error(f"몬스터 생성 실패: {e}")
            raise

    async def update_monster(self, monster: Monster) -> bool:
        """몬스터 정보를 업데이트합니다."""
        try:
            updated_monster = await self._monster_repo.update(monster.id, monster.to_dict())
            if updated_monster:
                logger.debug(f"몬스터 업데이트됨: {monster.id}")
                return True
            return False
        except Exception as e:
            logger.error(f"몬스터 업데이트 실패 ({monster.id}): {e}")
            raise

    async def delete_monster(self, monster_id: str) -> bool:
        """몬스터를 삭제합니다."""
        try:
            success = await self._monster_repo.delete(monster_id)
            if success:
                logger.info(f"몬스터 삭제됨: {monster_id}")
            return success
        except Exception as e:
            logger.error(f"몬스터 삭제 실패 ({monster_id}): {e}")
            raise

    async def move_monster_to_room(self, monster_id: str, room_id: str) -> bool:
        """몬스터를 특정 방으로 이동시킵니다."""
        try:
            # 대상 방이 존재하는지 확인
            room = await self.get_room(room_id)
            if not room:
                logger.warning(f"대상 방이 존재하지 않음: {room_id}")
                return False

            # 몬스터 조회
            monster = await self.get_monster(monster_id)
            if not monster:
                logger.warning(f"몬스터가 존재하지 않음: {monster_id}")
                return False

            # 몬스터 위치 업데이트
            monster.current_room_id = room_id
            success = await self.update_monster(monster)

            if success:
                short_id = monster_id.split('-')[-1] if '-' in monster_id else monster_id
                logger.info(f"몬스터 {short_id} 방 {room_id} 이동")

            return success

        except Exception as e:
            short_id = monster_id.split('-')[-1] if '-' in monster_id else monster_id
            logger.error(f"몬스터 방 이동 실패 ({short_id} -> {room_id}): {e}")
            raise

    async def find_monsters_by_name(self, name_pattern: str, locale: str = 'ko') -> List[Monster]:
        """이름 패턴으로 몬스터를 검색합니다."""
        try:
            all_monsters = await self.get_all_monsters()
            matching_monsters = []

            for monster in all_monsters:
                if not monster.is_alive:
                    continue

                monster_name = monster.get_localized_name(locale).lower()
                if name_pattern.lower() in monster_name:
                    matching_monsters.append(monster)

            return matching_monsters
        except Exception as e:
            logger.error(f"몬스터 이름 검색 실패 ({name_pattern}): {e}")
            raise

    # === 몬스터 로밍 시스템 ===

    async def _process_monster_roaming(self) -> None:
        """로밍 가능한 몬스터들의 이동을 처리합니다."""
        try:
            # 모든 살아있는 몬스터 조회
            all_monsters = await self.get_all_monsters()
            alive_monsters = [m for m in all_monsters if m.is_alive]

            for monster in alive_monsters:
                # 로밍 가능한 몬스터만 처리
                if not monster.can_roam():
                    continue

                # 로밍 설정 확인
                roaming_config = monster.get_property('roaming_config')
                if not roaming_config:
                    continue

                # 로밍 확률 체크
                roam_chance = roaming_config.get('roam_chance', 0.5)
                import random
                if random.random() > roam_chance:
                    continue

                # 로밍 범위 내에서 이동 가능한 방 찾기
                await self._roam_monster(monster, roaming_config)

        except Exception as e:
            logger.error(f"몬스터 로밍 처리 실패: {e}")

    async def _roam_monster(self, monster: Monster, roaming_config: Dict[str, Any]) -> None:
        """몬스터를 로밍 범위 내에서 이동시킵니다."""
        try:
            if not monster.current_room_id:
                return

            # 현재 방 정보 조회
            current_room = await self.get_room(monster.current_room_id)
            if not current_room:
                return

            # 로밍 범위 확인
            roaming_area = roaming_config.get('roaming_area', {})
            min_x = roaming_area.get('min_x')
            max_x = roaming_area.get('max_x')
            min_y = roaming_area.get('min_y')
            max_y = roaming_area.get('max_y')

            # 좌표가 없으면 로밍 불가
            if current_room.x is None or current_room.y is None:
                return

            # 이동 가능한 출구 찾기
            available_exits = []
            for direction, target_room_id in current_room.exits.items():
                target_room = await self.get_room(target_room_id)
                if not target_room or target_room.x is None or target_room.y is None:
                    continue

                # 로밍 범위 내에 있는지 확인
                if min_x is not None and target_room.x < min_x:
                    continue
                if max_x is not None and target_room.x > max_x:
                    continue
                if min_y is not None and target_room.y < min_y:
                    continue
                if max_y is not None and target_room.y > max_y:
                    continue

                available_exits.append((direction, target_room_id))

            # 이동 가능한 출구가 없으면 종료
            if not available_exits:
                return

            # 랜덤하게 출구 선택
            import random
            _, target_room_id = random.choice(available_exits)

            # 몬스터 이동
            success = await self.move_monster_to_room(monster.id, target_room_id)
            if success:
                logger.debug(f"몬스터 {monster.get_localized_name('ko')}가 {target_room_id}로 이동")

        except Exception as e:
            logger.error(f"몬스터 로밍 실패 ({monster.id}): {e}")
