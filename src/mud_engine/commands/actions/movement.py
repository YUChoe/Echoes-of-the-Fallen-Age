# -*- coding: utf-8 -*-
"""이동과 방 조회 액션

방향 이동, 통로 진입, 방 정보 재요청을 담당한다. 방향 별칭은 존재하지 않으며
`move` verb 의 `direction` params 로 통합되었다.
"""

import logging

from ..base import ActionHandler
from ..context import ActionContext, ActionResult, error, rejected, success

logger = logging.getLogger(__name__)

# 이동 가능한 방향. 계약이 규정한 네 방향이다.
VALID_DIRECTIONS = ("north", "south", "east", "west")

# 좌표 기반 출구 계산이 통로 연결을 담는 키
PASSAGE_EXIT_KEY = "enter"


class MoveHandler(ActionHandler):
    """방향 이동"""

    verb = "move"
    forbidden_in_combat = True

    async def handle(self, ctx: ActionContext) -> ActionResult:
        direction = ctx.params.get("direction")

        if not isinstance(direction, str) or direction not in VALID_DIRECTIONS:
            return rejected(
                "INVALID_PARAMS",
                message=f"direction must be one of {VALID_DIRECTIONS}",
            )

        if not ctx.room_id:
            return rejected("WRONG_STATE", message="No current room")

        # 이동 성공 시 room_info 는 이동 매니저가 밀어 보낸다. 스태미나 부족과
        # 출구 없음 판정도 매니저가 수행하므로 여기서 중복 검사하지 않는다.
        moved = await ctx.game_engine.movement_manager.move_player_by_direction(
            ctx.session, direction
        )

        if not moved:
            return rejected(
                "NOT_APPLICABLE",
                message=f"Cannot move {direction}",
            )

        return success(data={"direction": direction})


class EnterHandler(ActionHandler):
    """통로 진입

    `room_connections` 좌표 연결을 사용하므로 대상 엔티티가 없다.
    """

    verb = "enter"
    forbidden_in_combat = True

    async def handle(self, ctx: ActionContext) -> ActionResult:
        if not ctx.room_id:
            return rejected("WRONG_STATE", message="No current room")

        # 좌표 기반 출구 계산이 room_connections 연결을 enter 키로 담아 준다.
        # 직접 SQL 조회를 하지 않는 이유는 같은 판정이 두 곳에 생기기 때문이다.
        exits = await ctx.game_engine.world_manager._room_manager.get_coordinate_based_exits(
            ctx.room_id
        )

        target_room_id = exits.get(PASSAGE_EXIT_KEY)
        if not target_room_id:
            return rejected("NOT_APPLICABLE", message="No passage here")

        moved = await ctx.game_engine.movement_manager.move_player_to_room(
            ctx.session, target_room_id
        )

        if not moved:
            logger.error(f"통로 진입 실패: {ctx.room_id} -> {target_room_id}")
            return error(message="Passage move failed")

        return success(data={"room_id": target_room_id})


class LookHandler(ActionHandler):
    """방 정보 재요청"""

    verb = "look"

    async def handle(self, ctx: ActionContext) -> ActionResult:
        if not ctx.room_id:
            return rejected("WRONG_STATE", message="No current room")

        await ctx.game_engine.movement_manager.send_room_info_to_player(
            ctx.session, ctx.room_id
        )

        return success()


def handlers() -> list[ActionHandler]:
    """이 카테고리의 핸들러 목록"""
    return [MoveHandler(), EnterHandler(), LookHandler()]
