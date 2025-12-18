# -*- coding: utf-8 -*-
"""객체 상호작용 명령어들"""

import logging
from typing import List, Dict

from .base import BaseCommand, CommandResult, CommandResultType
from ..core.types import SessionType
from ..game.models import GameObject

logger = logging.getLogger(__name__)


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
                "획득할 객체를 지정해주세요.\n사용법: get <객체명>"
            )

        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        # 현재 방 ID 가져오기
        current_room_id = getattr(session, 'current_room_id', None)
        if not current_room_id:
            return self.create_error_result("현재 위치를 확인할 수 없습니다.")

        # GameEngine을 통해 객체 획득 처리
        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

        object_name = " ".join(args).lower()

        try:
            # 현재 방의 객체들 조회
            room_objects = await game_engine.world_manager.get_room_objects(current_room_id)

            # 객체 이름으로 검색
            target_object = None
            for obj in room_objects:
                try:
                    logger.debug(f"객체 검색 중: {obj.id}, type: {type(obj)}, name: {obj.name}")
                    obj_name_en = obj.get_localized_name('en').lower()
                    obj_name_ko = obj.get_localized_name('ko').lower()
                    if object_name in obj_name_en or object_name in obj_name_ko:
                        target_object = obj
                        break
                except Exception as name_error:
                    logger.error(f"객체 이름 처리 중 오류 ({obj.id}): {name_error}", exc_info=True)
                    continue

            if not target_object:
                return self.create_error_result(f"'{' '.join(args)}'을(를) 찾을 수 없습니다.")

            # 무게 제한 확인
            current_inventory = await game_engine.world_manager.get_inventory_objects(session.player.id)
            if not session.player.can_carry_more(current_inventory, target_object.weight):
                capacity_info = session.player.get_carry_capacity_info(current_inventory)
                return self.create_error_result(
                    f"무게 제한으로 인해 {target_object.get_localized_name(session.locale)}을(를) 들 수 없습니다.\n"
                    f"현재 소지 용량: {capacity_info['current_weight']:.1f}kg / {capacity_info['max_weight']:.1f}kg\n"
                    f"아이템 무게: {target_object.get_weight_display()}"
                )

            # 객체를 플레이어 인벤토리로 이동
            try:
                success = await game_engine.world_manager.move_object_to_inventory(
                    target_object.id, session.player.id
                )
                logger.debug(f"객체 이동 결과: {success}")
            except Exception as move_error:
                logger.error(f"객체 이동 중 오류: {move_error}", exc_info=True)
                return self.create_error_result("객체를 이동하는 중 오류가 발생했습니다.")

            if not success:
                return self.create_error_result("객체를 획득할 수 없습니다.")

            # 객체 획득 이벤트 발행
            try:
                from ..core.event_bus import Event, EventType
                logger.debug(f"이벤트 발행 준비: EventType.OBJECT_PICKED_UP = {EventType.OBJECT_PICKED_UP}")
                await game_engine.event_bus.publish(Event(
                    event_type=EventType.OBJECT_PICKED_UP,
                    source=session.session_id,
                    room_id=current_room_id,
                    data={
                        "player_id": session.player.id,
                        "player_name": session.player.username,
                        "object_id": target_object.id,
                        "object_name": target_object.get_localized_name(session.locale),
                        "room_id": current_room_id
                    }
                ))
                logger.debug("이벤트 발행 완료")
            except Exception as event_error:
                logger.error(f"이벤트 발행 중 오류: {event_error}", exc_info=True)
                # 이벤트 발행 실패해도 명령어는 성공으로 처리

            # 성공 메시지
            obj_name = target_object.get_localized_name(session.locale)
            player_message = f"📦 {obj_name}을(를) 획득했습니다."

            # 다른 플레이어들에게 알림
            broadcast_message = f"📦 {session.player.username}님이 {obj_name}을(를) 가져갔습니다."

            return self.create_success_result(
                message=player_message,
                data={
                    "action": "get",
                    "object_id": target_object.id,
                    "object_name": obj_name,
                    "player": session.player.username
                },
                broadcast=True,
                broadcast_message=broadcast_message,
                room_only=True
            )

        except Exception as e:
            import traceback
            logger.error(f"객체 획득 명령어 실행 중 오류: {e}")
            logger.error(f"스택 트레이스: {traceback.format_exc()}")
            return self.create_error_result("객체를 획득하는 중 오류가 발생했습니다.")


class DropCommand(BaseCommand):
    """객체 버리기 명령어"""

    def __init__(self):
        super().__init__(
            name="drop",
            aliases=["put", "place"],
            description="인벤토리의 객체를 현재 방에 놓습니다",
            usage="drop <객체명>"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not self.validate_args(args, min_args=1):
            return self.create_error_result(
                "버릴 객체를 지정해주세요.\n사용법: drop <객체명>"
            )

        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        # 현재 방 ID 가져오기
        current_room_id = getattr(session, 'current_room_id', None)
        if not current_room_id:
            return self.create_error_result("현재 위치를 확인할 수 없습니다.")

        # GameEngine을 통해 객체 버리기 처리
        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

        object_name = " ".join(args).lower()

        try:
            # 플레이어 인벤토리의 객체들 조회
            inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)

            # 객체 이름으로 검색
            target_object = None
            for obj in inventory_objects:
                obj_name_en = obj.get_localized_name('en').lower()
                obj_name_ko = obj.get_localized_name('ko').lower()
                if object_name in obj_name_en or object_name in obj_name_ko:
                    target_object = obj
                    break

            if not target_object:
                return self.create_error_result(f"인벤토리에 '{' '.join(args)}'이(가) 없습니다.")

            # 객체를 현재 방으로 이동
            success = await game_engine.world_manager.move_object_to_room(
                target_object.id, current_room_id
            )

            if not success:
                return self.create_error_result("객체를 버릴 수 없습니다.")

            # 객체 드롭 이벤트 발행
            from ..core.event_bus import Event, EventType
            await game_engine.event_bus.publish(Event(
                event_type=EventType.OBJECT_DROPPED,
                source=session.session_id,
                room_id=current_room_id,
                data={
                    "player_id": session.player.id,
                    "player_name": session.player.username,
                    "object_id": target_object.id,
                    "object_name": target_object.get_localized_name(session.locale),
                    "room_id": current_room_id
                }
            ))

            # 성공 메시지
            obj_name = target_object.get_localized_name(session.locale)
            player_message = f"📦 {obj_name}을(를) 버렸습니다."

            # 다른 플레이어들에게 알림
            broadcast_message = f"📦 {session.player.username}님이 {obj_name}을(를) 버렸습니다."

            return self.create_success_result(
                message=player_message,
                data={
                    "action": "drop",
                    "object_id": target_object.id,
                    "object_name": obj_name,
                    "player": session.player.username,
                    "room_id": current_room_id
                },
                broadcast=True,
                broadcast_message=broadcast_message,
                room_only=True
            )

        except Exception as e:
            logger.error(f"객체 버리기 명령어 실행 중 오류: {e}")
            return self.create_error_result("객체를 버리는 중 오류가 발생했습니다.")


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
            return self.create_error_result("인증되지 않은 사용자입니다.")

        # GameEngine을 통해 인벤토리 조회
        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

        # 카테고리 필터링
        filter_category = None
        if args:
            filter_category = args[0].lower()
            valid_categories = {'weapon', 'armor', 'consumable', 'misc', 'material', 'equipped'}
            if filter_category not in valid_categories:
                return self.create_error_result(
                    f"올바르지 않은 카테고리입니다. 사용 가능한 카테고리: {', '.join(valid_categories)}"
                )

        try:
            # 플레이어 인벤토리의 객체들 조회
            inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)

            if not inventory_objects:
                return self.create_info_result("🎒 인벤토리가 비어있습니다.")

            # 카테고리별 필터링
            if filter_category:
                if filter_category == 'equipped':
                    filtered_objects = [obj for obj in inventory_objects if obj.is_equipped]
                else:
                    filtered_objects = [obj for obj in inventory_objects if obj.category == filter_category]
            else:
                filtered_objects = inventory_objects

            if not filtered_objects:
                category_name = filter_category if filter_category else "전체"
                return self.create_info_result(f"🎒 {category_name} 카테고리에 아이템이 없습니다.")

            # 소지 용량 정보
            capacity_info = session.player.get_carry_capacity_info(inventory_objects)

            # 인벤토리 목록 생성
            response = f"🎒 {session.player.username}의 인벤토리"
            if filter_category:
                response += f" ({filter_category})"
            response += ":\n\n"

            # 용량 정보 표시
            response += f"📊 소지 용량: {capacity_info['current_weight']:.1f}kg / {capacity_info['max_weight']:.1f}kg ({capacity_info['percentage']:.1f}%)\n"
            if capacity_info['is_overloaded']:
                response += "⚠️ 과부하 상태입니다!\n"
            response += "\n"

            # 카테고리별로 정렬 및 같은 아이템 집계
            categories: Dict[str, Dict[str, Dict]] = {}
            for obj in filtered_objects:
                category = obj.category
                if category not in categories:
                    categories[category] = {}

                # 아이템 이름으로 그룹화
                obj_name = obj.get_localized_name(session.locale)
                if obj_name not in categories[category]:
                    categories[category][obj_name] = {
                        'objects': [],
                        'total_weight': 0.0,
                        'equipped_count': 0
                    }

                categories[category][obj_name]['objects'].append(obj)
                categories[category][obj_name]['total_weight'] += obj.weight
                if obj.is_equipped:
                    categories[category][obj_name]['equipped_count'] += 1

            object_list = []
            for category in sorted(categories.keys()):
                items = categories[category]
                if not items:
                    continue

                # 카테고리 표시명 가져오기
                first_obj = next(iter(items.values()))['objects'][0]
                category_display = first_obj.get_category_display(session.locale)
                response += f"📂 {category_display}:\n"

                for obj_name in sorted(items.keys()):
                    item_data = items[obj_name]
                    count = len(item_data['objects'])
                    total_weight = item_data['total_weight']
                    equipped_count = item_data['equipped_count']

                    # 무게 표시 (무게가 0이면 표시하지 않음)
                    if total_weight > 0:
                        weight_display = f"({total_weight:.1f}kg)"
                    else:
                        weight_display = ""

                    # 개수 표시 (1개보다 많으면 표시)
                    count_display = f" x{count}" if count > 1 else ""

                    # 착용 표시
                    equipped_mark = " [착용중]" if equipped_count > 0 else ""

                    response += f"  • {obj_name}{count_display} {weight_display}{equipped_mark}\n"

                    # 첫 번째 객체 정보를 대표로 사용
                    first_obj = item_data['objects'][0]
                    object_list.append({
                        "id": first_obj.id,
                        "name": obj_name,
                        "category": first_obj.category,
                        "count": count,
                        "total_weight": total_weight,
                        "is_equipped": equipped_count > 0,
                        "equipment_slot": first_obj.equipment_slot,
                        "description": first_obj.get_localized_description(session.locale)
                    })

                response += "\n"

            response += f"총 {len(filtered_objects)}개의 아이템을 소지하고 있습니다."

            return self.create_success_result(
                message=response.strip(),
                data={
                    "action": "inventory",
                    "player": session.player.username,
                    "filter_category": filter_category,
                    "item_count": len(filtered_objects),
                    "total_items": len(inventory_objects),
                    "capacity_info": capacity_info,
                    "items": object_list
                }
            )

        except Exception as e:
            logger.error(f"인벤토리 명령어 실행 중 오류: {e}")
            return self.create_error_result("인벤토리를 확인하는 중 오류가 발생했습니다.")


class ExamineCommand(BaseCommand):
    """객체 자세히 보기 명령어"""

    def __init__(self):
        super().__init__(
            name="examine",
            aliases=["exam", "inspect", "look at"],
            description="객체나 대상을 자세히 살펴봅니다",
            usage="examine <대상>"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not self.validate_args(args, min_args=1):
            return self.create_error_result(
                "살펴볼 대상을 지정해주세요.\n사용법: examine <대상>"
            )

        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        target_name = " ".join(args).lower()

        # 자기 자신 살펴보기
        if target_name in ["me", "myself", session.player.username.lower()]:
            return await self._examine_self(session)

        # 다른 플레이어 살펴보기 (추후 구현)
        # if target_name in other_players:
        #     return await self._examine_player(session, target_name)

        # 객체 살펴보기
        return await self._examine_object(session, target_name)

    async def _examine_self(self, session: SessionType) -> CommandResult:
        """자기 자신 살펴보기"""
        response = f"""
👤 {session.player.username}
당신은 이 신비로운 세계에 발을 들인 모험가입니다.
아직 여행을 시작한 지 얼마 되지 않아 평범한 옷을 입고 있습니다.

📧 이메일: {session.player.email or '설정되지 않음'}
🌐 선호 언어: {session.player.preferred_locale}
📅 가입일: {session.player.created_at.strftime('%Y-%m-%d') if session.player.created_at else '알 수 없음'}
        """.strip()

        return self.create_success_result(
            message=response,
            data={
                "action": "examine",
                "target": "self",
                "target_type": "player",
                "player_info": {
                    "username": session.player.username,
                    "email": session.player.email,
                    "locale": session.player.preferred_locale,
                    "created_at": session.player.created_at.isoformat() if session.player.created_at else None
                }
            }
        )

    async def _examine_object(self, session: SessionType, object_name: str) -> CommandResult:
        """객체 살펴보기"""
        # 현재 방 ID 가져오기
        current_room_id = getattr(session, 'current_room_id', None)
        if not current_room_id:
            return self.create_error_result("현재 위치를 확인할 수 없습니다.")

        # GameEngine을 통해 객체 검색
        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

        try:
            target_object = None

            # 1. 현재 방의 객체들에서 검색
            room_objects = await game_engine.world_manager.get_room_objects(current_room_id)
            for obj in room_objects:
                obj_name_en = obj.get_localized_name('en').lower()
                obj_name_ko = obj.get_localized_name('ko').lower()
                if object_name in obj_name_en or object_name in obj_name_ko:
                    target_object = obj
                    break

            # 2. 플레이어 인벤토리에서 검색
            if not target_object:
                inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)
                for obj in inventory_objects:
                    obj_name_en = obj.get_localized_name('en').lower()
                    obj_name_ko = obj.get_localized_name('ko').lower()
                    if object_name in obj_name_en or object_name in obj_name_ko:
                        target_object = obj
                        break

            if not target_object:
                return self.create_error_result(f"'{' '.join(object_name.split())}'을(를) 찾을 수 없습니다.")

            # 객체 정보 표시
            obj_name = target_object.get_localized_name(session.locale)
            obj_description = target_object.get_localized_description(session.locale)
            obj_type = target_object.object_type
            location = "인벤토리" if target_object.location_type == 'inventory' else "이 방"

            response = f"""
🔍 {obj_name}
{obj_description}

📋 종류: {obj_type}
📍 위치: {location}
            """.strip()

            # 객체의 추가 속성이 있다면 표시
            if target_object.properties:
                response += "\n\n🔧 속성:"
                for key, value in target_object.properties.items():
                    response += f"\n• {key}: {value}"

            return self.create_success_result(
                message=response,
                data={
                    "action": "examine",
                    "target": obj_name,
                    "target_type": "object",
                    "object_info": {
                        "id": target_object.id,
                        "name": target_object.name,
                        "description": target_object.description,
                        "type": obj_type,
                        "location_type": target_object.location_type,
                        "location_id": target_object.location_id,
                        "properties": target_object.properties
                    }
                }
            )

        except Exception as e:
            logger.error(f"객체 살펴보기 명령어 실행 중 오류: {e}")
            return self.create_error_result("객체를 살펴보는 중 오류가 발생했습니다.")


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
            return self.create_error_result(
                "착용할 장비를 지정해주세요.\n사용법: equip <장비명>"
            )

        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

        equipment_name = " ".join(args).lower()

        try:
            # 플레이어 인벤토리의 객체들 조회
            inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)

            # 장비 이름으로 검색
            target_equipment = None
            for obj in inventory_objects:
                obj_name_en = obj.get_localized_name('en').lower()
                obj_name_ko = obj.get_localized_name('ko').lower()
                if equipment_name in obj_name_en or equipment_name in obj_name_ko:
                    target_equipment = obj
                    break

            if not target_equipment:
                return self.create_error_result(f"인벤토리에 '{' '.join(args)}'이(가) 없습니다.")

            # 장비할 수 있는지 확인
            if not target_equipment.can_be_equipped():
                return self.create_error_result(f"{target_equipment.get_localized_name(session.locale)}은(는) 착용할 수 없는 아이템입니다.")

            # 이미 착용 중인지 확인
            if target_equipment.is_equipped:
                return self.create_error_result(f"{target_equipment.get_localized_name(session.locale)}은(는) 이미 착용 중입니다.")

            # 같은 슬롯의 다른 장비가 착용되어 있는지 확인 (부위별 1개 제한)
            equipped_in_slot = None
            for obj in inventory_objects:
                if (obj.equipment_slot == target_equipment.equipment_slot and
                    obj.is_equipped and obj.id != target_equipment.id):
                    equipped_in_slot = obj
                    break

            # 기존 장비 해제 (부위별 1개만 착용 가능)
            if equipped_in_slot:
                # 기존 장비의 능력치 보너스 제거
                await self._remove_equipment_bonuses(session.player, equipped_in_slot, game_engine)
                equipped_in_slot.unequip()
                await game_engine.world_manager.update_object(equipped_in_slot)

            # 새 장비 착용
            target_equipment.equip()
            await game_engine.world_manager.update_object(target_equipment)

            # 새 장비의 능력치 보너스 적용
            await self._apply_equipment_bonuses(session.player, target_equipment, game_engine)

            # 성공 메시지
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
            return self.create_error_result("장비를 착용하는 중 오류가 발생했습니다.")

    async def _apply_equipment_bonuses(self, player, equipment, game_engine):
        """장비의 능력치 보너스를 플레이어에게 적용"""
        try:
            if not hasattr(equipment, 'properties') or not equipment.properties:
                return

            # 아이템 속성에서 능력치 보너스 추출
            stats_bonus = equipment.properties.get('stats_bonus', {})
            damage = equipment.properties.get('damage', 0)

            # stats_bonus 적용 (나무 곤봉 등)
            for stat_name, bonus in stats_bonus.items():
                if isinstance(bonus, (int, float)) and bonus > 0:
                    player.stats.add_equipment_bonus(stat_name, int(bonus))

            # damage 속성을 ATK 보너스로 적용 (곤봉 등)
            if damage > 0:
                player.stats.add_equipment_bonus('ATK', damage)

            # 플레이어 정보 업데이트
            await game_engine.session_manager.update_player(player)

        except Exception as e:
            logger.error(f"장비 보너스 적용 중 오류: {e}")

    async def _remove_equipment_bonuses(self, player, equipment, game_engine):
        """장비의 능력치 보너스를 플레이어에서 제거"""
        try:
            if not hasattr(equipment, 'properties') or not equipment.properties:
                return

            # 아이템 속성에서 능력치 보너스 추출
            stats_bonus = equipment.properties.get('stats_bonus', {})
            damage = equipment.properties.get('damage', 0)

            # stats_bonus 제거 (나무 곤봉 등)
            for stat_name, bonus in stats_bonus.items():
                if isinstance(bonus, (int, float)) and bonus > 0:
                    player.stats.remove_equipment_bonus(stat_name, int(bonus))

            # damage 속성 제거 (곤봉 등)
            if damage > 0:
                player.stats.remove_equipment_bonus('ATK', damage)

            # 플레이어 정보 업데이트
            await game_engine.session_manager.update_player(player)

        except Exception as e:
            logger.error(f"장비 보너스 제거 중 오류: {e}")


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
            return self.create_error_result(
                "해제할 장비를 지정해주세요.\n사용법: unequip <장비명>"
            )

        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

        equipment_name = " ".join(args).lower()

        try:
            # 플레이어 인벤토리의 객체들 조회
            inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)

            # 착용 중인 장비 중에서 검색
            target_equipment = None
            for obj in inventory_objects:
                if obj.is_equipped:
                    obj_name_en = obj.get_localized_name('en').lower()
                    obj_name_ko = obj.get_localized_name('ko').lower()
                    if equipment_name in obj_name_en or equipment_name in obj_name_ko:
                        target_equipment = obj
                        break

            if not target_equipment:
                return self.create_error_result(f"착용 중인 '{' '.join(args)}'을(를) 찾을 수 없습니다.")

            # 장비의 능력치 보너스 제거
            await self._remove_equipment_bonuses(session.player, target_equipment, game_engine)

            # 장비 해제
            target_equipment.unequip()
            await game_engine.world_manager.update_object(target_equipment)

            # 성공 메시지
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
            return self.create_error_result("장비를 해제하는 중 오류가 발생했습니다.")

    async def _remove_equipment_bonuses(self, player, equipment, game_engine):
        """장비의 능력치 보너스를 플레이어에서 제거"""
        try:
            if not hasattr(equipment, 'properties') or not equipment.properties:
                return

            # 아이템 속성에서 능력치 보너스 추출
            stats_bonus = equipment.properties.get('stats_bonus', {})
            damage = equipment.properties.get('damage', 0)

            # stats_bonus 제거 (나무 곤봉 등)
            for stat_name, bonus in stats_bonus.items():
                if isinstance(bonus, (int, float)) and bonus > 0:
                    player.stats.remove_equipment_bonus(stat_name, int(bonus))

            # damage 속성 제거 (곤봉 등)
            if damage > 0:
                player.stats.remove_equipment_bonus('ATK', damage)

            # 플레이어 정보 업데이트
            await game_engine.session_manager.update_player(player)

        except Exception as e:
            logger.error(f"장비 보너스 제거 중 오류: {e}")


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
            return self.create_error_result(
                "사용할 아이템을 지정해주세요.\n사용법: use <아이템명>"
            )

        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

        item_name = " ".join(args).lower()

        try:
            # 플레이어 인벤토리의 객체들 조회
            inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)

            # 아이템 이름으로 검색
            target_item = None
            for obj in inventory_objects:
                obj_name_en = obj.get_localized_name('en').lower()
                obj_name_ko = obj.get_localized_name('ko').lower()
                if item_name in obj_name_en or item_name in obj_name_ko:
                    target_item = obj
                    break

            if not target_item:
                return self.create_error_result(f"인벤토리에 '{' '.join(args)}'이(가) 없습니다.")

            # 사용 가능한 아이템인지 확인
            if target_item.category != 'consumable':
                return self.create_error_result(f"{target_item.get_localized_name(session.locale)}은(는) 사용할 수 없는 아이템입니다.")

            # 아이템 사용 효과 처리 (기본 구현)
            item_name_display = target_item.get_localized_name(session.locale)
            effect_message = ""

            # 아이템 속성에 따른 효과 처리
            if 'heal_amount' in target_item.properties:
                heal_amount = target_item.properties.get('heal_amount', 10)
                effect_message = f"체력이 {heal_amount} 회복되었습니다."
            elif 'mana_amount' in target_item.properties:
                mana_amount = target_item.properties.get('mana_amount', 10)
                effect_message = f"마나가 {mana_amount} 회복되었습니다."
            else:
                effect_message = f"{item_name_display}을(를) 사용했습니다."

            # 소모품은 사용 후 제거
            await game_engine.world_manager.remove_object(target_item.id)

            # 성공 메시지
            message = f"💊 {item_name_display}을(를) 사용했습니다.\n{effect_message}"

            return self.create_success_result(
                message=message,
                data={
                    "action": "use",
                    "item_id": target_item.id,
                    "item_name": item_name_display,
                    "effect": effect_message
                }
            )

        except Exception as e:
            logger.error(f"아이템 사용 명령어 실행 중 오류: {e}")
            return self.create_error_result("아이템을 사용하는 중 오류가 발생했습니다.")