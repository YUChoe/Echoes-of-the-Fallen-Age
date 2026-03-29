# -*- coding: utf-8 -*-
"""장비 착용/해제 명령어"""

import logging
from typing import List

from .base import BaseCommand, CommandResult
from .utils import get_user_locale
from ..core.types import SessionType
from ..core.localization import get_localization_manager

logger = logging.getLogger(__name__)
I18N = get_localization_manager()


class EquipCommand(BaseCommand):
    """장비 착용 명령어"""

    def __init__(self):
        super().__init__(
            name="equip",
            aliases=["wear", "wield"],
            description="인벤토리의 장비를 착용합니다",
            usage="equip <장비명>"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not self.validate_args(args, min_args=1):
            return self.create_error_result("착용할 장비를 지정해주세요.\n사용법: equip <장비명>")

        if not session.is_authenticated or not session.player:
            return self.create_error_result(I18N.get_message("obj.unauthenticated", get_user_locale(session)))

        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result(I18N.get_message("obj.no_engine", get_user_locale(session)))

        equipment_name = " ".join(args).lower()

        try:
            inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)

            target_equipment = None
            for obj in inventory_objects:
                obj_name_en = obj.get_localized_name('en').lower()
                obj_name_ko = obj.get_localized_name('ko').lower()
                if equipment_name in obj_name_en or equipment_name in obj_name_ko:
                    target_equipment = obj
                    break

            if not target_equipment:
                return self.create_error_result(I18N.get_message("obj.equip.not_in_inv", get_user_locale(session), name=' '.join(args)))

            if not target_equipment.can_be_equipped():
                return self.create_error_result(I18N.get_message("obj.equip.not_equippable", get_user_locale(session), name=target_equipment.get_localized_name(session.locale)))

            if target_equipment.is_equipped:
                return self.create_error_result(I18N.get_message("obj.equip.already_equipped", get_user_locale(session), name=target_equipment.get_localized_name(session.locale)))

            equipped_in_slot = None
            for obj in inventory_objects:
                if (obj.equipment_slot == target_equipment.equipment_slot and
                    obj.is_equipped and obj.id != target_equipment.id):
                    equipped_in_slot = obj
                    break

            if equipped_in_slot:
                await _remove_equipment_bonuses(session.player, equipped_in_slot, game_engine)
                equipped_in_slot.unequip()
                await game_engine.world_manager.update_object(equipped_in_slot)

            target_equipment.equip()
            await game_engine.world_manager.update_object(target_equipment)
            await _apply_equipment_bonuses(session.player, target_equipment, game_engine)

            equipment_name_display = target_equipment.get_localized_name(session.locale)
            message = f"⚔️ {equipment_name_display}을(를) 착용했습니다."

            if equipped_in_slot:
                old_equipment_name = equipped_in_slot.get_localized_name(session.locale)
                message += f"\n({old_equipment_name}을(를) 해제했습니다.)"

            return self.create_success_result(
                message=message,
                data={
                    "action": "equip",
                    "equipment_id": target_equipment.id,
                    "equipment_name": equipment_name_display,
                    "equipment_slot": target_equipment.equipment_slot,
                    "replaced_equipment": equipped_in_slot.get_localized_name(session.locale) if equipped_in_slot else None
                }
            )

        except Exception as e:
            logger.error(f"장비 착용 명령어 실행 중 오류: {e}")
            return self.create_error_result(I18N.get_message("obj.equip.error", get_user_locale(session)))


class UnequipCommand(BaseCommand):
    """장비 해제 명령어"""

    def __init__(self):
        super().__init__(
            name="unequip",
            aliases=["remove", "unwield"],
            description="착용 중인 장비를 해제합니다",
            usage="unequip <장비명>"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not self.validate_args(args, min_args=1):
            return self.create_error_result("해제할 장비를 지정해주세요.\n사용법: unequip <장비명>")

        if not session.is_authenticated or not session.player:
            return self.create_error_result(I18N.get_message("obj.unauthenticated", get_user_locale(session)))

        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result(I18N.get_message("obj.no_engine", get_user_locale(session)))

        equipment_name = " ".join(args).lower()

        try:
            inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)

            target_equipment = None
            for obj in inventory_objects:
                if obj.is_equipped:
                    obj_name_en = obj.get_localized_name('en').lower()
                    obj_name_ko = obj.get_localized_name('ko').lower()
                    if equipment_name in obj_name_en or equipment_name in obj_name_ko:
                        target_equipment = obj
                        break

            if not target_equipment:
                return self.create_error_result(I18N.get_message("obj.unequip.not_found", get_user_locale(session), name=' '.join(args)))

            await _remove_equipment_bonuses(session.player, target_equipment, game_engine)
            target_equipment.unequip()
            await game_engine.world_manager.update_object(target_equipment)

            equipment_name_display = target_equipment.get_localized_name(session.locale)
            message = f"⚔️ {equipment_name_display}을(를) 해제했습니다."

            return self.create_success_result(
                message=message,
                data={
                    "action": "unequip",
                    "equipment_id": target_equipment.id,
                    "equipment_name": equipment_name_display,
                    "equipment_slot": target_equipment.equipment_slot
                }
            )

        except Exception as e:
            logger.error(f"장비 해제 명령어 실행 중 오류: {e}")
            return self.create_error_result(I18N.get_message("obj.unequip.error", get_user_locale(session)))


async def _apply_equipment_bonuses(player, equipment, game_engine):
    """장비의 능력치 보너스를 플레이어에게 적용"""
    try:
        if not hasattr(equipment, 'properties') or not equipment.properties:
            return
        stats_bonus = equipment.properties.get('stats_bonus', {})
        for stat_name, bonus in stats_bonus.items():
            if isinstance(bonus, (int, float)) and bonus > 0:
                player.stats.add_equipment_bonus(stat_name, int(bonus))
        await game_engine.session_manager.update_player(player)
    except Exception as e:
        logger.error(f"장비 보너스 적용 중 오류: {e}")


async def _remove_equipment_bonuses(player, equipment, game_engine):
    """장비의 능력치 보너스를 플레이어에서 제거"""
    try:
        if not hasattr(equipment, 'properties') or not equipment.properties:
            return
        stats_bonus = equipment.properties.get('stats_bonus', {})
        for stat_name, bonus in stats_bonus.items():
            if isinstance(bonus, (int, float)) and bonus > 0:
                player.stats.remove_equipment_bonus(stat_name, int(bonus))
        await game_engine.session_manager.update_player(player)
    except Exception as e:
        logger.error(f"장비 보너스 제거 중 오류: {e}")
