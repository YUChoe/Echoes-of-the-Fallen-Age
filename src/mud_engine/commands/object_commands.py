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
                "획득할 객체를 지정해주세요.\n사용법: get <객체명> 또는 take <번호> from <상자번호>"
            )

        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        # "take X from Y" 구문 처리
        if len(args) >= 3 and args[-2].lower() == "from":
            return await self._take_from_container(session, args)

        # 일반적인 get/take 처리
        return await self._take_from_room(session, args)

    async def _take_from_container(self, session: SessionType, args: List[str]) -> CommandResult:
        """컨테이너에서 아이템을 가져오는 처리"""
        try:
            # take <item_number> from <container_number> 구문 파싱
            item_arg = args[0]
            container_arg = args[-1]

            # 숫자 인자 검증
            try:
                item_number = int(item_arg)
                container_number = int(container_arg)
            except ValueError:
                return self.create_error_result("올바른 번호를 입력해주세요. 예: take 1 from 11")

            # 게임 엔진 접근
            game_engine = getattr(session, 'game_engine', None)
            if not game_engine:
                return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

            # 컨테이너에서 아이템 가져오기
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
            return self.create_error_result("아이템을 가져오는 중 오류가 발생했습니다.")

    async def _take_from_room(self, session: SessionType, args: List[str]) -> CommandResult:
        """방에서 아이템을 가져오는 처리"""
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
            # 번호로 입력된 경우 처리
            target_group = None
            if object_name.isdigit():
                item_num = int(object_name)
                entity_map = getattr(session, 'room_entity_map', {})

                if item_num in entity_map and entity_map[item_num]['type'] == 'object':
                    target_object = entity_map[item_num]['entity']
                    # 단일 객체를 그룹 형태로 변환
                    target_group = {
                        'objects': [target_object],
                        'name_en': target_object.get_localized_name('en'),
                        'name_ko': target_object.get_localized_name('ko'),
                        'display_name_en': target_object.get_localized_name('en'),
                        'display_name_ko': target_object.get_localized_name('ko'),
                        'id': target_object.id
                    }
                else:
                    return self.create_error_result(
                        f"번호 [{item_num}]에 해당하는 아이템을 찾을 수 없습니다."
                    )
            else:
                # 현재 방의 객체들 조회
                room_objects = await game_engine.world_manager.get_room_objects(current_room_id)

                # stackable 오브젝트 그룹화
                grouped_objects = game_engine.world_manager._group_stackable_objects(room_objects)

                # 객체 이름으로 검색 (그룹화된 오브젝트에서)
                for group in grouped_objects:
                    group_name_en = group['name_en'].lower()
                    group_name_ko = group['name_ko'].lower()
                    if object_name in group_name_en or object_name in group_name_ko:
                        target_group = group
                        break

            if not target_group:
                return self.create_error_result(f"'{' '.join(args)}'을(를) 찾을 수 없습니다.")

            # stackable 오브젝트인 경우 모든 인스턴스를 가져감
            target_objects = target_group['objects']

            # 무게 제한 확인 (모든 오브젝트의 총 무게)
            total_weight = sum(obj.weight for obj in target_objects)
            current_inventory = await game_engine.world_manager.get_inventory_objects(session.player.id)

            if not session.player.can_carry_more(current_inventory, total_weight):
                capacity_info = session.player.get_carry_capacity_info(current_inventory)
                return self.create_error_result(
                    f"무게 제한으로 인해 {target_group['display_name_ko']}을(를) 들 수 없습니다.\n"
                    f"현재 소지 용량: {capacity_info['current_weight']:.1f}kg / {capacity_info['max_weight']:.1f}kg\n"
                    f"아이템 총 무게: {total_weight:.1f}kg"
                )

            # 모든 오브젝트를 플레이어 인벤토리로 이동
            moved_objects = []
            for obj in target_objects:
                success = await game_engine.world_manager.move_object_to_inventory(
                    obj.id, session.player.id
                )
                if success:
                    moved_objects.append(obj)

            if not moved_objects:
                return self.create_error_result("객체를 획득할 수 없습니다.")

            # 객체 획득 이벤트 발행
            from ..core.event_bus import Event, EventType
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

            # 성공 메시지
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
            return self.create_error_result("객체를 획득하는 중 오류가 발생했습니다.")
            moved_objects = []
            for obj in target_objects:
                try:
                    success = await game_engine.world_manager.move_object_to_inventory(
                        obj.id, session.player.id
                    )
                    if success:
                        moved_objects.append(obj)
                    logger.debug(f"객체 이동 결과 ({obj.id}): {success}")
                except Exception as move_error:
                    logger.error(f"객체 이동 중 오류 ({obj.id}): {move_error}", exc_info=True)

            if not moved_objects:
                return self.create_error_result("객체를 획득할 수 없습니다.")

            # 객체 획득 이벤트 발행 (각 오브젝트별로)
            try:
                from ..core.event_bus import Event, EventType
                for obj in moved_objects:
                    await game_engine.event_bus.publish(Event(
                        event_type=EventType.OBJECT_PICKED_UP,
                        source=session.session_id,
                        room_id=current_room_id,
                        data={
                            "player_id": session.player.id,
                            "player_name": session.player.username,
                            "object_id": obj.id,
                            "object_name": obj.get_localized_name(session.locale),
                            "room_id": current_room_id
                        }
                    ))
                logger.debug(f"이벤트 발행 완료 ({len(moved_objects)}개 오브젝트)")
            except Exception as event_error:
                logger.error(f"이벤트 발행 중 오류: {event_error}", exc_info=True)
                # 이벤트 발행 실패해도 명령어는 성공으로 처리

            # 성공 메시지
            if len(moved_objects) == 1:
                obj_name = moved_objects[0].get_localized_name(session.locale)
                player_message = f"📦 {obj_name}을(를) 획득했습니다."
                broadcast_message = f"📦 {session.player.username}님이 {obj_name}을(를) 가져갔습니다."
            else:
                # stackable 오브젝트 여러 개
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
        logger.info(f"current_room_id[{current_room_id}]")
        # GameEngine을 통해 객체 버리기 처리
        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

        # object_name = " ".join(args).lower()
        object_entity = int(args[0])
        logger.info(f"DropCommand execute invoked object_entity[{object_entity}]")

        inventory_entity = getattr(session, 'inventory_entity_map', {})  # session 을 dict로 쓸 수 있네.. 흐음..
        logger.info(f"inventory_entity from session cnt[{len(inventory_entity.keys())}]")

        try:
            # 객체를 inventory_entity_map 로 검색
            target_object = inventory_entity[object_entity]['objects'][0]  # 첫번째 아이템 한번에 하나씩 옮긴다면
            logger.info(f"target_object[{target_object.to_simple()}]")
            if not target_object:
                logger.info(f"인벤토리에 '{' '.join(args)}'이(가) 없습니다.")
                return self.create_error_result(f"인벤토리에 '{' '.join(args)}'이(가) 없습니다.")

            # 객체를 현재 방으로 이동
            success = await game_engine.world_manager.move_object_to_room(target_object.id, current_room_id)

            if not success:
                logger.error("객체를 버릴 수 없습니다.")
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
            broadcast_message = f"📦 {session.player.username}가 {obj_name}을(를) 버렸습니다."

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

        # 사용자 언어 설정 가져오기
        from ..core.localization import get_message
        locale = getattr(session, 'preferred_locale', 'en') if hasattr(session, 'preferred_locale') else 'en'
        if hasattr(session, 'player') and session.player and hasattr(session.player, 'preferred_locale'):
            locale = session.player.preferred_locale

        inventory_entity = getattr(session, 'inventory_entity_map', {})  # session 을 dict로 쓸 수 있네.. 흐음..
        logger.info(f"inventory_entity from session cnt[{len(inventory_entity.keys())}]")

        # 카테고리 필터링
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
            # 플레이어 인벤토리의 객체들 조회
            inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)

            if not inventory_objects:
                return self.create_info_result(get_message("inventory.empty", locale))

            # logger.info(f"inventory_objects[{inventory_objects}]")
            _cnt = 0
            for _item in inventory_objects:
                _cnt += 1
                logger.debug(f"inventory_objects[{_cnt}]{_item.to_simple()}]")
            # 카테고리별 필터링 ?? 이게 뭐하는거임?
            if filter_category:
                if filter_category == 'equipped':
                    filtered_objects = [obj for obj in inventory_objects if obj.is_equipped]
                else:
                    filtered_objects = [obj for obj in inventory_objects if obj.category == filter_category]
            else:
                filtered_objects = inventory_objects
            logger.debug(f"filter_category[{filter_category}] filtered_objects[{filtered_objects}]")
            # 나중에 착용중인 아이템은 [equipped] 라고 표시 됨

            if not filtered_objects:
                category_name = filter_category if filter_category else get_message("inventory.category_all", locale)
                return self.create_info_result(
                    get_message("inventory.category_empty", locale, category=category_name)
                )

            # 소지 용량 정보
            capacity_info = session.player.get_carry_capacity_info(inventory_objects)
            logger.debug(f"capacity_info[{capacity_info}]")

            # 인벤토리 목록 생성
            response = get_message("inventory.title", locale, username=session.player.username)
            if filter_category:
                response += f" ({filter_category})"

            logger.debug(f"[{response}]") # 중간점검 🎒 player5426's inventory:

            # 용량 정보 표시
            # response += get_message("inventory.capacity", locale,
            #                       current=f"{capacity_info['current_weight']:.1f}",
            #                       max=f"{capacity_info['max_weight']:.1f}",
            #                       percentage=f"{capacity_info['percentage']:.1f}") + "\n"
            # if capacity_info['is_overloaded']:
            #     response += get_message("inventory.overloaded", locale) + "\n"
            response += f" {capacity_info['current_weight']:.1f}/{capacity_info['max_weight']:.1f} ({capacity_info['percentage']:.1f}%)"
            response += "\n\n"

            logger.info(f"[{response}]")

            # 카테고리별로 정렬 및 같은 아이템 집계
            items: Dict[str, Dict] = {}
            for obj in filtered_objects:
                # 아이템 이름으로 그룹화 (카테고리 구분 없이)
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

            # 하나의 목록으로 표시 + entity index TODO: WIP
            _idx = 100
            inventory_entity = {}
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
                equipped_mark = get_message("inventory.equipped_marker", locale) if equipped_count > 0 else ""

                response += f"• [{_idx}] {obj_name}{count_display} {weight_display}{equipped_mark}\n"
                inventory_entity[_idx] = item_data
                _idx += 1

            for _idx in inventory_entity.keys():
                _list = inventory_entity[_idx]['objects']
                for gobj in _list:
                    logger.info(f"inventory_entity[{_idx}] {gobj.to_simple()}")

            # session 에 저장
            # TODO: 이걸 inv 명령 때만이 아니라 다른 상황에도 갱신이 되어야 함
            session.inventory_entity_map = inventory_entity

            response += "\n" # + get_message("inventory.total_items", locale, count=len(filtered_objects))

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

            # stats_bonus 적용 (나무 곤봉 등)
            for stat_name, bonus in stats_bonus.items():
                if isinstance(bonus, (int, float)) and bonus > 0:
                    player.stats.add_equipment_bonus(stat_name, int(bonus))

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

            # stats_bonus 제거 (나무 곤봉 등)
            for stat_name, bonus in stats_bonus.items():
                if isinstance(bonus, (int, float)) and bonus > 0:
                    player.stats.remove_equipment_bonus(stat_name, int(bonus))

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

            # stats_bonus 제거 (나무 곤봉 등)
            for stat_name, bonus in stats_bonus.items():
                if isinstance(bonus, (int, float)) and bonus > 0:
                    player.stats.remove_equipment_bonus(stat_name, int(bonus))

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
    async def _take_from_container(self, session: SessionType, args: List[str]) -> CommandResult:
        """컨테이너에서 아이템 가져오기 (take X from Y)"""
        container_target = args[-1]  # 마지막 인자가 컨테이너
        item_target = " ".join(args[:-2])  # "from" 앞까지가 아이템명

        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

        try:
            # 컨테이너 찾기
            container_id, container_name = await self._find_container(session, game_engine, container_target)
            if not container_id:
                return self.create_error_result(f"'{container_target}' 상자를 찾을 수 없습니다.")

            # 컨테이너 내부 아이템들 조회
            container_items = await game_engine.world_manager.get_container_items(container_id)
            if not container_items:
                return self.create_error_result(f"{container_name}이(가) 비어있습니다.")

            # 아이템 찾기 (번호 또는 이름으로)
            target_item = None
            locale = session.player.preferred_locale if session.player else "en"

            if item_target.isdigit():
                # 번호로 찾기
                item_index = int(item_target) - 1  # 1-based index를 0-based로 변환
                if 0 <= item_index < len(container_items):
                    target_item = container_items[item_index]
            else:
                # 이름으로 찾기
                for item in container_items:
                    if item_target.lower() in item.get_localized_name(locale).lower():
                        target_item = item
                        break

            if not target_item:
                return self.create_error_result(f"'{item_target}'을(를) {container_name}에서 찾을 수 없습니다.")

            # 무게 제한 확인
            current_inventory = await game_engine.world_manager.get_inventory_objects(session.player.id)
            if not session.player.can_carry_more(current_inventory, target_item.weight):
                capacity_info = session.player.get_carry_capacity_info(current_inventory)
                return self.create_error_result(
                    f"무게 제한으로 인해 {target_item.get_localized_name(locale)}을(를) 들 수 없습니다.\n"
                    f"현재 소지 용량: {capacity_info['current_weight']:.1f}kg / {capacity_info['max_weight']:.1f}kg\n"
                    f"아이템 무게: {target_item.weight:.1f}kg"
                )

            # 아이템을 플레이어 인벤토리로 이동
            success = await game_engine.world_manager.move_item_from_container(
                target_item.id, "INVENTORY", session.player.id
            )

            if not success:
                return self.create_error_result("아이템을 가져오는 중 오류가 발생했습니다.")

            item_name = target_item.get_localized_name(locale)
            message = f"📦 {container_name}에서 {item_name}을(를) 가져왔습니다."

            return self.create_success_result(
                message=message,
                data={
                    "action": "take_from_container",
                    "item_name": item_name,
                    "container_name": container_name,
                    "item_id": target_item.id
                }
            )

        except Exception as e:
            logger.error(f"컨테이너에서 아이템 가져오기 오류: {e}")
            return self.create_error_result("아이템을 가져오는 중 오류가 발생했습니다.")

    async def _take_from_room(self, session: SessionType, args: List[str]) -> CommandResult:
        """방에서 아이템 가져오기 (기존 로직)"""
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
            # 번호로 입력된 경우 처리
            target_group = None
            if object_name.isdigit():
                item_num = int(object_name)
                entity_map = getattr(session, 'room_entity_map', {})

                if item_num in entity_map and entity_map[item_num]['type'] == 'object':
                    target_object = entity_map[item_num]['entity']
                    # 단일 객체를 그룹 형태로 변환
                    target_group = {
                        'objects': [target_object],
                        'name_en': target_object.get_localized_name('en'),
                        'name_ko': target_object.get_localized_name('ko'),
                        'display_name_en': target_object.get_localized_name('en'),
                        'display_name_ko': target_object.get_localized_name('ko'),
                        'id': target_object.id
                    }
                else:
                    return self.create_error_result(
                        f"번호 [{item_num}]에 해당하는 아이템을 찾을 수 없습니다."
                    )
            else:
                # 현재 방의 객체들 조회
                room_objects = await game_engine.world_manager.get_room_objects(current_room_id)

                # stackable 오브젝트 그룹화
                grouped_objects = game_engine.world_manager._group_stackable_objects(room_objects)

                # 객체 이름으로 검색 (그룹화된 오브젝트에서)
                for group in grouped_objects:
                    group_name_en = group['name_en'].lower()
                    group_name_ko = group['name_ko'].lower()
                    if object_name in group_name_en or object_name in group_name_ko:
                        target_group = group
                        break

            if not target_group:
                return self.create_error_result(f"'{' '.join(args)}'을(를) 찾을 수 없습니다.")

            # stackable 오브젝트인 경우 모든 인스턴스를 가져감
            target_objects = target_group['objects']

            # 무게 제한 확인 (모든 오브젝트의 총 무게)
            total_weight = sum(obj.weight for obj in target_objects)
            current_inventory = await game_engine.world_manager.get_inventory_objects(session.player.id)

            if not session.player.can_carry_more(current_inventory, total_weight):
                capacity_info = session.player.get_carry_capacity_info(current_inventory)
                return self.create_error_result(
                    f"무게 제한으로 인해 {target_group['display_name_ko']}을(를) 들 수 없습니다.\n"
                    f"현재 소지 용량: {capacity_info['current_weight']:.1f}kg / {capacity_info['max_weight']:.1f}kg\n"
                    f"아이템 총 무게: {total_weight:.1f}kg"
                )

            # 모든 오브젝트를 인벤토리로 이동
            moved_objects = []
            for obj in target_objects:
                success = await game_engine.world_manager.move_object_to_inventory(obj.id, session.player.id)
                if success:
                    moved_objects.append(obj)

            if not moved_objects:
                return self.create_error_result("객체를 획득할 수 없습니다.")

            # 성공 메시지 생성
            if len(moved_objects) == 1:
                # 단일 오브젝트
                obj_name = moved_objects[0].get_localized_name(session.locale)
                player_message = f"📦 {obj_name}을(를) 획득했습니다."
                broadcast_message = f"📦 {session.player.username}님이 {obj_name}을(를) 가져갔습니다."
            else:
                # stackable 오브젝트 여러 개
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
            import traceback
            logger.error(f"객체 획득 명령어 실행 중 오류: {e}")
            logger.error(f"스택 트레이스: {traceback.format_exc()}")
            return self.create_error_result("객체를 획득하는 중 오류가 발생했습니다.")

    async def _find_container(self, session: SessionType, game_engine, target: str) -> tuple[str | None, str | None]:
        """상자 찾기 (번호 또는 이름으로)"""
        if target.isdigit():
            # 번호로 찾기
            entity_number = int(target)
            entity_map = getattr(session, 'room_entity_map', {})
            if entity_number in entity_map:
                entity_info = entity_map[entity_number]
                if entity_info.get('type') == 'object':
                    # 컨테이너인지 확인
                    obj = entity_info.get('entity')
                    if obj and self._is_container(obj):
                        return entity_info.get('id'), entity_info.get('name')

        return None, None

    def _is_container(self, obj) -> bool:
        """오브젝트가 컨테이너인지 확인"""
        try:
            properties = obj.properties if hasattr(obj, 'properties') else {}
            if isinstance(properties, str):
                import json
                properties = json.loads(properties)

            return properties.get('is_container', False)
        except:
            return False