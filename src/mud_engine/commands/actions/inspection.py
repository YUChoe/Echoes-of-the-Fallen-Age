# -*- coding: utf-8 -*-
"""대상 조사 액션

방 정보에 이미 담겨 온 엔티티를 다시 요청한다. 클라이언트가 보유한 사본이
오래되었을 때 최신 상태로 갱신하는 용도다.
"""

import logging

from .support import entity_payload
from ..base import ActionHandler
from ..context import ActionContext, ActionResult, rejected, success
from ...server.serialization import build

logger = logging.getLogger(__name__)


class ExamineHandler(ActionHandler):
    """대상 상세 조사

    `entity_update` 로 응답한다. `changes` 에 엔티티 전체를 담아 클라이언트가
    보유 사본에 병합하게 한다. 별도 응답 타입을 두지 않는 이유는 계약이
    엔티티 갱신 경로를 이미 정의하고 있어서다.
    """

    verb = "examine"
    requires_target = True

    async def handle(self, ctx: ActionContext) -> ActionResult:
        if ctx.entity is None:
            return rejected("NOT_FOUND", message="Target not resolved")

        payload = entity_payload(ctx, ctx.entity)

        await ctx.session.send_message(
            build(
                "entity_update",
                seq=ctx.seq,
                entity_id=payload.get("id", ctx.target),
                changes=payload,
            )
        )

        return success()


def handlers() -> list[ActionHandler]:
    """이 카테고리의 핸들러 목록"""
    return [ExamineHandler()]
