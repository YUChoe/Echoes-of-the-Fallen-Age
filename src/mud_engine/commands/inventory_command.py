# -*- coding: utf-8 -*-
"""인벤토리 확인 명령어"""

import logging
from typing import List, Dict

from .base import BaseCommand, CommandResult
from .utils import get_user_locale
from ..core.types import SessionType
from ..core.localization import get_localization_manager, get_message

logger = logging.getLogger(__name__)
I18N = get_localization_manager()


class InventoryCommand(BaseCommand):
    """인벤토리 확인 명령어"""

    def __init__(self):
        super().__init__(
            name="inventory",
            aliases=["inv", "i"],
            description="현재 소지하고 있는 객체들을 표시합니다",
            usage="inventory [category]"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result(I18N.get_message("obj.unauthenticated", get_user_locale(session)))

        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result(I18N.get_message("obj.no_engine", get_user_locale(session)))

        locale = get_user_locale(session)

        inventory_entity = getattr(session, 'inventory_entity_map', {})
        logger.info(f"inventory_entity from session cnt[{len(inventory_entity.keys())}]")

        filter_category = None
        logger.info(f"args[{args}]")
        if args:
            filter_category = args[0].lower()
            valid_categories = {'weapon', 'armor', 'consumable', 'misc', 'material', 'equipped'}
            if filter_category not in valid_categories:
                return self.create_error_result(
                    get_message("inventory.invalid_category", locale, categories=', '.join(valid_categories))
                )

        try:
            inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)

            if not inventory_objects:
                return self.create_info_result(get_message("inventory.empty", locale))

            _cnt = 0
            for _item in inventory_objects:
                _cnt += 1
                logger.debug(f"inventory_objects[{_cnt}]{_item.to_simple()}]")

            if filter_category:
                if filter_category == 'equipped':
                    filtered_objects = [obj for obj in inventory_objects if obj.is_equipped]
                else:
                    filtered_objects = [obj for obj in inventory_objects if obj.category == filter_category]
            else:
                filtered_objects = inventory_objects
            logger.debug(f"filter_category[{filter_category}] filtered_objects[{filtered_objects}]")

            if not filtered_objects:
                category_name = filter_category if filter_category else get_message("inventory.category_all", locale)
                return self.create_info_result(
                    get_message("inventory.category_empty", locale, category=category_name)
                )

            capacity_info = session.player.get_carry_capacity_info(inventory_objects)
            logger.debug(f"capacity_info[{capacity_info}]")

            response = get_message("inventory.title", locale, username=session.player.username)
            if filter_category:
                response += f" ({filter_category})"

            response += f" {capacity_info['current_weight']:.1f}/{capacity_info['max_weight']:.1f} ({capacity_info['percentage']:.1f}%)"
            response += "\n\n"

            items: Dict[str, Dict] = {}
            for obj in filtered_objects:
                obj_name = obj.get_localized_name(locale)
                if obj_name not in items:
                    items[obj_name] = {
                        'objects': [],
                        'total_weight': 0.0,
                        'equipped_count': 0
                    }
                items[obj_name]['objects'].append(obj)
                items[obj_name]['total_weight'] += obj.weight
                if obj.is_equipped:
                    items[obj_name]['equipped_count'] += 1

            _idx = 100
            inventory_entity = {}
            for obj_name in sorted(items.keys()):
                item_data = items[obj_name]
                count = len(item_data['objects'])
                total_weight = item_data['total_weight']
                equipped_count = item_data['equipped_count']

                weight_display = f"({total_weight:.1f}kg)" if total_weight > 0 else ""
                count_display = f" x{count}" if count > 1 else ""
                equipped_mark = get_message("inventory.equipped_marker", locale) if equipped_count > 0 else ""

                response += f"• [{_idx}] {obj_name}{count_display} {weight_display}{equipped_mark}\n"
                inventory_entity[_idx] = item_data
                _idx += 1

            for _idx in inventory_entity.keys():
                _list = inventory_entity[_idx]['objects']
                for gobj in _list:
                    logger.info(f"inventory_entity[{_idx}] {gobj.to_simple()}")

            session.inventory_entity_map = inventory_entity

            response += "\n"

            return self.create_success_result(
                message=response.strip(),
                data={
                    "action": "inventory",
                    "player": session.player.username,
                    "filter_category": filter_category,
                    "item_count": len(filtered_objects),
                    "total_items": len(inventory_objects),
                    "capacity_info": capacity_info,
                    "items": list(items.keys())
                }
            )

        except Exception as e:
            logger.error(f"인벤토리 명령어 실행 중 오류: {e}")
            return self.create_error_result(I18N.get_message("obj.inv.error", get_user_locale(session)))
