# -*- coding: utf-8 -*-
"""게임의 핵심 관리자(Manager) 클래스들을 정의합니다."""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .repositories import PlayerRepository, RoomRepository, GameObjectRepository
from ..game.auth import AuthService
from ..game.models import Player, Room, GameObject

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
        await self._player_repo.update(player)


class WorldManager:
    """게임 세계 관리자 클래스 - 방과 게임 객체를 총괄 관리합니다."""

    def __init__(self, room_repo: RoomRepository, object_repo: GameObjectRepository) -> None:
        """WorldManager를 초기화합니다."""
        self._room_repo: RoomRepository = room_repo
        self._object_repo: GameObjectRepository = object_repo
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
            default_room_id = 'room_001'  # 기본 방 ID

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
                - exits: Dict[str, str] - 출구 정보
                - connected_rooms: List[Room] - 연결된 방들
        """
        try:
            room = await self.get_room(room_id)
            if not room:
                return {}

            objects = await self.get_room_objects(room_id)
            connected_rooms = await self.get_connected_rooms(room_id)

            return {
                'room': room,
                'objects': objects,
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
            issues = {
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
            default_room_id = 'room_001'  # 기본 방 ID

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
