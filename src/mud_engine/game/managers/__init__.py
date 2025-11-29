# -*- coding: utf-8 -*-
"""게임 매니저 모듈

하위 호환성을 위해 기존 import 경로 유지:
    from src.mud_engine.game.managers import PlayerManager, WorldManager
"""

from .player_manager import PlayerManager
from .world_manager import WorldManager

__all__ = ['PlayerManager', 'WorldManager']
