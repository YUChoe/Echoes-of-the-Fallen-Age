"""
다이얼로그 매니저 - 대화창 관리
- 대화
- 퀘스트
- 상점
"""

import logging
from collections import OrderedDict
from typing import Any

from ..lua_script_loader import LuaScriptLoader
from ..monster import Monster
from ..models import Player
from ...core.localization import get_localization_manager
from ...game.dialogue import DialogueInstance

logger = logging.getLogger(__name__)
I18N = get_localization_manager()


class DialogueManager:
    def __init__(self, session_manager: Any = None) -> None:
        self.session_manager = session_manager
        self.dialogue_instances: dict[str, DialogueInstance] = {}
        self.lua_loader: LuaScriptLoader = LuaScriptLoader()
        logger.info("DialogueManager 초기화")

    def create_dialogue(self, session: Any) -> DialogueInstance:
        dlg = DialogueInstance()
        dlg.session = session
        dlg.lua_loader = self.lua_loader
        self.dialogue_instances[dlg.id] = dlg  # append
        logger.info(f"새 대화 인스턴스 {dlg.id} session.id[{session.session_id}]")
        return dlg

    def get_dialogue_instance(self, dialogue_id: str) -> DialogueInstance | None:
        return self.dialogue_instances.get(dialogue_id)

    # def get_dialogue_by_player
    # def get_dialogue_by_interlocutor

    async def end_dialogue(self, dialogue_id: str) -> None:
        logger.info(f"end_dialogue invoked dlg.id[{dialogue_id}]")
        dlg = self.dialogue_instances.get(dialogue_id)
        session = dlg.session
        locale = session.locale
        await session.send_message({"type":"dialogue", "message": I18N.get_message("npc.talk.finished", locale)})

        session.current_room_id = session.original_room_id
        session.in_dialogue = False
        session.original_room_id = None
        session.dialogue_id = None
        self.dialogue_instances.pop(dialogue_id, None)

    async def send_dialogue_message(
        self,
        dialogue_instance: DialogueInstance,
        msg: list[dict[str, str]] | list[str],
    ) -> None:
        """대화 메시지를 세션에 전송한다.

        Args:
            dialogue_instance: 대화 인스턴스
            msg: 다국어 dict 리스트 또는 기존 str 리스트
        """
        logger.info(f"send_dialogue_message msg={msg}")

        session = dialogue_instance.session
        logger.info(f"session.id[{session.session_id}]")
        locale: str = session.locale
        npc_name: str = dialogue_instance.interlocutor.get_localized_name(locale)

        # '...' 폴백 처리 (Lua 스크립트 없는 NPC)  # TODO: 직접 bye 를
        if "..." in msg:
            # 아무 말 없이 바라봅니다 + [1] Bye
            choice_entity: OrderedDict[int, str | dict[str, str]] = OrderedDict()
            choice_entity[1] = "Bye."
            logger.info(choice_entity)
            dialogue_instance.choice_entity = choice_entity

            output = (
                I18N.get_message("npc.talk.silent_stare", locale, name=npc_name)
                + "\n"
            )
            for c in choice_entity:
                output += f"[{c}] {choice_entity[c]}\n"
            logger.info(output)
            await session.send_message({"type": "dialogue", "message": output})
            return

        # Lua 스크립트 결과 처리 (다국어 dict 리스트)
        # dialogue_texts에서 locale 기반 텍스트 선택
        text_lines: list[str] = []
        for item in msg:
            if isinstance(item, dict):
                text_lines.append(item.get(locale, item.get("en", "")))
            else:
                text_lines.append(str(item))

        # 자동 Bye 선택지 추가
        choice_entity_raw = dialogue_instance.choice_entity
        if choice_entity_raw:
            max_key = max(choice_entity_raw.keys())
        else:
            max_key = 0
        bye_key = max_key + 1
        choice_entity_raw[bye_key] = {"en": "Bye.", "ko": "안녕히."}
        dialogue_instance.choice_entity = choice_entity_raw

        # 출력 메시지 조립
        output = f"{npc_name}: " + " ".join(text_lines) + "\n"
        for c in choice_entity_raw:
            val = choice_entity_raw[c]
            if isinstance(val, dict):
                display_text = val.get(locale, val.get("en", ""))
            else:
                display_text = str(val)
            output += f"[{c}] {display_text}\n"

        logger.info(f"send_dialogue_message output={output}")
        await session.send_message({"type": "dialogue", "message": output})

