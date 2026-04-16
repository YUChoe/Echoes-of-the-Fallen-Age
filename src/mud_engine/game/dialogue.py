import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar, List, TYPE_CHECKING
from uuid import uuid4

from .dialogue_context import DialogueContext
from .monster import Monster
from ..core.localization import get_localization_manager
from .models import Player
from ..core.types import SessionType

if TYPE_CHECKING:
    from .managers.currency_manager import CurrencyManager
    from .game_object_repository import GameObjectRepository

logger = logging.getLogger(__name__)


@dataclass
class DialogueInstance:
    id: str = field(default_factory=lambda: str(uuid4()))
    interlocutor: Monster | None = None
    player: Player | None = None
    session: SessionType | None = None
    is_active: bool = True
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: datetime | None = None
    I18N: ClassVar = get_localization_manager()
    choice_entity: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.lua_loader: Any | None = None
        self.currency_manager: CurrencyManager | None = None
        self.object_repo: GameObjectRepository | None = None

    def is_dialogue_finished(self) -> bool:
        # TODO: player offline
        return self.is_active

    def _has_exchange_config(self) -> bool:
        """NPC에 exchange_config가 있는지 확인"""
        if self.interlocutor is None:
            return False
        props = getattr(self.interlocutor, "properties", None)
        if not isinstance(props, dict):
            return False
        return "exchange_config" in props

    async def _build_context(self) -> dict[str, Any]:
        """대화 컨텍스트를 빌드. exchange_config가 있으면 교환 정보 포함."""
        assert self.player is not None
        assert self.session is not None
        assert self.interlocutor is not None

        if (
            self._has_exchange_config()
            and self.currency_manager is not None
            and self.object_repo is not None
        ):
            return await DialogueContext.build_with_exchange(
                player=self.player,
                session=self.session,
                npc=self.interlocutor,
                dialogue=self,
                currency_manager=self.currency_manager,
                object_repo=self.object_repo,
            )
        return DialogueContext.build(
            player=self.player,
            session=self.session,
            npc=self.interlocutor,
            dialogue=self,
        )

    async def get_new_dialogue(
        self,
    ) -> list[dict[str, str]] | List[str]:
        """해당 session에 있는 NPC 대화 내용 가져오기.

        LuaScriptLoader가 있고 사용 가능하면 Lua 스크립트를 실행하여
        (dialogue_texts, choice_entity) 를 반환한다.
        실패 시 기존 ["..."] 폴백 유지.
        """
        talker = self.interlocutor
        session = self.session

        # Lua 스크립트 로더를 통한 대화 로드 시도
        if (
            self.lua_loader is not None
            and self.lua_loader.is_available()
            and talker is not None
            and session is not None
            and self.player is not None
        ):
            try:
                ctx = await self._build_context()
                result = self.lua_loader.execute_get_dialogue(
                    talker.id, ctx
                )
                if result is not None:
                    dialogue_texts, choice_entity = result
                    self.choice_entity = choice_entity
                    logger.info(
                        f"Lua 대화 로드 성공 npc_id[{talker.id}] "
                        f"texts={len(dialogue_texts)} choices={len(choice_entity)}"
                    )
                    return dialogue_texts
            except Exception as e:
                logger.error(f"Lua 대화 스크립트 실행 실패: {e}")

        # 폴백: 기존 동작
        logger.info(
            f"폴백 대화 사용 npc_id[{talker.id if talker else 'None'}]"
        )
        return ["..."]

    async def get_dialogueby_choice(
        self, choice: int
    ) -> list[dict[str, str]] | List[str]:
        """선택지에 따른 후속 대화 가져오기.

        LuaScriptLoader가 있으면 execute_on_choice를 호출한다.
        on_choice가 nil(None) 반환 시 대화 종료 처리.
        기존 Bye 판별 로직도 하위 호환성을 위해 유지.
        """
        if choice not in self.choice_entity:
            logger.error(
                f"not found choice[{choice}] in {self.choice_entity}"
            )
            return ["..."]

        logger.info(
            f"choice_entity[{choice}]: {self.choice_entity[choice]}"
        )

        # 자동 추가된 Bye 선택지 확인 → on_bye 콜백 호출 후 대화 종료
        choice_val = self.choice_entity[choice]
        is_bye = False
        if isinstance(choice_val, dict) and choice_val.get("en") == "Bye.":
            is_bye = True
        elif choice_val == "Bye.":
            is_bye = True

        if is_bye:
            logger.info("Bye 선택지 선택 → 대화 종료")
            # Lua on_bye 콜백 호출 (선택적)
            if (
                self.lua_loader is not None
                and self.lua_loader.is_available()
                and self.interlocutor is not None
                and self.session is not None
                and self.player is not None
            ):
                try:
                    ctx = await self._build_context()
                    self.lua_loader.execute_on_bye(self.interlocutor.id, ctx)
                except Exception as e:
                    logger.error(f"Lua on_bye 콜백 실행 실패: {e}")
            self.is_active = False
            self.ended_at = datetime.now()
            return []

        talker = self.interlocutor
        session = self.session

        # Lua 스크립트 로더를 통한 선택지 처리 시도
        if (
            self.lua_loader is not None
            and self.lua_loader.is_available()
            and talker is not None
            and session is not None
            and self.player is not None
        ):
            try:
                ctx = await self._build_context()
                result = self.lua_loader.execute_on_choice(
                    talker.id, choice, ctx
                )
                if result is None:
                    # on_choice가 nil 반환 → 대화 종료
                    logger.info(
                        f"on_choice nil 반환 → 대화 종료 npc_id[{talker.id}]"
                    )
                    self.is_active = False
                    self.ended_at = datetime.now()
                    return []

                dialogue_texts, choice_entity = result
                self.choice_entity = choice_entity
                logger.info(
                    f"Lua on_choice 성공 npc_id[{talker.id}] "
                    f"texts={len(dialogue_texts)} choices={len(choice_entity)}"
                )
                return dialogue_texts
            except Exception as e:
                logger.error(f"Lua on_choice 실행 실패: {e}")

        # 기존 Bye 판별 로직 (하위 호환성)
        if self.choice_entity[choice] == 'Bye.':  # TODO: locale
            self.is_active = False
            self.ended_at = datetime.now()
        return []