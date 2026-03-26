# -*- coding: utf-8 -*-
"""몬스터와 거래하는 명령어 (퀘스트용)"""

import logging
from typing import List

from ...commands.base import BaseCommand, CommandResult
from ...core.types import SessionType

logger = logging.getLogger(__name__)


class TradeCommand(BaseCommand):
    """몬스터와 거래하는 명령어 (퀘스트용)"""

    def __init__(self):
        super().__init__(
            name="trade",
            aliases=["give"],
            description="몬스터와 아이템을 거래합니다",
            usage="trade <아이템이름> <몬스터이름>"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        """몬스터와 거래 실행"""
        try:
            if len(args) < 2:
                return self.create_error_result("사용법: trade <아이템이름> <몬스터이름>")

            item_name = args[0]
            monster_name = " ".join(args[1:])

            # GameEngine을 통해 몬스터 조회
            game_engine = getattr(session, 'game_engine', None)
            if not game_engine:
                return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

            # 플레이어 현재 좌표 가져오기
            current_room_id = getattr(session, 'current_room_id', None)
            if not current_room_id:
                return self.create_error_result("현재 위치를 확인할 수 없습니다.")

            current_room = await game_engine.world_manager.get_room(current_room_id)
            if not current_room or current_room.x is None or current_room.y is None:
                return self.create_error_result("현재 방의 좌표를 확인할 수 없습니다.")

            player_x, player_y = current_room.x, current_room.y

            # 몬스터 찾기
            monsters = await game_engine.world_manager.get_monsters_at_coordinates(player_x, player_y)
            target_monster = None

            for monster in monsters:
                locale = session.player.preferred_locale if session.player else 'en'
                if (monster_name.lower() in monster.get_localized_name(locale).lower() or
                    monster_name.lower() in monster.get_localized_name('en').lower() or
                    monster_name.lower() in monster.get_localized_name('ko').lower()):
                    target_monster = monster
                    break

            if not target_monster:
                return self.create_error_result(f"'{monster_name}'을(를) 찾을 수 없습니다.")

            # 교회 수도사와의 거래 처리
            if target_monster.id == "church_monk":
                return await self._handle_monk_trade(session, game_engine, target_monster, item_name)

            return self.create_error_result("이 몬스터는 거래를 하지 않습니다.")

        except Exception as e:
            logger.error(f"거래 명령어 실행 실패: {e}", exc_info=True)
            return self.create_error_result("거래 중 오류가 발생했습니다.")

    async def _handle_monk_trade(self, session, game_engine, monster, item_name: str) -> CommandResult:  # type: ignore[no-untyped-def]
        """수도사와의 거래 처리"""
        try:
            locale = session.player.preferred_locale if session.player else "en"

            # 퀘스트 완료 여부 확인
            completed_quests = getattr(session.player, 'completed_quests', [])
            if "tutorial_basic_equipment" in completed_quests:
                if locale == "ko":
                    return self.create_error_result("이미 퀘스트를 완료하셨습니다. 더 이상 거래할 수 없습니다.")
                else:
                    return self.create_error_result("You have already completed the quest. No more trades available.")

            # 생명의 정수인지 확인
            if "essence" not in item_name.lower() and "정수" not in item_name:
                if locale == "ko":
                    return self.create_error_result("수도사는 생명의 정수만 받습니다.")
                else:
                    return self.create_error_result("The monk only accepts Essence of Life.")

            # 플레이어가 생명의 정수를 가지고 있는지 확인
            inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)
            essence_items = []

            for obj in inventory_objects:
                obj_name_en = obj.get_localized_name("en").lower()
                obj_name_ko = obj.get_localized_name("ko").lower()

                if ("essence" in obj_name_en or "정수" in obj_name_ko):
                    essence_items.append(obj)

            if not essence_items:
                if locale == "ko":
                    return self.create_error_result("생명의 정수를 가지고 있지 않습니다.")
                else:
                    return self.create_error_result("You don't have any Essence of Life.")

            # 생명의 정수 개수 확인
            total_essence = len(essence_items)

            if total_essence < 10:
                if locale == "ko":
                    return self.create_error_result(f"생명의 정수가 부족합니다. ({total_essence}/10개)")
                else:
                    return self.create_error_result(f"Not enough Essence of Life. ({total_essence}/10)")

            # 퀘스트 완료 처리
            from .talk_command import TalkCommand
            talk_command = TalkCommand()
            result = await talk_command._complete_tutorial_quest(session, game_engine, locale)

            return self.create_success_result(result)

        except Exception as e:
            logger.error(f"수도사 거래 처리 실패: {e}")
            locale = session.player.preferred_locale if session.player else "en"
            if locale == "ko":
                return self.create_error_result("거래 처리 중 오류가 발생했습니다.")
            else:
                return self.create_error_result("An error occurred during the trade.")
