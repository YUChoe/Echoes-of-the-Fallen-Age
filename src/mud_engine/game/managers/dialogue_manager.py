"""
다이얼로그 매니저 - 대화창 관리
- 대화
- 퀘스트
- 상점
"""

import logging
from typing import Any, Dict
from dataclasses import field

from ..monster import Monster
from ..models import Player
from ...core.localization import get_localization_manager
from ...game.dialogue import DialogueInstance

logger = logging.getLogger(__name__)

class DialogueManager:
    def __init__(self, session_manager: Any = None):
        self.session_manager = session_manager
        self.dialogue_instances: Dict[str, DialogueInstance] = field(default_factory=dict)
        logger.info("DialogueManager 초기화 ")

    def create_dialogue(self) -> DialogueInstance:
        dlg = DialogueInstance()
        self.dialogue_instances[dlg.id] = dlg  # append
        logger.info(f"새 대화 인스턴스 {dlg.id}")
        return dlg

    def get_dialogue(self, dialogue_id:str) -> DialogueInstance:
        return self.dialogue_instances.get(dialogue_id)

    # def get_dialogue_by_player
    # def get_dialogue_by_interlocutor

    def end_dialogue(self, dialogue_is:str) -> bool:
        # TODO
        return False