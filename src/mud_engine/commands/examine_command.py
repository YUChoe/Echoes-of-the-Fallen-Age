# -*- coding: utf-8 -*-
"""객체 자세히 보기 명령어"""

import logging
from typing import List

from .base import BaseCommand, CommandResult
from .utils import get_user_locale
from ..core.types import SessionType
from ..core.localization import get_localization_manager

logger = logging.getLogger(__name__)
I18N = get_localization_manager()


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
            return self.create_error_result(I18N.get_message("obj.unauthenticated", get_user_locale(session)))

        target_name = " ".join(args).lower()

        if target_name in ["me", "myself", session.player.username.lower()]:
            return await self._examine_self(session)

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
        current_room_id = getattr(session, 'current_room_id', None)
        if not current_room_id:
            return self.create_error_result(I18N.get_message("obj.no_location", get_user_locale(session)))

        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result(I18N.get_message("obj.no_engine", get_user_locale(session)))

        try:
            target_object = None

            room_objects = await game_engine.world_manager.get_room_objects(current_room_id)
            for obj in room_objects:
                obj_name_en = obj.get_localized_name('en').lower()
                obj_name_ko = obj.get_localized_name('ko').lower()
                if object_name in obj_name_en or object_name in obj_name_ko:
                    target_object = obj
                    break

            if not target_object:
                inventory_objects = await game_engine.world_manager.get_inventory_objects(session.player.id)
                for obj in inventory_objects:
                    obj_name_en = obj.get_localized_name('en').lower()
                    obj_name_ko = obj.get_localized_name('ko').lower()
                    if object_name in obj_name_en or object_name in obj_name_ko:
                        target_object = obj
                        break

            if not target_object:
                return self.create_error_result(I18N.get_message("obj.get.not_found", get_user_locale(session), name=' '.join(object_name.split())))

            obj_name = target_object.get_localized_name(session.locale)
            obj_description = target_object.get_localized_description(session.locale)
            obj_type = target_object.object_type
            location = "인벤토리" if target_object.location_type == 'inventory' else "이 방"

            response = f"🔍 {obj_name}\n{obj_description}\n\n📋 종류: {obj_type}\n📍 위치: {location}"

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
            return self.create_error_result(I18N.get_message("obj.examine.error", get_user_locale(session)))
