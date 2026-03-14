#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""컨테이너(상자) 관련 명령어들"""

import logging
import json
from typing import List, Dict, Any, Optional
from .base import BaseCommand, CommandResult
from ..core.types import SessionType

logger = logging.getLogger(__name__)


class OpenCommand(BaseCommand):
    """상자나 컨테이너를 여는 명령어"""

    def __init__(self):
        super().__init__(
            name="open",
            aliases=["o"],
            description="상자나 컨테이너를 열어 내용물을 확인합니다",
            usage="open <대상> 또는 open <번호>"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        if not args:
            return self.create_error_result("사용법: open <대상> 또는 open <번호>")

        target = args[0]
        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

        # 숫자 인자 처리 (엔티티 번호)
        if target.isdigit():
            entity_number = int(target)
            return await self._open_by_number(session, game_engine, entity_number)
        # else:
        #     return await self._open_by_name(session, game_engine, target)
        logger.info("네임으로는 찾는 기능이 없음")
        return self.create_error_result("네임으로는 찾는 기능이 없음")

    async def _open_by_number(self, session: SessionType, game_engine, entity_number: int) -> CommandResult:
        """번호로 상자 열기"""
        # entity_map = getattr(session, 'room_entity_map', {})
        # if not entity_map:
        #     entity_map = getattr(session, 'inventory_entity_map', {})
        # # 이게 or 이어야 함
        # if not entity_map:
        #     return self.create_error_result("방+inv 엔티티를 찾을 수 없습니다.")

        # if entity_number not in entity_map:
        #     logger.info(f"'{entity_number}'번 대상을 찾을 수 없습니다.")
        #     logger.info(f"entity_map[{entity_map}]")
        #     return self.create_error_result(f"'{entity_number}'번 대상을 찾을 수 없습니다.")

        # entity_info = entity_map[entity_number]
        # if entity_info.get('type') != 'object':
        #     logger.info(f"'{entity_number}'번은 열 수 있는 대상이 아닙니다.")
        #     return self.create_error_result(f"'{entity_number}'번은 열 수 있는 대상이 아닙니다.")

        # container_id = entity_info.get('id')
        # container_name = entity_info.get('name', '알 수 없는 상자')

        # 상자 찾기 - 방에서 먼저 그 다음에 인벤토리. 근데 인덱스숫자만 보고도 알 수 있긴 한데
        # container_command:202
        container_id, container_name = await self._find_container_in_room(session, game_engine, entity_number)
        if not container_id:
                container_id, container_name = await self._find_container_in_inv(session, game_engine, entity_number)
        if not container_id:
            # 그래도 없으면
            logger.info(f"'{entity_number}' 상자를 찾을 수 없습니다.")
            return self.create_error_result(f"'{entity_number}' 상자를 찾을 수 없습니다.")

        logger.info(f"found [{entity_number}] container_id[{container_id}] container_name[{container_name}]")

        return await self._open_container(session, game_engine, container_id, container_name)

    # async def _open_by_name(self, session: SessionType, game_engine, target_name: str) -> CommandResult:
    #     """이름으로 상자 열기"""
    #     # 현재 방의 오브젝트들 중에서 찾기
    #     current_room_id = getattr(session, 'current_room_id', None)
    #     if not current_room_id:
    #         return self.create_error_result("현재 위치를 확인할 수 없습니다.")

    #     try:
    #         room_objects = await game_engine.world_manager.get_room_objects(current_room_id)

    #         # 이름으로 매칭되는 컨테이너 찾기
    #         locale = session.player.preferred_locale if session.player else "en"
    #         for obj in room_objects:
    #             obj_name = obj.get_localized_name(locale).lower()
    #             if target_name.lower() in obj_name:
    #                 # 컨테이너인지 확인
    #                 if self._is_container(obj):
    #                     return await self._open_container(session, game_engine, obj.id, obj.get_localized_name(locale))

    #         return self.create_error_result(f"'{target_name}'을(를) 찾을 수 없거나 열 수 없는 대상입니다.")

    #     except Exception as e:
    #         logger.error(f"상자 열기 오류: {e}")
    #         return self.create_error_result("상자를 여는 중 오류가 발생했습니다.")

    async def _find_container_in_room(self, session: SessionType, game_engine, entity_number: int) -> tuple[Optional[str], Optional[str]]:
        """상자 찾기 - 번호 로만 TODO: 나중에 id 로 """
        entity_map = getattr(session, 'room_entity_map', {})
        if entity_number in entity_map:
            entity_info = entity_map[entity_number]
            if entity_info.get('type') == 'object':
                # 컨테이너인지 확인
                obj = entity_info.get('entity')
                if obj and self._is_container(obj):
                    return entity_info.get('id'), entity_info.get('name') # TODO: name 을 locale 로
        return None, None

    async def _find_container_in_inv(self, session: SessionType, game_engine, entity_number: int) -> tuple[Optional[str], Optional[str]]:
        """inv 에서 상자 찾기 TODO: 나중에 id 로 """
        inventory_entity = getattr(session, 'inventory_entity_map', {})  # session 을 dict로 쓸 수 있네.. 흐음..
        logger.info(f"inventory_entity from session cnt[{len(inventory_entity.keys())}]")
        if entity_number in inventory_entity:
            entity_info = inventory_entity[entity_number]['objects'][0]
            logger.info(f"entity_info[{entity_info}]")
            if self._is_container(entity_info):
                return entity_info.id, entity_info.name  # TODO: name 을 locale 로
            # if entity_info.get('type') == 'object':
            #     # 컨테이너인지 확인
            #     obj = entity_info.get('entity')  # 기존엔 왜 됐지???
            #     if obj and self._is_container(obj):
            #         return entity_info.get('id'), entity_info.get('name')# TODO: name 을 locale 로
        return None, None

        # entity_info = entity_map[entity_number]
        # if entity_info.get('type') != 'object':
        #     logger.info(f"'{entity_number}'번은 열 수 있는 대상이 아닙니다.")
        #     return self.create_error_result(f"'{entity_number}'번은 열 수 있는 대상이 아닙니다.")

    async def _find_item_in_inv(self, session: SessionType, game_engine, entity_number: int) -> tuple[Optional[str], Optional[str]]:
        inventory_entity = getattr(session, 'inventory_entity_map', {})  # session 을 dict로 쓸 수 있네.. 흐음..
        logger.info(f"inventory_entity from session cnt[{len(inventory_entity.keys())}]")
        if entity_number in inventory_entity:
            game_obj = inventory_entity[entity_number]['objects'][0]
            logger.info(f"found [{entity_number}] game_obj[{game_obj}]")
            # TODO: name 을 locale 로
            return game_obj.id, game_obj.name
        return None, None

    def _is_container(self, gameobj) -> bool:
        """오브젝트가 컨테이너인지 확인"""
        try:
            properties = gameobj.properties if hasattr(gameobj, 'properties') else {}
            if isinstance(properties, str):
                properties = json.loads(properties)

            return properties.get('is_container', False)
        except:
            return False

    async def _open_container(self, session: SessionType, game_engine, container_id: str, container_name: str) -> CommandResult:
        """컨테이너 열기 및 내용물 표시"""
        try:
            # 컨테이너 내부 아이템들 조회
            container_items = await game_engine.world_manager.get_container_items(container_id)

            locale = session.player.preferred_locale if session.player else "en"

            if not container_items:
                message = f"""
📦 {container_name}을(를) 열었습니다.

상자가 비어있습니다.

사용법:
- put <아이템> in <상자번호>: 아이템을 상자에 넣기
- take <아이템> from <상자번호>: 상자에서 아이템 꺼내기
                """.strip()
            else:
                # 아이템 목록 생성
                item_list = []
                for i, item in enumerate(container_items, 1):
                    item_name = item.get_localized_name(locale)
                    quantity = getattr(item, 'quantity', 1) if hasattr(item, 'quantity') else 1
                    if quantity > 1:
                        item_list.append(f"  [{i}] {item_name} x{quantity}")
                    else:
                        item_list.append(f"  [{i}] {item_name}")

                message = f"""
📦 {container_name}을(를) 열었습니다.

상자 안의 아이템들:
{chr(10).join(item_list)}

사용법:
- put <아이템> in <상자번호>: 아이템을 상자에 넣기
- take <아이템번호> from <상자번호>: 상자에서 아이템 꺼내기
                """.strip()

            return self.create_success_result(
                message=message,
                data={
                    "action": "open_container",
                    "container_id": container_id,
                    "container_name": container_name,
                    "item_count": len(container_items)
                }
            )

        except Exception as e:
            logger.error(f"컨테이너 열기 오류: {e}")
            return self.create_error_result("상자를 여는 중 오류가 발생했습니다.")


class PutCommand(BaseCommand):
    """아이템을 상자에 넣는 명령어"""

    def __init__(self):
        super().__init__(
            name="put",
            aliases=["place"],
            description="아이템을 상자에 넣습니다",
            usage="put <아이템> in <상자번호>"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        if len(args) < 3 or args[-2].lower() != "in":
            return self.create_error_result("사용법: put <아이템> in <상자번호>")

        logger.info(f"PutCommand.excute invoked args[{args}]")
        # 마지막 인자가 상자 번호, 그 앞의 "in"을 제외한 나머지가 아이템명
        container_target = args[-1]
        item_entity_id = " ".join(args[:-2])

        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

        try:
            # 상자 찾기 - 방에서 먼저 그 다음에 인벤토리. 근데 인덱스숫자만 보고도 알 수 있긴 한데
            container_id, container_name = await self._find_container_in_room(session, game_engine, container_target)
            if not container_id:
                    container_id, container_name = await self._find_container_in_inv(session, game_engine, container_target)
            if not container_id:
                # 그래도 없으면
                logger.info(f"'{container_target}' 상자를 찾을 수 없습니다.")
                return self.create_error_result(f"'{container_target}' 상자를 찾을 수 없습니다.")

            logger.info(f"found [{container_target}] container_id[{container_id}] container_name[{container_name}]")

            # 플레이어 인벤토리에서 아이템 찾기
            # inventory_items = await game_engine.world_manager.get_inventory_objects(session.player.id)
            # target_item = None

            # locale = session.player.preferred_locale if session.player else "en"

            # for item in inventory_items:
            #     if item_name.lower() in item.get_localized_name(locale).lower():
            #         target_item = item
            #         break

            # 인덱스로 찾기
            target_item_id, target_item_name = await self._find_item_in_inv(session, game_engine, item_entity_id)

            if not target_item_id:
                logger.info((f"인벤토리에서 '{item_entity_id}'을(를) 찾을 수 없습니다."))
                return self.create_error_result(f"인벤토리에서 '{item_entity_id}'을(를) 찾을 수 없습니다.")
            logger.info(f"found [{item_entity_id}] target_item_id[{target_item_id}] target_item_name[{target_item_name}]")
            # 아이템을 상자로 이동
            await game_engine.world_manager.move_item_to_container(target_item_id, container_id)

            message = f"✅ {target_item_name}을(를) {container_name}에 넣었습니다."

            return self.create_success_result(
                message=message,
                data={
                    "action": "put_item",
                    "item_name": target_item_name,
                    "container_name": container_name
                }
            )

        except Exception as e:
            logger.error(f"아이템 넣기 오류: {e}")
            return self.create_error_result("아이템을 넣는 중 오류가 발생했습니다.")

    async def _find_container_in_room(self, session: SessionType, game_engine, target: str) -> tuple[Optional[str], Optional[str]]:
        """상자 찾기 - 번호 로만 TODO: 나중에 id 로 """

        if target.isdigit():
            entity_number = int(target)
            entity_map = getattr(session, 'room_entity_map', {})
            if entity_number in entity_map:
                entity_info = entity_map[entity_number]
                if entity_info.get('type') == 'object':
                    # 컨테이너인지 확인
                    obj = entity_info.get('entity')  # !!! 여기서 에러 날 듯
                    if obj and self._is_container(obj):
                        return entity_info.get('id'), entity_info.get('name') # TODO: name 을 locale 로
        return None, None

    async def _find_container_in_inv(self, session: SessionType, game_engine, target: str) -> tuple[Optional[str], Optional[str]]:
        """inv 에서 상자 찾기 TODO: 나중에 id 로 """
        if target.isdigit():
            entity_number = int(target)
            inventory_entity = getattr(session, 'inventory_entity_map', {})  # session 을 dict로 쓸 수 있네.. 흐음..
            logger.info(f"inventory_entity from session cnt[{len(inventory_entity.keys())}]")
            if entity_number in inventory_entity:
                entity_info = inventory_entity[entity_number]['objects'][0]
                logger.info(f"entity_info[{entity_info}]")
                if self._is_container(entity_info):
                    return entity_info.id, entity_info.name  # TODO: name 을 locale 로
        return None, None

    async def _find_item_in_inv(self, session: SessionType, game_engine, target: str) -> tuple[Optional[str], Optional[str]]:
        if target.isdigit():
            entity_number = int(target)
            inventory_entity = getattr(session, 'inventory_entity_map', {})  # session 을 dict로 쓸 수 있네.. 흐음..
            logger.info(f"inventory_entity from session cnt[{len(inventory_entity.keys())}]")
            if entity_number in inventory_entity:
                game_obj = inventory_entity[entity_number]['objects'][0]
                logger.info(f"found [{entity_number}] game_obj[{game_obj}]")
                # TODO: name 을 locale 로
                return game_obj.id, game_obj.name
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