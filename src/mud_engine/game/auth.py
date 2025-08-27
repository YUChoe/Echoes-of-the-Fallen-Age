# -*- coding: utf-8 -*-
"""플레이어 인증 관련 서비스를 제공합니다."""
import bcrypt
from typing import Optional

from .repositories import PlayerRepository
from ..game.models import Player
from ..utils.exceptions import AuthenticationError


class AuthService:
    """인증 관련 로직을 처리하는 서비스 클래스입니다."""

    def __init__(self, player_repo: PlayerRepository) -> None:
        """AuthService를 초기화합니다."""
        self._player_repo: PlayerRepository = player_repo

    @staticmethod
    def hash_password(password: str) -> str:
        """비밀번호를 해시 처리합니다."""
        salt = bcrypt.gensalt()
        hashed_password: bytes = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed_password.decode('utf-8')

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """입력된 비밀번호와 해시된 비밀번호를 비교합니다."""
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), hashed_password.encode('utf-8')
        )

    async def create_account(self, username: str, password: str) -> Player:
        """새로운 플레이어 계정을 생성합니다.

        Args:
            username: 생성할 사용자 이름
            password: 생성할 계정의 비밀번호

        Returns:
            생성된 Player 객체

        Raises:
            AuthenticationError: 사용자 이름이 이미 존재할 경우
        """
        existing_player: Optional[Player] = await self._player_repo.get_by_username(
            username
        )
        if existing_player:
            raise AuthenticationError(f"사용자 이름 '{username}'이(가) 이미 존재합니다.")

        hashed_password: str = self.hash_password(password)
        player_data = {
            'username': username,
            'password_hash': hashed_password
        }
        new_player: Player = await self._player_repo.create(player_data)
        return new_player

    async def authenticate(self, username: str, password: str) -> Player:
        """사용자를 인증합니다.

        Args:
            username: 인증할 사용자 이름
            password: 비밀번호

        Returns:
            인증된 Player 객체

        Raises:
            AuthenticationError: 인증에 실패한 경우
        """
        player: Optional[Player] = await self._player_repo.get_by_username(username)

        if not player or not self.verify_password(password, player.password_hash):
            raise AuthenticationError("사용자 이름 또는 비밀번호가 잘못되었습니다.")

        return player
