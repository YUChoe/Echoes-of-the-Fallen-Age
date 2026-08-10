"""
다이얼로그 매니저 - 대화창 관리
- 대화
- 퀘스트
- 상점
"""

import logging
from typing import Any, TYPE_CHECKING

from ..lua_script_loader import LuaScriptLoader
from ..monster import Monster
from ..models import Player
from ...game.dialogue import DialogueInstance
from .currency_manager import CurrencyManager
from .exchange_manager import ExchangeManager

if TYPE_CHECKING:
    from ..game_object_repository import GameObjectRepository
    from ..player_repository import PlayerRepository

logger = logging.getLogger(__name__)


class DialogueManager:
    def __init__(self, game_engine: Any = None) -> None:
        self.game_engine = game_engine
        self.dialogue_instances: dict[str, DialogueInstance] = {}
        self.lua_loader: LuaScriptLoader = LuaScriptLoader()

        # 교환 시스템 의존성 초기화
        self.currency_manager: CurrencyManager | None = None
        self.exchange_manager: ExchangeManager | None = None
        self._object_repo: GameObjectRepository | None = None

        if game_engine is not None:
            self._init_exchange_system(game_engine)

        logger.info("DialogueManager 초기화")

    def _init_exchange_system(self, game_engine: Any) -> None:
        """GameEngine에서 교환 시스템 의존성을 주입받아 초기화.

        CurrencyManager, ExchangeManager를 생성하고
        LuaScriptLoader에 Exchange API를 등록한다.
        """
        try:
            object_repo = game_engine.world_manager._object_manager._object_repo
            player_repo = game_engine.player_manager._player_repo
            self._object_repo = object_repo

            self.currency_manager = CurrencyManager(object_repo)
            self.exchange_manager = ExchangeManager(
                currency_manager=self.currency_manager,
                object_repo=object_repo,
                player_repo=player_repo,
            )
            self.lua_loader.register_exchange_api(self.exchange_manager)

            # MonsterManager에도 CurrencyManager 전달 (NPC 스폰 시 초기 실버 생성용)
            if hasattr(game_engine, 'world_manager') and game_engine.world_manager:
                game_engine.world_manager._monster_manager.set_currency_manager(self.currency_manager)

            logger.info("교환 시스템 초기화 완료 (CurrencyManager, ExchangeManager, Exchange API)")
        except Exception as e:
            logger.error(f"교환 시스템 초기화 실패: {e}", exc_info=True)

    def create_dialogue(self, session: Any) -> DialogueInstance:
        dlg = DialogueInstance()
        dlg.session = session
        dlg.lua_loader = self.lua_loader
        # 교환 시스템 참조 전달
        dlg.currency_manager = self.currency_manager
        dlg.object_repo = self._object_repo
        self.dialogue_instances[dlg.id] = dlg
        logger.info(f"새 대화 인스턴스 {dlg.id} session.id[{session.session_id}]")
        return dlg

    def get_dialogue_instance(self, dialogue_id: str) -> DialogueInstance | None:
        return self.dialogue_instances.get(dialogue_id)

    # def get_dialogue_by_player
    # def get_dialogue_by_interlocutor

    async def end_dialogue(self, dialogue_id: str) -> None:
        """대화를 종료하고 세션 상태를 되돌린다.

        종료 통보를 보내지 않는다. 계약은 `is_active: false` 인 `dialogue`
        메시지로 종료를 표현하므로 호출부가 그 메시지를 보낸다.
        """
        logger.info(f"end_dialogue invoked dlg.id[{dialogue_id}]")
        dlg = self.dialogue_instances.get(dialogue_id)

        if dlg is None:
            logger.warning(f"종료할 대화를 찾을 수 없다: {dialogue_id}")
            return

        session = dlg.session
        if session is not None:
            session.current_room_id = session.original_room_id
            session.in_dialogue = False
            session.original_room_id = None
            session.dialogue_id = None

        self.dialogue_instances.pop(dialogue_id, None)
