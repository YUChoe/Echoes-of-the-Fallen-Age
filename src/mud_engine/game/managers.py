# -*- coding: utf-8 -*-
"""게임의 핵심 관리자(Manager) 클래스들을 정의합니다."""
from typing import Optional

from .repositories import PlayerRepository
from ..game.auth import AuthService
from ..game.models import Player


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
