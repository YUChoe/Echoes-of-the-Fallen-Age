# -*- coding: utf-8 -*-
"""AuthService에 대한 단위 테스트"""
import pytest
import re
from unittest.mock import AsyncMock, MagicMock

from src.mud_engine.game.auth import AuthService
from src.mud_engine.game.models import Player
from src.mud_engine.utils.exceptions import AuthenticationError

# PlayerRepository를 모의(mock) 처리합니다.
# 실제 데이터베이스 호출 없이 AuthService의 로직을 테스트하기 위함입니다.
@pytest.fixture
def mock_player_repo() -> MagicMock:
    """모의 PlayerRepository를 생성하는 픽스처"""
    return MagicMock(
        get_by_username=AsyncMock(),
        create=AsyncMock()
    )

@pytest.fixture
def auth_service(mock_player_repo: MagicMock) -> AuthService:
    """테스트용 AuthService 인스턴스를 생성하는 픽스처"""
    return AuthService(mock_player_repo)

@pytest.mark.asyncio
class TestAuthService:
    """AuthService의 비동기 메서드들을 테스트합니다."""

    async def test_create_account_success(self, auth_service: AuthService, mock_player_repo: MagicMock):
        """사용자 이름이 고유할 때 계정 생성이 성공하는지 테스트"""
        mock_player_repo.get_by_username.return_value = None
        
        mock_created_player = Player(id="player1", username="testuser", password_hash="hashed_password")
        mock_player_repo.create.return_value = mock_created_player

        created_player = await auth_service.create_account("testuser", "password123")

        mock_player_repo.get_by_username.assert_called_once_with("testuser")
        mock_player_repo.create.assert_called_once()
        assert created_player.username == "testuser"
        assert created_player.password_hash != "password123"

    async def test_create_account_user_exists(self, auth_service: AuthService, mock_player_repo: MagicMock):
        """사용자 이름이 이미 존재할 때 AuthenticationError를 발생시키는지 테스트"""
        mock_player_repo.get_by_username.return_value = Player(id="player1", username="testuser", password_hash="some_hash")

        error_msg = f"사용자 이름 'testuser'이(가) 이미 존재합니다."
        with pytest.raises(AuthenticationError, match=re.escape(error_msg)):
            await auth_service.create_account("testuser", "password123")

    async def test_authenticate_success(self, auth_service: AuthService, mock_player_repo: MagicMock):
        """올바른 자격 증명으로 인증이 성공하는지 테스트"""
        hashed_password = auth_service.hash_password("password123")
        mock_player = Player(id="player1", username="testuser", password_hash=hashed_password)
        mock_player_repo.get_by_username.return_value = mock_player

        authenticated_player = await auth_service.authenticate("testuser", "password123")

        assert authenticated_player.id == "player1"

    async def test_authenticate_user_not_found(self, auth_service: AuthService, mock_player_repo: MagicMock):
        """사용자가 존재하지 않을 때 인증이 실패하는지 테스트"""
        mock_player_repo.get_by_username.return_value = None

        with pytest.raises(AuthenticationError, match="사용자 이름 또는 비밀번호가 잘못되었습니다."):
            await auth_service.authenticate("nonexistent", "password123")

    async def test_authenticate_wrong_password(self, auth_service: AuthService, mock_player_repo: MagicMock):
        """비밀번호가 틀렸을 때 인증이 실패하는지 테스트"""
        hashed_password = auth_service.hash_password("correct_password")
        mock_player = Player(id="player1", username="testuser", password_hash=hashed_password)
        mock_player_repo.get_by_username.return_value = mock_player

        with pytest.raises(AuthenticationError, match="사용자 이름 또는 비밀번호가 잘못되었습니다."):
            await auth_service.authenticate("testuser", "wrong_password")


def test_password_hashing():
    """비밀번호 해싱 및 검증 기능이 올바르게 작동하는지 테스트"""
    password = "mysecretpassword"
    hashed = AuthService.hash_password(password)

    assert isinstance(hashed, str)
    assert hashed != password
    assert AuthService.verify_password(password, hashed)
    assert not AuthService.verify_password("wrongpassword", hashed)
