# -*- coding: utf-8 -*-
from ..core.types import SessionType

"""
매 명령 excute 할 때 마다 is_session_available 검사 하는데, 그럼 실행 하는 앞 부분 telnet input 에서 검사 하면 되는거 아녀?

"""

# audit
def is_session_available(session: SessionType) -> bool:
    if not session.is_authenticated or not session.player:
        return False
    return True

def is_game_engine_available(session: SessionType) -> bool:
    if not getattr(session, "game_engine", None):
        return False
    return True

def get_user_locale(session: SessionType) -> str:
    return session.player.preferred_locale if session.player else "en"

def is_in_combat(session):
    return getattr(session, "in_combat", False)

"""

        combat_id = getattr(session, "combat_id", None)
        if not combat_id:
            return self.create_error_result("전투 정보를 찾을 수 없습니다.")

        combat = self.combat_handler.combat_manager.get_combat(combat_id)
        if not combat:
            return self.create_error_result("전투를 찾을 수 없습니다.")
"""