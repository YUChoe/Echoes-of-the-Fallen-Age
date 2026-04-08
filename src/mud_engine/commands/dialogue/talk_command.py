# -*- coding: utf-8 -*-
"""다이얼로그 시작 명령어
- 대화
- 퀘스트
- 상점 """

import logging
from typing import List

from ..base import BaseCommand, CommandResult, CommandResultType
from ...core.types import SessionType
from ...core.localization import get_localization_manager
from ...server.telnet_session import TelnetSession
from ...game.managers.dialogue_manager import DialogueManager

logger = logging.getLogger(__name__)

# WIP
class TalkCommand(BaseCommand):

    def __init__(self, dialogue_manager: DialogueManager):
        super().__init__(
            name="talk",
            aliases=[""],
            description="NPC와 대화 합니다.",
            usage="talk <Mob id>"
        )
        self.I18N = get_localization_manager()
        self.dialogue_manager = dialogue_manager

    async def execute(self, session: TelnetSession, args: List[str]) -> CommandResult:
        locale = session.player.preferred_locale if session.player else "en"
        self.session = session

        if not self.validate_args(args, min_args=1):
            error_msg = self.I18N.get_message("say.usage_error", locale)
            return self.create_error_result(error_msg)

        message = " ".join(args)
        username = session.player.get_display_name() # pyright: ignore[reportOptionalMemberAccess]

        # 1. 인덱스, id로 대상 찾기
        # 2. 인스턴스 확인 및 생성. 확인은 필요 없을 꺼 같음. 유지 할 필요 없으니 바로바로 삭제 되도록
        dlg = self.dialogue_manager.create_dialogue()
        dlg.player = self.session.player
        # dlg.interlocutor = TODO: 1번에서 찾은 몹/NPC
        # 3. 세션 대화중 업데이트
        self.session.in_dialogue = True
        self.session.original_room_id = self.session.current_room_id  # 바꿔치기
        self.session.dialogue_id = dlg.id
        self.session.current_room_id = f"dialogue_{dlg.id}"  # 인스턴스
        logger.info(self.session)

        # 플레이어에게 확인 메시지
        # player_message = self.I18N.get_message("say.success", locale, message=message)
        # broadcast_message = self.I18N.get_message("say.broadcast", locale, username=username, message=message)

        # 플레이어에게 npc의 메시지
        # 1. 메시지는 플레이어의 상태에 따라 다름
        """
        [타운가드]
        처음보는 얼굴이군 저쪽으로 가서 안내를 받으라고
        1. 누구신가요?
        2. 여기는 어디죠?
        3. ... 에 대해서 들어 보셨습니다? << 예를 들어 다른데서 조사하라는 퀘스트를 받으면.
        3. 상점
        이런 가변적인 다이얼로그 시스템은 어떻게 만들 수 있을까? ㅜㅜ
        """

        return self.create_success_result(
            message="",
            data={
                "action": "talk",
                "speaker": username,
                "message": message
            },
            broadcast=False
        )
