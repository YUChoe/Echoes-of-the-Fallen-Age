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
from ...game.monster import Monster
from ...game.dialogue import DialogueInstance

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

    # 이거 무조건 비동기로 만들어야 하나?
    def get_npc_entity_by_input_digit(self, session: SessionType, target_input) -> Monster:
        if not target_input.isdigit():
            logger.error(f"target_input[{target_input}] is not digit")
            return None

        entity_num = int(target_input)
        logger.info(f"target_input[{target_input}] entity_num[{entity_num}]")

        # if session.in_dialogue:
        #     dialogue_instance: DialogueInstance = self.dialogue_manager.get_dialogue(session.dialogue_id)
        #     entity_map = combat_instances.get_entity_map()
        # else:
        #     entity_map = getattr(session, "room_entity_map", {})

        entity_map = getattr(session, "room_entity_map", {})
        logger.info("entity_map starting")
        for entnum in entity_map:
            entity_info = entity_map[entnum]
            logger.info(f"entity_map[{entnum}]: {entity_info['type']}")
        logger.info("entity_map finished")

        if entity_num in entity_map:
            entity_info = entity_map[entity_num]
            logger.info(f"{target_input}번은 타입이 {entity_info['type']} 입니다.")
        else:
            logger.info("못찾음")
            return None

        target_monster = entity_info["entity"]
        return target_monster

    async def execute(self, session: TelnetSession, args: List[str]) -> CommandResult:
        locale = session.player.preferred_locale if session.player else "en"
        self.session = session

        if not self.validate_args(args, min_args=1):
            error_msg = self.I18N.get_message("say.usage_error", locale)
            return self.create_error_result(error_msg)

        target_input = " ".join(args)
        username = self.session.player.get_display_name() # pyright: ignore[reportOptionalMemberAccess]

        if self.session.in_dialogue:
            # 대화 중
            dlg: DialogueInstance = self.dialogue_manager.get_dialogue_instance(self.session.dialogue_id)
            logger.info(f"대화중 {dlg.id} {target_input}")
            choice = int(target_input)
            logger.info(f'choice[{choice}]')
            result_msgs = await dlg.get_dialogueby_choice(choice)
            if not dlg.is_active:
                # Bye 선택 → 메시지 전송 없이 대화 종료
                await self.dialogue_manager.end_dialogue(dlg.id)
            else:
                await self.dialogue_manager.send_dialogue_message(dlg, result_msgs)
            return self.create_info_result(message="")

        # 대화 생성
        # 1. 인덱스, id로 대상 찾기
        target_npc = self.get_npc_entity_by_input_digit(self.session, target_input)
        if not target_input or not target_npc:
            logger.info(f"NPC 대화 대상을 찾을 수 없습니다.args[{args}] target_input[{target_input}]")
            return self.create_error_result(self.I18N.get_message("combat.target_not_found_usage", locale, usage=self.usage))
        logger.info(f"target_npc.id[{target_npc.id}]")

        # 2. 인스턴스 확인 및 생성. 확인은 필요 없을 꺼 같음. 유지 할 필요 없으니 바로바로 삭제 되도록
        dlg = self.dialogue_manager.create_dialogue(self.session)
        dlg.player = self.session.player
        dlg.interlocutor = target_npc

        # 3. 세션 대화중 업데이트
        self.session.in_dialogue = True
        self.session.original_room_id = self.session.current_room_id  # 바꿔치기
        self.session.dialogue_id = dlg.id
        self.session.current_room_id = f"dialogue_{dlg.id}"  # 인스턴스

        # 플레이어에게 npc의 메시지
        # 1. 메시지는 플레이어의 상태에 따라 다름
        # await self.dialogue_manager.send_dialogue_message(dlg.get_new_dialogue(target_npc, self.session), dlg)
        await self.dialogue_manager.send_dialogue_message(dlg, await dlg.get_new_dialogue())
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
                "message": ""
            },
            broadcast=False
        )

