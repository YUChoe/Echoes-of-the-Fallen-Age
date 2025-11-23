#!/usr/bin/env python3
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.mud_engine.database.connection import DatabaseManager
from src.mud_engine.game.repositories import PlayerRepository

async def check():
    db = DatabaseManager()
    await db.initialize()
    repo = PlayerRepository(db)
    players = await repo.get_all()
    print(f'총 플레이어 수: {len(players)}')
    for p in players[:10]:
        print(f'- {p.username} (관리자: {p.is_admin})')
    await db.close()

asyncio.run(check())
