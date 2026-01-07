"""
게임 로직 모듈

핵심 데이터 모델과 게임 로직을 제공합니다.
"""

from .models.session import Session
from .models.player import Player
from .models.character import Character
from .models.room import Room
from .models.gameobject import GameObject

# from .models.npc import NPC

# repositories.py 파일에서 import (repositories 디렉토리가 아님)
from .repositories import (
    PlayerRepository,
    CharacterRepository,
    RoomRepository,
    GameObjectRepository,
    ModelManager,
)
from .managers import PlayerManager, WorldManager

__all__ = [
    # 모델
    "Player",
    "Character",
    "Room",
    "GameObject",
    "Session",
    # 리포지토리
    "PlayerRepository",
    "CharacterRepository",
    "RoomRepository",
    "GameObjectRepository",
    "ModelManager",
    # 매니저
    "PlayerManager",
    "WorldManager",
]
