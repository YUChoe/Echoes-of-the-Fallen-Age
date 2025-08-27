# -*- coding: utf-8 -*-
"""WorldManager 단위 테스트"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.mud_engine.game.managers import WorldManager
from src.mud_engine.game.models import Room, GameObject
from src.mud_engine.game.repositories import RoomRepository, GameObjectRepository


class TestWorldManager:
    """WorldManager 테스트 클래스"""

    @pytest.fixture
    def mock_room_repo(self):
        """RoomRepository 모의 객체"""
        return AsyncMock(spec=RoomRepository)

    @pytest.fixture
    def mock_object_repo(self):
        """GameObjectRepository 모의 객체"""
        return AsyncMock(spec=GameObjectRepository)

    @pytest.fixture
    def world_manager(self, mock_room_repo, mock_object_repo):
        """WorldManager 인스턴스"""
        return WorldManager(mock_room_repo, mock_object_repo)

    @pytest.fixture
    def sample_room(self):
        """테스트용 샘플 방"""
        return Room(
            id="room_001",
            name={"en": "Test Room", "ko": "테스트 방"},
            description={"en": "A test room", "ko": "테스트용 방입니다"},
            exits={"north": "room_002", "south": "room_003"},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    @pytest.fixture
    def sample_object(self):
        """테스트용 샘플 객체"""
        return GameObject(
            id="obj_001",
            name={"en": "Test Item", "ko": "테스트 아이템"},
            description={"en": "A test item", "ko": "테스트용 아이템입니다"},
            object_type="item",
            location_type="room",
            location_id="room_001",
            properties={"weight": 1.0, "value": 10},
            created_at=datetime.now()
        )

    @pytest.mark.asyncio
    async def test_get_room_success(self, world_manager, mock_room_repo, sample_room):
        """방 조회 성공 테스트"""
        # Given
        mock_room_repo.get_by_id.return_value = sample_room

        # When
        result = await world_manager.get_room("room_001")

        # Then
        assert result == sample_room
        mock_room_repo.get_by_id.assert_called_once_with("room_001")

    @pytest.mark.asyncio
    async def test_get_room_not_found(self, world_manager, mock_room_repo):
        """방 조회 실패 테스트 (방이 존재하지 않음)"""
        # Given
        mock_room_repo.get_by_id.return_value = None

        # When
        result = await world_manager.get_room("nonexistent_room")

        # Then
        assert result is None
        mock_room_repo.get_by_id.assert_called_once_with("nonexistent_room")

    @pytest.mark.asyncio
    async def test_create_room_success(self, world_manager, mock_room_repo, sample_room):
        """방 생성 성공 테스트"""
        # Given
        room_data = {
            "name": {"en": "Test Room", "ko": "테스트 방"},
            "description": {"en": "A test room", "ko": "테스트용 방입니다"},
            "exits": {"north": "room_002"}
        }
        mock_room_repo.create.return_value = sample_room

        # When
        result = await world_manager.create_room(room_data)

        # Then
        assert result == sample_room
        mock_room_repo.create.assert_called_once()

        # 생성된 Room 객체의 속성 확인
        created_room_arg = mock_room_repo.create.call_args[0][0]
        assert created_room_arg.name == room_data["name"]
        assert created_room_arg.description == room_data["description"]
        assert created_room_arg.exits == room_data["exits"]

    @pytest.mark.asyncio
    async def test_update_room_success(self, world_manager, mock_room_repo, sample_room):
        """방 수정 성공 테스트"""
        # Given
        mock_room_repo.get_by_id.return_value = sample_room
        updated_room = Room(**sample_room.__dict__)
        updated_room.name = {"en": "Updated Room", "ko": "수정된 방"}
        mock_room_repo.update.return_value = updated_room

        updates = {"name": {"en": "Updated Room", "ko": "수정된 방"}}

        # When
        result = await world_manager.update_room("room_001", updates)

        # Then
        assert result == updated_room
        mock_room_repo.get_by_id.assert_called_once_with("room_001")
        mock_room_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_room_not_found(self, world_manager, mock_room_repo):
        """방 수정 실패 테스트 (방이 존재하지 않음)"""
        # Given
        mock_room_repo.get_by_id.return_value = None

        # When
        result = await world_manager.update_room("nonexistent_room", {"name": {"en": "New Name"}})

        # Then
        assert result is None
        mock_room_repo.get_by_id.assert_called_once_with("nonexistent_room")
        mock_room_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_room_objects(self, world_manager, mock_object_repo, sample_object):
        """방 내 객체 조회 테스트"""
        # Given
        mock_object_repo.get_objects_in_room.return_value = [sample_object]

        # When
        result = await world_manager.get_room_objects("room_001")

        # Then
        assert result == [sample_object]
        mock_object_repo.get_objects_in_room.assert_called_once_with("room_001")

    @pytest.mark.asyncio
    async def test_create_game_object_success(self, world_manager, mock_object_repo, sample_object):
        """게임 객체 생성 성공 테스트"""
        # Given
        object_data = {
            "name": {"en": "Test Item", "ko": "테스트 아이템"},
            "description": {"en": "A test item", "ko": "테스트용 아이템입니다"},
            "object_type": "item",
            "location_type": "room",
            "location_id": "room_001",
            "properties": {"weight": 1.0}
        }
        mock_object_repo.create.return_value = sample_object

        # When
        result = await world_manager.create_game_object(object_data)

        # Then
        assert result == sample_object
        mock_object_repo.create.assert_called_once()

        # 생성된 GameObject 객체의 속성 확인
        created_object_arg = mock_object_repo.create.call_args[0][0]
        assert created_object_arg.name == object_data["name"]
        assert created_object_arg.object_type == object_data["object_type"]
        assert created_object_arg.location_type == object_data["location_type"]

    @pytest.mark.asyncio
    async def test_move_object_to_room_success(self, world_manager, mock_room_repo, mock_object_repo, sample_room, sample_object):
        """객체 방 이동 성공 테스트"""
        # Given
        mock_room_repo.get_by_id.return_value = sample_room
        moved_object = GameObject(**sample_object.__dict__)
        moved_object.location_type = "room"
        moved_object.location_id = "room_002"
        mock_object_repo.move_object_to_room.return_value = moved_object

        # When
        result = await world_manager.move_object_to_room("obj_001", "room_002")

        # Then
        assert result is True
        mock_room_repo.get_by_id.assert_called_once_with("room_002")
        mock_object_repo.move_object_to_room.assert_called_once_with("obj_001", "room_002")

    @pytest.mark.asyncio
    async def test_move_object_to_room_invalid_room(self, world_manager, mock_room_repo, mock_object_repo):
        """객체 방 이동 실패 테스트 (존재하지 않는 방)"""
        # Given
        mock_room_repo.get_by_id.return_value = None

        # When
        result = await world_manager.move_object_to_room("obj_001", "nonexistent_room")

        # Then
        assert result is False
        mock_room_repo.get_by_id.assert_called_once_with("nonexistent_room")
        mock_object_repo.move_object_to_room.assert_not_called()

    @pytest.mark.asyncio
    async def test_track_object_location_room(self, world_manager, mock_object_repo, mock_room_repo, sample_object, sample_room):
        """객체 위치 추적 테스트 (방에 있는 경우)"""
        # Given
        mock_object_repo.get_by_id.return_value = sample_object
        mock_room_repo.get_by_id.return_value = sample_room

        # When
        result = await world_manager.track_object_location("obj_001")

        # Then
        assert result is not None
        assert result["object_id"] == "obj_001"
        assert result["location_type"] == "room"
        assert result["location_id"] == "room_001"
        assert result["location_name"] == "Test Room"

    @pytest.mark.asyncio
    async def test_track_object_location_inventory(self, world_manager, mock_object_repo, sample_object):
        """객체 위치 추적 테스트 (인벤토리에 있는 경우)"""
        # Given
        inventory_object = GameObject(**sample_object.__dict__)
        inventory_object.location_type = "inventory"
        inventory_object.location_id = "char_001"
        mock_object_repo.get_by_id.return_value = inventory_object

        # When
        result = await world_manager.track_object_location("obj_001")

        # Then
        assert result is not None
        assert result["object_id"] == "obj_001"
        assert result["location_type"] == "inventory"
        assert result["location_id"] == "char_001"
        assert "Character char_001" in result["location_name"]

    @pytest.mark.asyncio
    async def test_get_location_summary(self, world_manager, mock_room_repo, mock_object_repo, sample_room, sample_object):
        """위치 요약 정보 조회 테스트"""
        # Given
        mock_room_repo.get_by_id.return_value = sample_room
        mock_object_repo.get_objects_in_room.return_value = [sample_object]
        mock_room_repo.get_connected_rooms.return_value = []

        # When
        result = await world_manager.get_location_summary("room_001")

        # Then
        assert result is not None
        assert result["room"] == sample_room
        assert result["objects"] == [sample_object]
        assert result["exits"] == sample_room.exits
        assert result["connected_rooms"] == []

    @pytest.mark.asyncio
    async def test_add_room_exit_success(self, world_manager, mock_room_repo, sample_room):
        """방 출구 추가 성공 테스트"""
        # Given
        target_room = Room(
            id="room_004",
            name={"en": "Target Room", "ko": "대상 방"},
            description={"en": "Target room", "ko": "대상 방입니다"},
            exits={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # get_by_id 호출 순서: 첫 번째는 add_room_exit에서, 두 번째는 target_room 확인, 세 번째는 update_room에서
        mock_room_repo.get_by_id.side_effect = [sample_room, target_room, sample_room]

        updated_room = Room(**sample_room.__dict__)
        updated_room.exits["east"] = "room_004"
        mock_room_repo.update.return_value = updated_room

        # When
        result = await world_manager.add_room_exit("room_001", "east", "room_004")

        # Then
        assert result is True
        assert mock_room_repo.get_by_id.call_count == 3
        mock_room_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_world_integrity(self, world_manager, mock_room_repo, mock_object_repo):
        """세계 무결성 검증 테스트"""
        # Given
        # 정상적인 방
        valid_room = Room(
            id="room_001",
            name={"en": "Valid Room", "ko": "정상 방"},
            description={"en": "A valid room", "ko": "정상적인 방"},
            exits={"north": "room_002"},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # 잘못된 출구를 가진 방
        invalid_room = Room(
            id="room_002",
            name={"en": "Invalid Room", "ko": "잘못된 방"},
            description={"en": "Room with invalid exit", "ko": "잘못된 출구를 가진 방"},
            exits={"south": "nonexistent_room"},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # 고아 객체
        orphaned_object = GameObject(
            id="obj_001",
            name={"en": "Orphaned Object", "ko": "고아 객체"},
            description={"en": "An orphaned object", "ko": "고아 객체입니다"},
            object_type="item",
            location_type="room",
            location_id="nonexistent_room",
            properties={},
            created_at=datetime.now()
        )

        mock_room_repo.get_all.return_value = [valid_room, invalid_room]
        mock_object_repo.get_all.return_value = [orphaned_object]

        # When
        result = await world_manager.validate_world_integrity()

        # Then
        assert "invalid_exits" in result
        assert "orphaned_objects" in result
        assert "missing_rooms" in result

        # 잘못된 출구 확인
        assert len(result["invalid_exits"]) == 1
        assert "room_002:south->nonexistent_room" in result["invalid_exits"]

        # 고아 객체 확인
        assert len(result["orphaned_objects"]) == 1
        assert "obj_001" in result["orphaned_objects"]


if __name__ == "__main__":
    pytest.main([__file__])