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

    def end_dialogue(self, dialogue_is:str) -> bool:
        # TODO
        return False

    async def send_dialogue_message(self, msg:List[str], dialogue_instance: DialogueInstance) -> None:
        logger.info(f"WIP talk messages are {msg}")
        logger.info(dialogue_instance)
        if '...' in msg:  # 설정이 없음. 대화 종료  # TODO: 직접 bye 를
            # send to player: 아무 말 없이 바라봅니다.
            # 선택지
            choice_entity = OrderedDict()
            choice_entity[1] = "Bye."
            logger.info(choice_entity)
            dialogue_instance.choice_entity = choice_entity
            session = dialogue_instance.session
            logger.info(f"session.id[{session.session_id}]")
            msg = ""
            for c in choice_entity.keys():
                msg += f"[{c}] {choice_entity[c]}\n"
            logger.info(msg)
            await session.send_message({"type":"dialogue", "message": msg})

