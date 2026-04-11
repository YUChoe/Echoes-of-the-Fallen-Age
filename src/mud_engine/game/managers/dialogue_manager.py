"""
다이얼로그 매니저 - 대화창 관리
- 대화
- 퀘스트
- 상점
"""

import logging
from typing import Any, Dict, List, OrderedDict

from ..monster import Monster
from ..models import Player
from ...core.localization import get_localization_manager
from ...game.dialogue import DialogueInstance

logger = logging.getLogger(__name__)
I18N = get_localization_manager()

class DialogueManager:
    def __init__(self, session_manager: Any = None):
        self.session_manager = session_manager
        self.dialogue_instances: Dict[str, DialogueInstance] = {}
        logger.info("DialogueManager 초기화 ")

    def create_dialogue(self, session) -> DialogueInstance:
        dlg = DialogueInstance()
        dlg.session = session
        self.dialogue_instances[dlg.id] = dlg  # append
        logger.info(f"새 대화 인스턴스 {dlg.id} session.id[{session.session_id}]")
        return dlg

    def get_dialogue_instance(self, dialogue_id:str) -> DialogueInstance:
        return self.dialogue_instances.get(dialogue_id)

    # def get_dialogue_by_player
    # def get_dialogue_by_interlocutor

    async def end_dialogue(self, dialogue_id:str) -> None:
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

    async def send_dialogue_message(self, dialogue_instance: DialogueInstance, msg:List[str]) -> None:
        logger.info(f"WIP talk messages are {msg}")

        session = dialogue_instance.session
        logger.info(f"session.id[{session.session_id}]")
        locale = session.locale
        npc_name = dialogue_instance.interlocutor.get_localized_name(locale)

        if '...' in msg:  # 설정이 없음. 대화 종료  # TODO: 직접 bye 를
            # send to player: 아무 말 없이 바라봅니다.
            # 선택지
            choice_entity = OrderedDict()
            choice_entity[1] = "Bye."
            logger.info(choice_entity)
            dialogue_instance.choice_entity = choice_entity

            msg = I18N.get_message("npc.talk.silent_stare", locale, name=npc_name) + "\n"
            for c in choice_entity.keys():
                msg += f"[{c}] {choice_entity[c]}\n"
            logger.info(msg)
            await session.send_message({"type":"dialogue", "message": msg})

