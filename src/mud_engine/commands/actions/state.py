# -*- coding: utf-8 -*-
"""상태 조회 액션

플레이어가 이미 알고 있어야 할 상태를 다시 요청하는 verb 들이다. 재접속이나
화면 전환 후 클라이언트가 상태를 맞추는 데 쓴다.

기존 `stats`, `inventory`, `combat` 명령어를 대체한다.
"""

import logging

from .support import get_carried_objects, get_silver
from ..base import ActionHandler
from ..context import ActionContext, ActionResult, rejected, success
from ...server.serialization import (
    build_combat_state,
    build_inventory,
    build_player_state,
)

logger = logging.getLogger(__name__)


class RequestStateHandler(ActionHandler):
    """player_state 재전송"""

    verb = "request_state"

    async def handle(self, ctx: ActionContext) -> ActionResult:
        player = ctx.session.player
        if player is None:
            return rejected("NOT_AUTHENTICATED")

        await ctx.session.send_message(
            build_player_state(
                player,
                room_id=ctx.room_id,
                stamina=getattr(ctx.session, "stamina", 0.0),
                max_stamina=getattr(ctx.session, "max_stamina", 0.0),
                silver=await get_silver(ctx),
                in_combat=getattr(ctx.session, "in_combat", False),
                in_dialogue=getattr(ctx.session, "in_dialogue", False),
                following=getattr(ctx.session, "following_player", None),
                seq=ctx.seq,
            )
        )

        return success()


class RequestInventoryHandler(ActionHandler):
    """inventory 재전송"""

    verb = "request_inventory"

    async def handle(self, ctx: ActionContext) -> ActionResult:
        player = ctx.session.player
        if player is None:
            return rejected("NOT_AUTHENTICATED")

        objects = await get_carried_objects(ctx)

        await ctx.session.send_message(
            build_inventory(
                player,
                objects,
                silver=await get_silver(ctx),
                seq=ctx.seq,
            )
        )

        return success()


class RequestCombatStateHandler(ActionHandler):
    """combat_state 재전송"""

    verb = "request_combat_state"
    combat_only = True

    async def handle(self, ctx: ActionContext) -> ActionResult:
        player = ctx.session.player
        if player is None:
            return rejected("NOT_AUTHENTICATED")

        combat_id = getattr(ctx.session, "combat_id", None)
        if not combat_id:
            return rejected("WRONG_STATE", message="No combat id on session")

        combat = ctx.game_engine.combat_manager.get_combat(combat_id)
        if combat is None:
            logger.warning(f"세션의 전투 {combat_id} 를 찾을 수 없다")
            return rejected("WRONG_STATE", message="Combat not found")

        await ctx.session.send_message(
            build_combat_state(combat, player.id, seq=ctx.seq)
        )

        return success()


def handlers() -> list[ActionHandler]:
    """이 카테고리의 핸들러 목록"""
    return [
        RequestStateHandler(),
        RequestInventoryHandler(),
        RequestCombatStateHandler(),
    ]
