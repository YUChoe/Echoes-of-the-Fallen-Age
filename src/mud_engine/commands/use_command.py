# -*- coding: utf-8 -*-
"""아이템 사용 명령어"""

import json
import logging
import traceback
from typing import List, Optional

from .base import BaseCommand, CommandResult
from .utils import get_user_locale
from ..core.types import SessionType
from ..core.localization import get_localization_manager

logger = logging.getLogger(__name__)
I18N = get_localization_manager()


class UseCommand(BaseCommand):
    """아이템 사용 명령어"""

    def __init__(self):
        super().__init__(
            name="use",
            aliases=["consume", "activate"],
            description="소모품이나 사용 가능한 아이템을 사용합니다",
            usage="use <아이템명>"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not self.validate_args(args, min_args=1):
            return self.create_error_result("사용할 아이템을 지정해주세요.\n사용법: use <아이템명>")

        if not session.is_authenticated or not session.player:
            return self.create_error_result(I18N.get_message("obj.unauthenticated", get_user_locale(session)))

        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result(I18N.get_message("obj.no_engine", get_user_locale(session)))

        item_name = " ".join(args).lower()

        try:
            inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)

            target_item = None
            for obj in inventory_objects:
                obj_name_en = obj.get_localized_name('en').lower()
                obj_name_ko = obj.get_localized_name('ko').lower()
                if item_name in obj_name_en or item_name in obj_name_ko:
                    target_item = obj
                    break

            if not target_item:
                return self.create_error_result(I18N.get_message("obj.use.not_in_inv", get_user_locale(session), name=' '.join(args)))

            if target_item.category != 'consumable':
                return self.create_error_result(I18N.get_message("obj.use.not_usable", get_user_locale(session), name=target_item.get_localized_name(session.locale)))

            item_name_display = target_item.get_localized_name(session.locale)
            effect_message = ""

            if 'heal_amount' in target_item.properties:
                heal_amount = target_item.properties.get('heal_amount', 10)
                effect_message = f"체력이 {heal_amount} 회복되었습니다."
            elif 'mana_amount' in target_item.properties:
                mana_amount = target_item.properties.get('mana_amount', 10)
                effect_message = f"마나가 {mana_amount} 회복되었습니다."
            else:
                effect_message = f"{item_name_display}을(를) 사용했습니다."

            await game_engine.world_manager.remove_object(target_item.id)

            message = f"💊 {item_name_display}을(를) 사용했습니다.\n{effect_message}"

            return self.create_success_result(
                message=message,
                data={"action": "use", "item_id": target_item.id, "item_name": item_name_display, "effect": effect_message}
            )

        except Exception as e:
            logger.error(f"아이템 사용 명령어 실행 중 오류: {e}")
            return self.create_error_result(I18N.get_message("obj.use.error", get_user_locale(session)))

    async def _take_from_container(self, session: SessionType, args: List[str]) -> CommandResult:
        """컨테이너에서 아이템 가져오기 (take X from Y)"""
        container_target = args[-1]
        item_target = " ".join(args[:-2])

        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result(I18N.get_message("obj.no_engine", get_user_locale(session)))

        try:
            container_id, container_name = await self._find_container(session, game_engine, container_target)
            if not container_id:
                message = f"Could't find a container {container_target}."
                if session.locale != 'en':
                    message = f"'{container_target}' 상자를 찾을 수 없습니다."
                return self.create_error_result(message)

            container_items = await game_engine.world_manager.get_container_items(container_id)
            if not container_items:
                return self.create_error_result(I18N.get_message("obj.container.empty", get_user_locale(session), name=container_name))

            target_item = None
            locale = session.player.preferred_locale if session.player else "en"

            if item_target.isdigit():
                item_index = int(item_target) - 1
                if 0 <= item_index < len(container_items):
                    target_item = container_items[item_index]
            else:
                for item in container_items:
                    if item_target.lower() in item.get_localized_name(locale).lower():
                        target_item = item
                        break

            if not target_item:
                return self.create_error_result(I18N.get_message("obj.container.item_not_found", get_user_locale(session), item=item_target, container=container_name))

            current_inventory = await game_engine.world_manager.get_inventory_objects(session.player.id)
            if not session.player.can_carry_more(current_inventory, target_item.weight):
                capacity_info = session.player.get_carry_capacity_info(current_inventory)
                return self.create_error_result(
                    f"무게 제한으로 인해 {target_item.get_localized_name(locale)}을(를) 들 수 없습니다.\n"
                    f"현재 소지 용량: {capacity_info['current_weight']:.1f}kg / {capacity_info['max_weight']:.1f}kg\n"
                    f"아이템 무게: {target_item.weight:.1f}kg"
                )

            success = await game_engine.world_manager.move_item_from_container(
                target_item.id, "INVENTORY", session.player.id
            )

            if not success:
                return self.create_error_result(I18N.get_message("obj.get.error", get_user_locale(session)))

            item_name = target_item.get_localized_name(locale)
            message = f"📦 {container_name}에서 {item_name}을(를) 가져왔습니다."

            return self.create_success_result(
                message=message,
                data={"action": "take_from_container", "item_name": item_name, "container_name": container_name, "item_id": target_item.id}
            )

        except Exception as e:
            logger.error(f"컨테이너에서 아이템 가져오기 오류: {e}")
            return self.create_error_result(I18N.get_message("obj.get.error", get_user_locale(session)))

    async def _take_from_room(self, session: SessionType, args: List[str]) -> CommandResult:
        """방에서 아이템 가져오기"""
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
                else:
                    return self.create_error_result(f"번호 [{item_num}]에 해당하는 아이템을 찾을 수 없습니다.")
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
                success = await game_engine.world_manager.move_object_to_inventory(obj.id, session.player.id)
                if success:
                    moved_objects.append(obj)

            if not moved_objects:
                return self.create_error_result(I18N.get_message("obj.get.failed", get_user_locale(session)))

            if len(moved_objects) == 1:
                obj_name = moved_objects[0].get_localized_name(session.locale)
            else:
                obj_name = target_group['display_name_ko'] if session.locale == 'ko' else target_group['display_name_en']

            player_message = f"📦 {obj_name}을(를) 획득했습니다."
            broadcast_message = f"📦 {session.player.username}님이 {obj_name}을(를) 가져갔습니다."

            return self.create_success_result(
                message=player_message,
                data={
                    "action": "get",
                    "object_count": len(moved_objects),
                    "object_ids": [obj.id for obj in moved_objects],
                    "object_name": obj_name,
                    "player": session.player.username
                },
                broadcast=True,
                broadcast_message=broadcast_message,
                room_only=True
            )

        except Exception as e:
            logger.error(f"객체 획득 명령어 실행 중 오류: {e}")
            logger.error(f"스택 트레이스: {traceback.format_exc()}")
            return self.create_error_result(I18N.get_message("obj.get.error", get_user_locale(session)))

    async def _find_container(self, session: SessionType, game_engine, target: str) -> tuple[Optional[str], Optional[str]]:
        """상자 찾기 (번호 또는 이름으로)"""
        if target.isdigit():
            entity_number = int(target)
            entity_map = getattr(session, 'room_entity_map', {})
            if entity_number in entity_map:
                entity_info = entity_map[entity_number]
                if entity_info.get('type') == 'object':
                    obj = entity_info.get('entity')
                    if obj and self._is_container(obj):
                        return entity_info.get('id'), entity_info.get('name')
        return None, None

    def _is_container(self, obj) -> bool:
        """오브젝트가 컨테이너인지 확인"""
        try:
            properties = obj.properties if hasattr(obj, 'properties') else {}
            if isinstance(properties, str):
                properties = json.loads(properties)
            return properties.get('is_container', False)
        except Exception:
            return False
