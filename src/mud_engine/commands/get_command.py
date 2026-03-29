# -*- coding: utf-8 -*-
"""객체 획득 명령어"""

import logging
import traceback
from typing import List

from .base import BaseCommand, CommandResult
from .utils import get_user_locale
from ..core.types import SessionType
from ..core.localization import get_localization_manager
from ..core.event_bus import Event, EventType

logger = logging.getLogger(__name__)
I18N = get_localization_manager()


class GetCommand(BaseCommand):
    """객체 획득 명령어"""

    def __init__(self):
        super().__init__(
            name="get",
            aliases=["take", "pick"],
            description="방에 있는 객체를 인벤토리에 추가합니다",
            usage="get <객체명>"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not self.validate_args(args, min_args=1):
            return self.create_error_result(
                "획득할 객체를 지정해주세요.\n사용법: get <객체명> 또는 take <번호> from <상자번호>"
            )

        if not session.is_authenticated or not session.player:
            return self.create_error_result(I18N.get_message("obj.unauthenticated", get_user_locale(session)))

        if len(args) >= 3 and args[-2].lower() == "from":
            return await self._take_from_container(session, args)

        return await self._take_from_room(session, args)

    async def _take_from_container(self, session: SessionType, args: List[str]) -> CommandResult:
        """컨테이너에서 아이템을 가져오는 처리"""
        try:
            item_arg = args[0]
            container_arg = args[-1]

            try:
                item_number = int(item_arg)
                container_number = int(container_arg)
            except ValueError:
                return self.create_error_result(I18N.get_message("obj.invalid_number", get_user_locale(session)))

            game_engine = getattr(session, 'game_engine', None)
            if not game_engine:
                return self.create_error_result(I18N.get_message("obj.no_engine", get_user_locale(session)))

            result = await game_engine.world_manager.take_item_from_container(
                session.player.id, item_number, container_number, session.room_entity_map
            )

            if result['success']:
                return self.create_success_result(
                    message=result['message'],
                    data={
                        "action": "take_from_container",
                        "item_name": result.get('item_name'),
                        "container_name": result.get('container_name')
                    }
                )
            else:
                return self.create_error_result(result['message'])

        except Exception as e:
            logger.error(f"컨테이너에서 아이템 가져오기 실패: {e}")
            return self.create_error_result(I18N.get_message("obj.get.error", get_user_locale(session)))

    async def _take_from_room(self, session: SessionType, args: List[str]) -> CommandResult:
        """방에서 아이템을 가져오는 처리"""
        current_room_id = getattr(session, 'current_room_id', None)
        if not current_room_id:
            return self.create_error_result(I18N.get_message("obj.no_location", get_user_locale(session)))

        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result(I18N.get_message("obj.no_engine", get_user_locale(session)))

        object_name = " ".join(args).lower()

        try:
            target_group = None
            if object_name.isdigit():
                item_num = int(object_name)
                entity_map = getattr(session, 'room_entity_map', {})

                if item_num in entity_map and entity_map[item_num]['type'] == 'object':
                    target_object = entity_map[item_num]['entity']
                    target_group = {
                        'objects': [target_object],
                        'name_en': target_object.get_localized_name('en'),
                        'name_ko': target_object.get_localized_name('ko'),
                        'display_name_en': target_object.get_localized_name('en'),
                        'display_name_ko': target_object.get_localized_name('ko'),
                        'id': target_object.id
                    }
                elif item_num in entity_map and entity_map[item_num]['type'] == 'monster':
                    locale = get_user_locale(session)
                    if locale == "ko":
                        return self.create_error_result(
                            f"[{item_num}]은(는) 몬스터입니다. 아이템을 가져올 수 없습니다."
                        )
                    else:
                        return self.create_error_result(
                            f"[{item_num}] is a monster, not an item you can pick up."
                        )
                else:
                    locale = get_user_locale(session)
                    if locale == "ko":
                        return self.create_error_result(
                            f"번호 [{item_num}]에 해당하는 아이템을 찾을 수 없습니다.\n"
                            f"컨테이너 안의 아이템을 가져오려면: get <아이템번호> from <컨테이너번호>"
                        )
                    else:
                        return self.create_error_result(
                            f"No item found for number [{item_num}].\n"
                            f"To take from a container: get <item_num> from <container_num>"
                        )
            else:
                room_objects = await game_engine.world_manager.get_room_objects(current_room_id)
                grouped_objects = game_engine.world_manager._group_stackable_objects(room_objects)

                for group in grouped_objects:
                    group_name_en = group['name_en'].lower()
                    group_name_ko = group['name_ko'].lower()
                    if object_name in group_name_en or object_name in group_name_ko:
                        target_group = group
                        break

            if not target_group:
                return self.create_error_result(I18N.get_message("obj.get.not_found", get_user_locale(session), name=' '.join(args)))

            target_objects = target_group['objects']
            total_weight = sum(obj.weight for obj in target_objects)
            current_inventory = await game_engine.world_manager.get_inventory_objects(session.player.id)

            if not session.player.can_carry_more(current_inventory, total_weight):
                capacity_info = session.player.get_carry_capacity_info(current_inventory)
                return self.create_error_result(
                    f"무게 제한으로 인해 {target_group['display_name_ko']}을(를) 들 수 없습니다.\n"
                    f"현재 소지 용량: {capacity_info['current_weight']:.1f}kg / {capacity_info['max_weight']:.1f}kg\n"
                    f"아이템 총 무게: {total_weight:.1f}kg"
                )

            moved_objects = []
            for obj in target_objects:
                success = await game_engine.world_manager.move_object_to_inventory(
                    obj.id, session.player.id
                )
                if success:
                    moved_objects.append(obj)

            if not moved_objects:
                return self.create_error_result(I18N.get_message("obj.get.failed", get_user_locale(session)))

            await game_engine.event_bus.publish(Event(
                event_type=EventType.OBJECT_PICKED_UP,
                source=session.session_id,
                room_id=current_room_id,
                data={
                    "player_id": session.player.id,
                    "player_name": session.player.username,
                    "object_ids": [obj.id for obj in moved_objects],
                    "object_name": target_group['display_name_ko'],
                    "room_id": current_room_id,
                    "count": len(moved_objects)
                }
            ))

            count = len(moved_objects)
            obj_name = target_group['display_name_ko']
            if count > 1:
                player_message = f"📦 {obj_name} x{count}개를 획득했습니다."
                broadcast_message = f"📦 {session.player.username}님이 {obj_name} x{count}개를 획득했습니다."
            else:
                player_message = f"📦 {obj_name}을(를) 획득했습니다."
                broadcast_message = f"📦 {session.player.username}님이 {obj_name}을(를) 획득했습니다."

            return self.create_success_result(
                message=player_message,
                data={
                    "action": "get",
                    "object_ids": [obj.id for obj in moved_objects],
                    "object_name": obj_name,
                    "count": count,
                    "player": session.player.username,
                    "room_id": current_room_id
                },
                broadcast=True,
                broadcast_message=broadcast_message,
                room_only=True
            )

        except Exception as e:
            logger.error(f"객체 획득 명령어 실행 중 오류: {e}")
            logger.error(f"스택 트레이스: {traceback.format_exc()}")
            return self.create_error_result(I18N.get_message("obj.get.error", get_user_locale(session)))
