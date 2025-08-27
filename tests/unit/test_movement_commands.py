# -*- coding: utf-8 -*-
"""이동 명령어 단위 테스트"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.mud_engine.commands.basic_commands import MoveCommand, GoCommand, ExitsCommand
from src.mud_engine.game.models import Room, Player
from src.mud_engine.server.session import Session


class TestMovementCommands:
    """이동 명령어 테스트 클래스"""

    @pytest.fixture
    def mock_session(self):
        """모의 세션 객체"""
        session = MagicMock(spec=Session)
        session.is_authenticated = True
        session.player = Player(
            id="player_001",
            username="testuser",
            password_hash="hash",
            preferred_locale="ko"
        )
        session.current_room_id = "room_001"
        session.locale = "ko"

        # 모의 게임 엔진
        mock_game_engine = AsyncMock()
        session.game_engine = mock_game_engine

        return session

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
    def target_room(self):
        """이동 목적지 방"""
        return Room(
            id="room_002",
            name={"en": "Target Room", "ko": "목적지 방"},
            description={"en": "Target room", "ko": "목적지 방입니다"},
            exits={"south": "room_001"},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    @pytest.mark.asyncio
    async def test_move_command_success(self, mock_session, sample_room, target_room):
        """이동 명령어 성공 테스트"""
        # Given
        move_command = MoveCommand("north", ["n"])

        # 게임 엔진 모의 설정
        mock_session.game_engine.world_manager.get_room.side_effect = [sample_room, target_room]
        mock_session.game_engine.move_player_to_room.return_value = True

        # When
        result = await move_command.execute(mock_session, [])

        # Then
        assert result.result_type.value == "success"
        assert "north 방향으로 이동했습니다" in result.message
        assert result.data["action"] == "move"
        assert result.data["direction"] == "north"
        assert result.data["to_room"] == "room_002"

    @pytest.mark.asyncio
    async def test_move_command_no_exit(self, mock_session, sample_room):
        """출구가 없는 방향으로 이동 시도 테스트"""
        # Given
        move_command = MoveCommand("west", ["w"])
        mock_session.game_engine.world_manager.get_room.return_value = sample_room

        # When
        result = await move_command.execute(mock_session, [])

        # Then
        assert result.result_type.value == "error"
        assert "west 방향으로는 갈 수 없습니다" in result.message

    @pytest.mark.asyncio
    async def test_move_command_room_not_found(self, mock_session):
        """현재 방을 찾을 수 없는 경우 테스트"""
        # Given
        move_command = MoveCommand("north", ["n"])
        mock_session.game_engine.world_manager.get_room.return_value = None

        # When
        result = await move_command.execute(mock_session, [])

        # Then
        assert result.result_type.value == "error"
        assert "현재 방을 찾을 수 없습니다" in result.message

    @pytest.mark.asyncio
    async def test_go_command_success(self, mock_session, sample_room, target_room):
        """go 명령어 성공 테스트"""
        # Given
        go_command = GoCommand()
        mock_session.game_engine.world_manager.get_room.side_effect = [sample_room, target_room]
        mock_session.game_engine.move_player_to_room.return_value = True

        # When
        result = await go_command.execute(mock_session, ["north"])

        # Then
        assert result.result_type.value == "success"
        assert "north 방향으로 이동했습니다" in result.message

    @pytest.mark.asyncio
    async def test_go_command_invalid_direction(self, mock_session):
        """go 명령어 잘못된 방향 테스트"""
        # Given
        go_command = GoCommand()

        # When
        result = await go_command.execute(mock_session, ["invalid"])

        # Then
        assert result.result_type.value == "error"
        assert "올바른 방향이 아닙니다" in result.message

    @pytest.mark.asyncio
    async def test_go_command_no_args(self, mock_session):
        """go 명령어 인수 없음 테스트"""
        # Given
        go_command = GoCommand()

        # When
        result = await go_command.execute(mock_session, [])

        # Then
        assert result.result_type.value == "error"
        assert "이동할 방향을 지정해주세요" in result.message

    @pytest.mark.asyncio
    async def test_go_command_direction_aliases(self, mock_session, sample_room, target_room):
        """go 명령어 방향 축약형 테스트"""
        # Given
        go_command = GoCommand()
        mock_session.game_engine.world_manager.get_room.side_effect = [sample_room, target_room]
        mock_session.game_engine.move_player_to_room.return_value = True

        # When - 축약형 사용
        result = await go_command.execute(mock_session, ["n"])

        # Then
        assert result.result_type.value == "success"
        assert "north 방향으로 이동했습니다" in result.message

    @pytest.mark.asyncio
    async def test_exits_command_success(self, mock_session, sample_room):
        """exits 명령어 성공 테스트"""
        # Given
        exits_command = ExitsCommand()
        mock_session.game_engine.world_manager.get_room.return_value = sample_room

        # When
        result = await exits_command.execute(mock_session, [])

        # Then
        assert result.result_type.value == "success"
        assert "사용 가능한 출구" in result.message
        assert "north" in result.message
        assert "south" in result.message
        assert result.data["action"] == "exits"
        assert set(result.data["exits"]) == {"north", "south"}

    @pytest.mark.asyncio
    async def test_exits_command_no_exits(self, mock_session):
        """exits 명령어 출구 없음 테스트"""
        # Given
        exits_command = ExitsCommand()
        room_no_exits = Room(
            id="room_004",
            name={"en": "Dead End", "ko": "막다른 길"},
            description={"en": "A dead end", "ko": "막다른 길입니다"},
            exits={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_session.game_engine.world_manager.get_room.return_value = room_no_exits

        # When
        result = await exits_command.execute(mock_session, [])

        # Then
        assert result.result_type.value == "info"
        assert "출구가 없습니다" in result.message

    @pytest.mark.asyncio
    async def test_unauthenticated_session(self, mock_session):
        """인증되지 않은 세션 테스트"""
        # Given
        mock_session.is_authenticated = False
        move_command = MoveCommand("north", ["n"])

        # When
        result = await move_command.execute(mock_session, [])

        # Then
        assert result.result_type.value == "error"
        assert "인증되지 않은 사용자입니다" in result.message

    @pytest.mark.asyncio
    async def test_no_current_room(self, mock_session):
        """현재 방 ID가 없는 경우 테스트"""
        # Given
        mock_session.current_room_id = None
        move_command = MoveCommand("north", ["n"])

        # When
        result = await move_command.execute(mock_session, [])

        # Then
        assert result.result_type.value == "error"
        assert "현재 위치를 확인할 수 없습니다" in result.message


if __name__ == "__main__":
    pytest.main([__file__])