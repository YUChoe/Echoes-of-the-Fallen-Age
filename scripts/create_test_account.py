#!/usr/bin/env python3
"""
테스트 계정 생성 스크립트
"""

import asyncio
import sys
import os
import bcrypt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.mud_engine.database.connection import DatabaseManager
from src.mud_engine.game.repositories import PlayerRepository
from src.mud_engine.game.models import Player
from src.mud_engine.game.stats import PlayerStats

async def create_test_account():
    """테스트 계정 생성"""
    db = DatabaseManager()
    await db.initialize()
    
    try:
        repo = PlayerRepository(db)
        
        # 기존 계정 확인
        existing = await repo.get_by_username('aa')
        if existing:
            print("✓ 테스트 계정 'aa'가 이미 존재합니다")
            print(f"  - 관리자: {existing.is_admin}")
            
            # 전투 테스트에는 관리자 권한 불필요
            
            return True
        
        # 비밀번호 해시 생성
        password = 'aaaabbbb'
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # 플레이어 생성 (일반 사용자)
        player = Player(
            username='aa',
            password_hash=password_hash,
            preferred_locale='ko',
            is_admin=False,  # 전투 테스트에는 관리자 권한 불필요
            stats=PlayerStats()
        )
        
        # 데이터베이스에 저장
        await repo.create(player.to_dict_with_password())
        
        print("✓ 테스트 계정 'aa' 생성 완료")
        print(f"  - 사용자명: aa")
        print(f"  - 비밀번호: {password}")
        print(f"  - 일반 사용자 (전투 테스트용)")
        
        return True
        
    except Exception as e:
        print(f"✗ 계정 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(create_test_account())
