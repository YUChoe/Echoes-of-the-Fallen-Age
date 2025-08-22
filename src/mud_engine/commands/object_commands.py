# -*- coding: utf-8 -*-
"""객체 상호작용 명령어들"""

import logging
from typing import List

from .base import BaseCommand, CommandResult, CommandResultType
from ..server.session import Session

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

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
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
                obj_name_en = obj.get_localized_name('en').lower()
                obj_name_ko = obj.get_localized_name('ko').lower()
                if object_name in obj_name_en or object_name in obj_name_ko:
                    target_object = obj
                    break

            if not target_object:
                return self.create_error_result(f"'{' '.join(args)}'을(를) 찾을 수 없습니다.")

            # 객체를 플레이어 인벤토리로 이동
            success = await game_engine.world_manager.move_object_to_inventory(
                target_object.id, session.player.id
            )

            if not success:
                return self.create_error_result("객체를 획득할 수 없습니다.")

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
            logger.error(f"객체 획득 명령어 실행 중 오류: {e}")
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

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
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
            usage="inventory"
        )

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
        if not session.is_authenticated or not session.player:
            return self.create_error_result("인증되지 않은 사용자입니다.")

        # GameEngine을 통해 인벤토리 조회
        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result("게임 엔진에 접근할 수 없습니다.")

        try:
            # 플레이어 인벤토리의 객체들 조회
            inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)

            if not inventory_objects:
                return self.create_info_result("🎒 인벤토리가 비어있습니다.")

            # 인벤토리 목록 생성
            response = f"🎒 {session.player.username}의 인벤토리:\n"

            object_list = []
            for obj in inventory_objects:
                obj_name = obj.get_localized_name(session.locale)
                obj_type = obj.object_type
                response += f"• {obj_name} ({obj_type})\n"

                object_list.append({
                    "id": obj.id,
                    "name": obj_name,
                    "type": obj_type,
                    "description": obj.get_localized_description(session.locale)
                })

            response += f"\n총 {len(inventory_objects)}개의 아이템을 소지하고 있습니다."

            return self.create_success_result(
                message=response.strip(),
                data={
                    "action": "inventory",
                    "player": session.player.username,
                    "item_count": len(inventory_objects),
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

    async def execute(self, session: Session, args: List[str]) -> CommandResult:
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

    async def _examine_self(self, session: Session) -> CommandResult:
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

    async def _examine_object(self, session: Session, object_name: str) -> CommandResult:
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