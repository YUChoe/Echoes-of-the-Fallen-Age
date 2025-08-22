# -*- coding: utf-8 -*-
"""객체 상호작용 명령어 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.mud_engine.commands.object_commands import (
    GetCommand, DropCommand, InventoryCommand, ExamineCommand
)
from src.mud_engine.commands.base import CommandResultType
from src.mud_engine.server.session import Session
from src.mud_engine.game.models import Player, GameObject


class TestObjectCommands:
    """객체 상호작용 명령어 테스트"""

    @pytest.fixture
    def mock_session(self):
        """모의 세션 객체"""
        session = MagicMock(spec=Session)
        session.is_authenticated = True
        session.locale = 'ko'
        session.current_room_id = 'room_001'

        # 모의 플레이어
        player = MagicMock(spec=Player)
        player.id = 'player_001'
        player.username = 'testuser'
        player.email = 'test@example.com'
        player.preferred_locale = 'ko'
        player.created_at = datetime.now()
        session.player = player

        # 모의 게임 엔진
        game_engine = MagicMock()
        session.game_engine = game_engine

        return session

    @pytest.fixture
    def sample_object(self):
        """샘플 게임 객체"""
        return GameObject(
            id='obj_001',
            name={'en': 'Magic Sword', 'ko': '마법 검'},
            description={'en': 'A shining magic sword', 'ko': '빛나는 마법 검'},
            object_type='weapon',
            location_type='room',
            location_id='room_001',
            properties={'damage': 10, 'magic': True},
            created_at=datetime.now()
        )

    @pytest.fixture
    def inventory_object(self):
        """인벤토리에 있는 객체"""
        return GameObject(
            id='obj_002',
            name={'en': 'Health Potion', 'ko': '체력 물약'},
            description={'en': 'A red healing potion', 'ko': '빨간 치료 물약'},
            object_type='consumable',
            location_type='inventory',
            location_id='player_001',
            properties={'heal': 50},
            created_at=datetime.now()
        )

    # === GetCommand 테스트 ===

    @pytest.mark.asyncio
    async def test_get_command_success(self, mock_session, sample_object):
        """객체 획득 성공 테스트"""
        # 모의 설정 - AsyncMock 사용
        mock_session.game_engine.world_manager.get_room_objects = AsyncMock(return_value=[sample_object])
        mock_session.game_engine.world_manager.move_object_to_inventory = AsyncMock(return_value=True)

        command = GetCommand()
        result = await command.execute(mock_session, ['magic', 'sword'])

        assert result.result_type == CommandResultType.SUCCESS
        assert '마법 검' in result.message
        assert result.broadcast is True
        assert result.room_only is True
        assert result.data['action'] == 'get'
        assert result.data['object_id'] == 'obj_001'

    @pytest.mark.asyncio
    async def test_get_command_no_args(self, mock_session):
        """인수 없이 get 명령어 실행 테스트"""
        command = GetCommand()
        result = await command.execute(mock_session, [])

        assert result.result_type == CommandResultType.ERROR
        assert '획득할 객체를 지정해주세요' in result.message

    @pytest.mark.asyncio
    async def test_get_command_object_not_found(self, mock_session):
        """존재하지 않는 객체 획득 시도 테스트"""
        mock_session.game_engine.world_manager.get_room_objects = AsyncMock(return_value=[])

        command = GetCommand()
        result = await command.execute(mock_session, ['nonexistent'])

        assert result.result_type == CommandResultType.ERROR
        assert 'nonexistent' in result.message
        assert '찾을 수 없습니다' in result.message

    @pytest.mark.asyncio
    async def test_get_command_move_failed(self, mock_session, sample_object):
        """객체 이동 실패 테스트"""
        mock_session.game_engine.world_manager.get_room_objects = AsyncMock(return_value=[sample_object])
        mock_session.game_engine.world_manager.move_object_to_inventory = AsyncMock(return_value=False)

        command = GetCommand()
        result = await command.execute(mock_session, ['magic', 'sword'])

        assert result.result_type == CommandResultType.ERROR
        assert '획득할 수 없습니다' in result.message

    @pytest.mark.asyncio
    async def test_get_command_unauthenticated(self, mock_session):
        """인증되지 않은 사용자 테스트"""
        mock_session.is_authenticated = False

        command = GetCommand()
        result = await command.execute(mock_session, ['sword'])

        assert result.result_type == CommandResultType.ERROR
        assert '인증되지 않은 사용자' in result.message

    # === DropCommand 테스트 ===

    @pytest.mark.asyncio
    async def test_drop_command_success(self, mock_session, inventory_object):
        """객체 버리기 성공 테스트"""
        mock_session.game_engine.world_manager.get_inventory_objects = AsyncMock(return_value=[inventory_object])
        mock_session.game_engine.world_manager.move_object_to_room = AsyncMock(return_value=True)

        command = DropCommand()
        result = await command.execute(mock_session, ['health', 'potion'])

        assert result.result_type == CommandResultType.SUCCESS
        assert '체력 물약' in result.message
        assert result.broadcast is True
        assert result.room_only is True
        assert result.data['action'] == 'drop'
        assert result.data['object_id'] == 'obj_002'

    @pytest.mark.asyncio
    async def test_drop_command_no_args(self, mock_session):
        """인수 없이 drop 명령어 실행 테스트"""
        command = DropCommand()
        result = await command.execute(mock_session, [])

        assert result.result_type == CommandResultType.ERROR
        assert '버릴 객체를 지정해주세요' in result.message

    @pytest.mark.asyncio
    async def test_drop_command_object_not_in_inventory(self, mock_session):
        """인벤토리에 없는 객체 버리기 시도 테스트"""
        mock_session.game_engine.world_manager.get_inventory_objects = AsyncMock(return_value=[])

        command = DropCommand()
        result = await command.execute(mock_session, ['nonexistent'])

        assert result.result_type == CommandResultType.ERROR
        assert 'nonexistent' in result.message
        assert '인벤토리에' in result.message and '없습니다' in result.message

    # === InventoryCommand 테스트 ===

    @pytest.mark.asyncio
    async def test_inventory_command_with_items(self, mock_session, inventory_object):
        """아이템이 있는 인벤토리 확인 테스트"""
        mock_session.game_engine.world_manager.get_inventory_objects = AsyncMock(return_value=[inventory_object])

        command = InventoryCommand()
        result = await command.execute(mock_session, [])

        assert result.result_type == CommandResultType.SUCCESS
        assert 'testuser의 인벤토리' in result.message
        assert '체력 물약' in result.message
        assert '총 1개의 아이템' in result.message
        assert result.data['action'] == 'inventory'
        assert result.data['item_count'] == 1
        assert len(result.data['items']) == 1

    @pytest.mark.asyncio
    async def test_inventory_command_empty(self, mock_session):
        """빈 인벤토리 확인 테스트"""
        mock_session.game_engine.world_manager.get_inventory_objects = AsyncMock(return_value=[])

        command = InventoryCommand()
        result = await command.execute(mock_session, [])

        assert result.result_type == CommandResultType.INFO
        assert '인벤토리가 비어있습니다' in result.message

    # === ExamineCommand 테스트 ===

    @pytest.mark.asyncio
    async def test_examine_command_self(self, mock_session):
        """자기 자신 살펴보기 테스트"""
        command = ExamineCommand()
        result = await command.execute(mock_session, ['me'])

        assert result.result_type == CommandResultType.SUCCESS
        assert 'testuser' in result.message
        assert '모험가입니다' in result.message
        assert result.data['action'] == 'examine'
        assert result.data['target'] == 'self'
        assert result.data['target_type'] == 'player'

    @pytest.mark.asyncio
    async def test_examine_command_object_in_room(self, mock_session, sample_object):
        """방에 있는 객체 살펴보기 테스트"""
        mock_session.game_engine.world_manager.get_room_objects = AsyncMock(return_value=[sample_object])
        mock_session.game_engine.world_manager.get_inventory_objects = AsyncMock(return_value=[])

        command = ExamineCommand()
        result = await command.execute(mock_session, ['magic', 'sword'])

        assert result.result_type == CommandResultType.SUCCESS
        assert '마법 검' in result.message
        assert '빛나는 마법 검' in result.message
        assert 'weapon' in result.message
        assert result.data['action'] == 'examine'
        assert result.data['target_type'] == 'object'
        assert result.data['object_info']['id'] == 'obj_001'

    @pytest.mark.asyncio
    async def test_examine_command_object_in_inventory(self, mock_session, inventory_object):
        """인벤토리에 있는 객체 살펴보기 테스트"""
        mock_session.game_engine.world_manager.get_room_objects = AsyncMock(return_value=[])
        mock_session.game_engine.world_manager.get_inventory_objects = AsyncMock(return_value=[inventory_object])

        command = ExamineCommand()
        result = await command.execute(mock_session, ['health', 'potion'])

        assert result.result_type == CommandResultType.SUCCESS
        assert '체력 물약' in result.message
        assert '빨간 치료 물약' in result.message
        assert 'consumable' in result.message
        assert '인벤토리' in result.message
        assert result.data['object_info']['id'] == 'obj_002'

    @pytest.mark.asyncio
    async def test_examine_command_object_not_found(self, mock_session):
        """존재하지 않는 객체 살펴보기 테스트"""
        mock_session.game_engine.world_manager.get_room_objects = AsyncMock(return_value=[])
        mock_session.game_engine.world_manager.get_inventory_objects = AsyncMock(return_value=[])

        command = ExamineCommand()
        result = await command.execute(mock_session, ['nonexistent'])

        assert result.result_type == CommandResultType.ERROR
        assert 'nonexistent' in result.message
        assert '찾을 수 없습니다' in result.message

    @pytest.mark.asyncio
    async def test_examine_command_no_args(self, mock_session):
        """인수 없이 examine 명령어 실행 테스트"""
        command = ExamineCommand()
        result = await command.execute(mock_session, [])

        assert result.result_type == CommandResultType.ERROR
        assert '살펴볼 대상을 지정해주세요' in result.message

    # === 오류 처리 테스트 ===

    @pytest.mark.asyncio
    async def test_get_command_exception_handling(self, mock_session):
        """get 명령어 예외 처리 테스트"""
        mock_session.game_engine.world_manager.get_room_objects = AsyncMock(side_effect=Exception("Database error"))

        command = GetCommand()
        result = await command.execute(mock_session, ['sword'])

        assert result.result_type == CommandResultType.ERROR
        assert '오류가 발생했습니다' in result.message

    @pytest.mark.asyncio
    async def test_inventory_command_exception_handling(self, mock_session):
        """inventory 명령어 예외 처리 테스트"""
        mock_session.game_engine.world_manager.get_inventory_objects = AsyncMock(side_effect=Exception("Database error"))

        command = InventoryCommand()
        result = await command.execute(mock_session, [])

        assert result.result_type == CommandResultType.ERROR
        assert '오류가 발생했습니다' in result.message

    # === 명령어 별칭 테스트 ===

    def test_get_command_aliases(self):
        """get 명령어 별칭 테스트"""
        command = GetCommand()
        assert command.matches('get')
        assert command.matches('take')
        assert command.matches('pick')
        assert not command.matches('drop')

    def test_drop_command_aliases(self):
        """drop 명령어 별칭 테스트"""
        command = DropCommand()
        assert command.matches('drop')
        assert command.matches('put')
        assert command.matches('place')
        assert not command.matches('get')

    def test_inventory_command_aliases(self):
        """inventory 명령어 별칭 테스트"""
        command = InventoryCommand()
        assert command.matches('inventory')
        assert command.matches('inv')
        assert command.matches('i')
        assert not command.matches('examine')

    def test_examine_command_aliases(self):
        """examine 명령어 별칭 테스트"""
        command = ExamineCommand()
        assert command.matches('examine')
        assert command.matches('exam')
        assert command.matches('inspect')
        assert command.matches('look at')
        assert not command.matches('look')

    # === 다국어 지원 테스트 ===

    @pytest.mark.asyncio
    async def test_get_command_korean_object_name(self, mock_session):
        """한국어 객체 이름으로 획득 테스트"""
        korean_object = GameObject(
            id='obj_003',
            name={'en': 'Iron Shield', 'ko': '철 방패'},
            description={'en': 'A sturdy iron shield', 'ko': '튼튼한 철 방패'},
            object_type='armor',
            location_type='room',
            location_id='room_001',
            properties={'defense': 5},
            created_at=datetime.now()
        )

        mock_session.game_engine.world_manager.get_room_objects = AsyncMock(return_value=[korean_object])
        mock_session.game_engine.world_manager.move_object_to_inventory = AsyncMock(return_value=True)

        command = GetCommand()
        result = await command.execute(mock_session, ['철', '방패'])

        assert result.result_type == CommandResultType.SUCCESS
        assert '철 방패' in result.message

    @pytest.mark.asyncio
    async def test_examine_command_english_locale(self, mock_session, sample_object):
        """영어 로케일로 객체 살펴보기 테스트"""
        mock_session.locale = 'en'
        mock_session.game_engine.world_manager.get_room_objects = AsyncMock(return_value=[sample_object])
        mock_session.game_engine.world_manager.get_inventory_objects = AsyncMock(return_value=[])

        command = ExamineCommand()
        result = await command.execute(mock_session, ['magic', 'sword'])

        assert result.result_type == CommandResultType.SUCCESS
        assert 'Magic Sword' in result.message
        assert 'A shining magic sword' in result.message