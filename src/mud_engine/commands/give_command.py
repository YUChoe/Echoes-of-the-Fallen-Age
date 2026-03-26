# -*- coding: utf-8 -*-
"""다른 플레이어에게 아이템 주기 명령어"""

import logging
from typing import List

from .base import BaseCommand, CommandResult, CommandResultType
from ..core.types import SessionType
from ..core.event_bus import Event, EventType

logger = logging.getLogger(__name__)


class GiveCommand(BaseCommand):
    """다른 플레이어에게 아이템 주기"""

    def __init__(self):
        super().__init__(
            name="give",
            aliases=["주기"],
            description="다른 플레이어에게 아이템을 줍니다",
            usage="give <아이템명> <플레이어명>"
        )

    async def execute(self, session: SessionType, args: List[str]) -> CommandResult:
        logger.debug(f"GiveCommand 실행: 플레이어={session.player.username}, args={args}")

        if len(args) < 2:
            logger.warning(f"GiveCommand: 잘못된 인수 개수 - 플레이어={session.player.username}, args={args}")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="사용법: give <아이템명> <플레이어명>"
            )

        item_name = args[0]
        target_player_name = args[1]

        logger.info(f"아이템 주기 시도: {session.player.username} -> {target_player_name} ({item_name})")

        # 대상 플레이어 찾기 (같은 방에 있는 플레이어만)
        target_session = None
        current_room_id = getattr(session, 'current_room_id', None)

        if not current_room_id:
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="현재 방 정보를 찾을 수 없습니다."
            )

        # 같은 방에 있는 플레이어들 중에서 대상 찾기
        for other_session in session.game_engine.session_manager.get_authenticated_sessions().values():
            if (other_session.player and
                other_session.player.username.lower() == target_player_name.lower() and
                getattr(other_session, 'current_room_id', None) == current_room_id and
                other_session.session_id != session.session_id):
                target_session = other_session
                break

        if not target_session:
            logger.warning(f"GiveCommand: 대상 플레이어를 찾을 수 없음 - {target_player_name} (방: {current_room_id})")
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message=f"{target_player_name}님을 이 방에서 찾을 수 없습니다."
            )

        # 플레이어 인벤토리에서 아이템 찾기
        try:
            inventory_objects = await session.game_engine.world_manager.get_inventory_objects(session.player.id)
            target_object = None

            for obj in inventory_objects:
                if obj.get_localized_name(session.locale).lower() == item_name.lower():
                    target_object = obj
                    break

            if not target_object:
                logger.warning(f"GiveCommand: 아이템을 찾을 수 없음 - {item_name} (플레이어: {session.player.username})")
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message=f"'{item_name}' 아이템을 인벤토리에서 찾을 수 없습니다."
                )

            # 아이템을 대상 플레이어의 인벤토리로 이동
            success = await session.game_engine.world_manager.move_object_to_inventory(
                target_object.id, target_session.player.id
            )

            if not success:
                logger.error(f"GiveCommand: 아이템 이동 실패 - {item_name} ({session.player.username} -> {target_player_name})")
                return CommandResult(
                    result_type=CommandResultType.ERROR,
                    message="아이템 전달에 실패했습니다."
                )

            # 이벤트 발행
            await session.game_engine.event_bus.publish(Event(
                event_type=EventType.PLAYER_GIVE,
                source=session.session_id,
                room_id=current_room_id,
                data={
                    "giver_id": session.player.id,
                    "giver_name": session.player.username,
                    "receiver_id": target_session.player.id,
                    "receiver_name": target_session.player.username,
                    "item_id": target_object.id,
                    "item_name": target_object.get_localized_name(session.locale)
                }
            ))

            # 대상 플레이어에게 알림
            await target_session.send_message({
                "type": "item_received",
                "message": f"🎁 {session.player.username}님이 '{target_object.get_localized_name(target_session.locale)}'을(를) 주었습니다.",
                "item": {
                    "id": target_object.id,
                    "name": target_object.get_localized_name(target_session.locale)
                }
            })

            return CommandResult(
                result_type=CommandResultType.SUCCESS,
                message=f"'{target_object.get_localized_name(session.locale)}'을(를) {target_session.player.username}님에게 주었습니다.",
                broadcast=True,
                broadcast_message=f"🎁 {session.player.username}님이 {target_session.player.username}님에게 '{target_object.get_localized_name(session.locale)}'을(를) 주었습니다.",
                room_only=True
            )

        except Exception as e:
            logger.error(f"아이템 주기 실패: {e}", exc_info=True)
            return CommandResult(
                result_type=CommandResultType.ERROR,
                message="아이템 전달 중 오류가 발생했습니다."
            )
