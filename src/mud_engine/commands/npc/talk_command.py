# -*- coding: utf-8 -*-
"""몬스터와 대화하는 명령어"""

import logging
import warnings
from datetime import datetime
from typing import List

from ...commands.base import BaseCommand, CommandResult
from ...core.localization import get_localization_manager
from ...core.types import SessionType
from ...game.monster import Monster

logger = logging.getLogger(__name__)

I18N = get_localization_manager()

@warnings.deprecated("dialogue/talk_command 로 대체 됨")
class TalkCommand(BaseCommand):
    """몬스터와 대화하는 명령어"""

    def __init__(self):
        super().__init__(
            name="talk",
            aliases=["speak", "chat"],
            description="몬스터와 대화합니다",
            usage="talk <몬스터이름>"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        """몬스터와 대화 실행"""
        try:
            locale = session.player.preferred_locale if session.player else "en"

            if not args:
                return self.create_error_result(I18N.get_message("npc.talk.usage", locale))

            monster_input = " ".join(args)

            # GameEngine을 통해 몬스터 조회
            game_engine = getattr(session, 'game_engine', None)
            if not game_engine:
                return self.create_error_result(I18N.get_message("npc.talk.no_engine", locale))

            # 플레이어 현재 좌표 가져오기
            current_room_id = getattr(session, 'current_room_id', None)
            if not current_room_id:
                return self.create_error_result(I18N.get_message("npc.talk.no_location", locale))

            current_room = await game_engine.world_manager.get_room(current_room_id)
            if not current_room or current_room.x is None or current_room.y is None:
                return self.create_error_result(I18N.get_message("npc.talk.no_room_coords", locale))

            player_x, player_y = current_room.x, current_room.y

            # 몬스터 검색
            monsters = await game_engine.world_manager.get_monsters_at_coordinates(player_x, player_y)
            target_monster = None

            for monster in monsters:
                if (monster_input.lower() in monster.get_localized_name(locale).lower() or
                    monster_input.lower() in monster.get_localized_name('en').lower() or
                    monster_input.lower() in monster.get_localized_name('ko').lower()):
                    target_monster = monster
                    break

            if not target_monster:
                return self.create_error_result(
                    I18N.get_message("npc.talk.not_found", locale, target=monster_input)
                )

            # 몬스터 우호도 확인
            player_faction = session.player.faction_id or 'ash_knights'
            monster_faction = getattr(target_monster, 'faction_id', None)

            # 중립 몬스터이거나 같은 팩션이면 대화 가능
            if monster_faction and monster_faction != 'neutral' and monster_faction != player_faction:
                return self.create_error_result(
                    I18N.get_message("npc.talk.hostile", locale,
                                     name=target_monster.get_localized_name(locale))
                )

            # 대화 가져오기
            monster_display_name = target_monster.get_localized_name(locale)

            # 몬스터 대화 내용 가져오기
            dialogue = self._get_monster_dialogue(target_monster, locale)

            # 퀘스트 시스템 연동 (특정 몬스터만)
            quest_message = ""
            if target_monster.id == 'church_monk':
                quest_message = await self._handle_quest_interaction(session, target_monster, game_engine)

            # 대화 메시지 생성
            if dialogue == "...":
                message = I18N.get_message("npc.talk.silent_stare", locale, name=monster_display_name)
            else:
                message = I18N.get_message("npc.talk.dialogue", locale,
                                           name=monster_display_name, dialogue=dialogue)

            # 퀘스트 메시지 추가
            if quest_message:
                message += f"\n\n{quest_message}"

            # 같은 방의 다른 플레이어들에게도 알림
            await game_engine.broadcast_to_room(
                session.current_room_id,
                {
                    "type": "room_message",
                    "message": I18N.get_message("npc.talk.broadcast", locale,
                                                player=session.player.username,
                                                monster=monster_display_name)
                },
                exclude_session=session.session_id
            )

            return self.create_success_result(message)

        except Exception as e:
            logger.error(f"대화 명령어 실행 실패: {e}", exc_info=True)
            locale = session.player.preferred_locale if session.player else "en"
            return self.create_error_result(I18N.get_message("npc.talk.error", locale))

    def _get_monster_dialogue(self, monster: Monster, locale: str) -> str:
        """몬스터 대화 내용 가져오기"""
        try:
            # 몬스터의 properties에서 dialogue 정보 가져오기
            if hasattr(monster, 'properties') and monster.properties:
                properties = monster.properties
                if isinstance(properties, str):
                    import json
                    properties = json.loads(properties)

                if isinstance(properties, dict) and 'dialogue' in properties:
                    dialogue_data = properties['dialogue']
                    if isinstance(dialogue_data, dict):
                        dialogue_list = dialogue_data.get(locale, dialogue_data.get('en', ['...']))
                        if dialogue_list and isinstance(dialogue_list, list):
                            import random
                            return random.choice(dialogue_list)

            return "..."
        except Exception as e:
            logger.error(f"몬스터 대화 내용 가져오기 실패: {e}")
            return "..."

    async def _handle_quest_interaction(self, session, monster, game_engine) -> str:  # type: ignore[no-untyped-def]
        """퀘스트 몬스터와의 상호작용 처리"""
        try:
            from ...game.quest import get_quest_manager

            quest_manager = get_quest_manager()
            locale = session.player.preferred_locale if session.player else "en"

            # 교회 수도사와의 상호작용
            if monster.id == "church_monk":
                return await self._handle_church_monk_quest(session, game_engine, quest_manager, locale)

            return ""

        except Exception as e:
            logger.error(f"퀘스트 상호작용 처리 실패: {e}")
            return ""

    async def _handle_church_monk_quest(self, session, game_engine, quest_manager, locale: str) -> str:  # type: ignore[no-untyped-def]
        """교회 수도사 퀘스트 처리"""
        quest_id = "tutorial_basic_equipment"

        # 플레이어의 퀘스트 상태 확인
        completed_quests = getattr(session.player, 'completed_quests', [])
        quest_progress = getattr(session.player, 'quest_progress', {})

        # 이미 완료한 퀘스트인지 확인
        if quest_id in completed_quests:
            return I18N.get_message("npc.talk.quest.already_completed", locale)

        # 진행 중인 퀘스트인지 확인
        if quest_id in quest_progress:
            # 생명의 정수 수집 확인
            essence_count = await self._count_player_items(session, game_engine, "essence_of_life")

            if essence_count >= 10:
                # 퀘스트 완료 가능
                return await self._complete_tutorial_quest(session, game_engine, locale)
            else:
                # 아직 수집 중
                remaining = 10 - essence_count
                return I18N.get_message("npc.talk.quest.progress", locale,
                                        count=essence_count, remaining=remaining)
        else:
            # 새로운 퀘스트 시작
            return await self._start_tutorial_quest(session, game_engine, quest_manager, locale)

    async def _start_tutorial_quest(self, session, game_engine, quest_manager, locale: str) -> str:  # type: ignore[no-untyped-def]
        """튜토리얼 퀘스트 시작"""
        quest_id = "tutorial_basic_equipment"

        # 퀘스트 진행 상황 초기화
        if not hasattr(session.player, 'quest_progress') or not isinstance(session.player.quest_progress, dict):
            session.player.quest_progress = {}

        session.player.quest_progress[quest_id] = {
            "status": "in_progress",
            "started_at": datetime.now().isoformat(),
            "objectives": {
                "talk_to_monk": 1,  # 이미 대화함
                "collect_essence": 0
            }
        }

        # 데이터베이스 업데이트
        try:
            await game_engine.model_manager.players.update(session.player.id, {
                'quest_progress': session.player.quest_progress
            })

            logger.info(f"플레이어 {session.player.username}이 튜토리얼 퀘스트 시작")

        except Exception as e:
            logger.error(f"퀘스트 진행 상황 저장 실패: {e}")

        return I18N.get_message("npc.talk.quest.start", locale)

    async def _complete_tutorial_quest(self, session, game_engine, locale: str) -> str:  # type: ignore[no-untyped-def]
        """튜토리얼 퀘스트 완료"""
        quest_id = "tutorial_basic_equipment"

        try:
            # 생명의 정수 10개 제거
            removed_count = await self._remove_player_items(session, game_engine, "essence_of_life", 10)

            if removed_count < 10:
                return I18N.get_message("npc.talk.quest.not_enough", locale, count=removed_count)

            # 기본 장비 지급
            equipment_given = await self._give_tutorial_equipment(session, game_engine)

            # 퀘스트 완료 처리
            if not hasattr(session.player, 'completed_quests') or not isinstance(session.player.completed_quests, list):
                session.player.completed_quests = []

            session.player.completed_quests.append(quest_id)

            # 진행 중인 퀘스트에서 제거
            if (hasattr(session.player, 'quest_progress') and
                isinstance(session.player.quest_progress, dict) and
                quest_id in session.player.quest_progress):
                del session.player.quest_progress[quest_id]

            # 데이터베이스 업데이트
            await game_engine.model_manager.players.update(session.player.id, {
                'completed_quests': session.player.completed_quests,
                'quest_progress': session.player.quest_progress
            })

            logger.info(f"플레이어 {session.player.username}이 튜토리얼 퀘스트 완료")

            return I18N.get_message("npc.talk.quest.complete", locale, equipment=equipment_given)

        except Exception as e:
            logger.error(f"튜토리얼 퀘스트 완료 처리 실패: {e}")
            return I18N.get_message("npc.talk.quest.complete_error", locale)

    async def _count_player_items(self, session, game_engine, item_name: str) -> int:  # type: ignore[no-untyped-def]
        """플레이어 인벤토리에서 특정 아이템 개수 확인"""
        try:
            inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)
            count = 0

            for obj in inventory_objects:
                obj_name_en = obj.get_localized_name("en").lower()
                obj_name_ko = obj.get_localized_name("ko").lower()

                if (item_name.lower() in obj_name_en or
                    item_name.lower() in obj_name_ko or
                    "essence" in obj_name_en):
                    # 스택 가능한 아이템인 경우 수량 확인
                    if hasattr(obj, 'properties') and obj.properties:
                        if isinstance(obj.properties, dict):
                            count += obj.properties.get('quantity', 1)
                        else:
                            count += 1
                    else:
                        count += 1

            return count

        except Exception as e:
            logger.error(f"아이템 개수 확인 실패: {e}")
            return 0

    async def _remove_player_items(self, session, game_engine, item_name: str, count: int) -> int:  # type: ignore[no-untyped-def]
        """플레이어 인벤토리에서 특정 아이템 제거"""
        try:
            inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)
            removed_count = 0

            for obj in inventory_objects:
                if removed_count >= count:
                    break

                obj_name_en = obj.get_localized_name("en").lower()
                obj_name_ko = obj.get_localized_name("ko").lower()

                if (item_name.lower() in obj_name_en or
                    item_name.lower() in obj_name_ko or
                    "essence" in obj_name_en):

                    # 아이템 제거
                    success = await game_engine.world_manager.remove_object(obj.id)
                    if success:
                        # 스택 가능한 아이템인 경우 수량 확인
                        if hasattr(obj, 'properties') and obj.properties:
                            if isinstance(obj.properties, dict):
                                removed_count += obj.properties.get('quantity', 1)
                            else:
                                removed_count += 1
                        else:
                            removed_count += 1

            return min(removed_count, count)

        except Exception as e:
            logger.error(f"아이템 제거 실패: {e}")
            return 0

    async def _give_tutorial_equipment(self, session, game_engine) -> str:  # type: ignore[no-untyped-def]
        """튜토리얼 기본 장비 지급"""
        try:
            locale = session.player.preferred_locale if session.player else "en"
            equipment_items = [
                "tutorial_club",
                "tutorial_linen_shirt",
                "tutorial_linen_trousers"
            ]

            given_items = []
            template_loader = game_engine.world_manager._monster_manager._template_loader

            for item_id in equipment_items:
                success = await self._create_item_from_template(session, game_engine, item_id)
                if success:
                    template = template_loader.get_item_template(item_id)
                    if template:
                        name_key = "name_ko" if locale == "ko" else "name_en"
                        item_name = template.get(name_key, item_id)
                        given_items.append(f"• {item_name}")

            if given_items:
                return "\n".join(given_items)
            return I18N.get_message("npc.talk.quest.equipment_fail", locale)

        except Exception as e:
            logger.error(f"튜토리얼 장비 지급 실패: {e}")
            locale = session.player.preferred_locale if session.player else "en"
            return I18N.get_message("npc.talk.quest.equipment_error", locale)

    async def _create_item_from_template(self, session, game_engine, template_id: str) -> bool:  # type: ignore[no-untyped-def]
        """템플릿에서 아이템을 복사하여 플레이어에게 지급"""
        try:
            from uuid import uuid4

            # template_loader에서 아이템 생성
            template_loader = game_engine.world_manager._monster_manager._template_loader
            item_id = str(uuid4())
            item = template_loader.create_item_from_template(
                template_id, item_id,
                location_type="inventory",
                location_id=session.player.id
            )
            if not item:
                logger.warning(f"템플릿 {template_id}에서 아이템 생성 실패")
                return False

            # 데이터베이스에 저장
            item_data = item.to_dict()
            await game_engine.model_manager.game_objects.create(item_data)
            logger.info(f"플레이어 {session.player.username}에게 아이템 {template_id} 지급")

            return True

        except Exception as e:
            logger.error(f"템플릿에서 아이템 생성 실패: {e}")
            return False
