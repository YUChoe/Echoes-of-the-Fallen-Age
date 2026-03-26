# -*- coding: utf-8 -*-
"""객체 버리기 명령어"""

import logging
from typing import List

from .base import BaseCommand, CommandResult
from .utils import get_user_locale
from ..core.types import SessionType
from ..core.localization import get_localization_manager
from ..core.event_bus import Event, EventType

logger = logging.getLogger(__name__)
I18N = get_localization_manager()


class DropCommand(BaseCommand):
    """객체 버리기 명령어"""

    def __init__(self):
        super().__init__(
            name="drop",
            aliases=["place"],
            description="인벤토리의 객체를 현재 방에 놓습니다",
            usage="drop <객체명>"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        if not self.validate_args(args, min_args=1):
            return self.create_error_result(
                "버릴 객체를 지정해주세요.\n사용법: drop <객체명>"
            )

        if not session.is_authenticated or not session.player:
            return self.create_error_result(I18N.get_message("obj.unauthenticated", get_user_locale(session)))

        current_room_id = getattr(session, 'current_room_id', None)
        if not current_room_id:
            return self.create_error_result(I18N.get_message("obj.no_location", get_user_locale(session)))
        logger.info(f"current_room_id[{current_room_id}]")

        game_engine = getattr(session, 'game_engine', None)
        if not game_engine:
            return self.create_error_result(I18N.get_message("obj.no_engine", get_user_locale(session)))

        object_entity = int(args[0])
        logger.info(f"DropCommand execute invoked object_entity[{object_entity}]")

        inventory_entity = getattr(session, 'inventory_entity_map', {})
        logger.info(f"inventory_entity from session cnt[{len(inventory_entity.keys())}]")

        try:
            target_object = inventory_entity[object_entity]['objects'][0]
            logger.info(f"target_object[{target_object.to_simple()}]")
            if not target_object:
                logger.info(f"인벤토리에 '{' '.join(args)}'이(가) 없습니다.")
                return self.create_error_result(I18N.get_message("obj.drop.not_in_inv", get_user_locale(session), name=' '.join(args)))

            success = await game_engine.world_manager.move_object_to_room(target_object.id, current_room_id)

            if not success:
                logger.error("객체를 버릴 수 없습니다.")
                return self.create_error_result(I18N.get_message("obj.drop.failed", get_user_locale(session)))

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

            obj_name = target_object.get_localized_name(session.locale)
            player_message = f"📦 {obj_name}을(를) 버렸습니다."
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
            return self.create_error_result(I18N.get_message("obj.drop.error", get_user_locale(session)))
