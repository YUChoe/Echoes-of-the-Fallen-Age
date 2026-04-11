import logging
import os
import json

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, ClassVar
from uuid import uuid4

from .monster import Monster
from ..core.localization import get_localization_manager
from .models import Player
from ..core.types import SessionType  # 경로 틀렸는데 에러 왜 안나

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

    def is_dialogue_finished(self) -> bool:
        # TODO: player offline
        return self.is_active

    # def get_new_dialogue(self, talker: Monster, session: SessionType) -> List[str]:
    def get_new_dialogue(self) -> List[str]:
        """해당 session에 있는 NPC 대화 내용 가져오기"""
        # TODO: 이걸 properties 에서 가져올게 아니라 외부 파일로 가져와서 온라인 적용 하게 하자
        # 파일은? configs/dialogues/{id}.lua
        talker = self.interlocutor
        session = self.session
        try:
            logger.info(f"talker.id[{talker.id}]")
            file_path = f"{os.path.join('configs', 'dialogues', talker.id)}.lua"
            if not os.path.exists(file_path):
                logging.info(f"not found {file_path}")
                return ["..."]
            logging.info(f"found {file_path}")
            with open(file_path, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
            logger.info(data)
            # WIP
            return ["..."]
        except Exception as e:
            logger.error(f"몬스터 대화 내용 가져오기 실패: {e}")
            return ["..."]

    def get_dialogueby_choice(self, choice:int ) -> List[str]:
        if choice in self.choice_entity.keys():
            logger.info(f'choice_entity[{choice}]: {self.choice_entity[choice]}')
        else:
            logger.error(f"not found choice[{choice}] in {self.choice_entity}")
            return ["..."]
        if self.choice_entity[choice] == 'Bye.':  # TODO: locale
            self.is_active = False
            self.ended_at = datetime.now
        return []