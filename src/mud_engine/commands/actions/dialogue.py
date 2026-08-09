# -*- coding: utf-8 -*-
"""대화 액션

대화 시작, 선택지 선택, 대화 종료를 담당한다. 기존 구현은 세 가지를 `talk`
명령어 하나에 몰아넣고 대화 중 숫자 입력을 `talk N` 으로 재작성해 구분했다.
verb 가 분리되므로 그 변환이 필요하지 않다.

선택지 번호는 대화 인스턴스 로컬 번호이며 uuid 규약의 예외다.
"""

import logging
from typing import Any, Optional

from ..base import ActionHandler
from ..context import ActionContext, ActionResult, error, rejected, success
from ..resolver import EntityKind
from ...server.serialization import build_dialogue, ensure_farewell_choice

logger = logging.getLogger(__name__)


def _get_dialogue(ctx: ActionContext) -> tuple[Optional[Any], Optional[ActionResult]]:
    """세션의 활성 대화를 가져온다.

    Returns:
        (대화 인스턴스, 거절 결과). 성공하면 두 번째 값이 None
    """
    if not getattr(ctx.session, "in_dialogue", False):
        return None, rejected("WRONG_STATE", message="Not in a dialogue")

    dialogue_id = getattr(ctx.session, "dialogue_id", None)
    if not dialogue_id:
        return None, rejected("WRONG_STATE", message="No dialogue id on session")

    dialogue = ctx.game_engine.dialogue_manager.get_dialogue_instance(dialogue_id)
    if dialogue is None:
        logger.warning(f"세션의 대화 {dialogue_id} 를 찾을 수 없다")
        return None, rejected("WRONG_STATE", message="Dialogue not found")

    return dialogue, None


async def _send_dialogue(
    ctx: ActionContext, dialogue: Any, lines: Any, is_active: bool = True
) -> None:
    """대화 상태를 클라이언트에 보낸다."""
    if is_active:
        ensure_farewell_choice(dialogue.choice_entity)

    await ctx.session.send_message(
        build_dialogue(
            dialogue.id,
            dialogue.interlocutor,
            lines,
            dialogue.choice_entity if is_active else {},
            is_active=is_active,
            seq=ctx.seq,
        )
    )


async def _close_dialogue(ctx: ActionContext, dialogue: Any) -> None:
    """대화를 닫고 종료 상태를 통보한다."""
    await _send_dialogue(ctx, dialogue, [], is_active=False)
    await ctx.game_engine.dialogue_manager.end_dialogue(dialogue.id)


class TalkHandler(ActionHandler):
    """대화 시작"""

    verb = "talk"
    requires_target = True
    forbidden_in_combat = True

    async def handle(self, ctx: ActionContext) -> ActionResult:
        resolved = ctx.entity
        if resolved is None or resolved.kind is not EntityKind.MONSTER:
            return rejected("NOT_APPLICABLE", message="Target cannot talk")

        if getattr(ctx.session, "in_dialogue", False):
            return rejected("WRONG_STATE", message="Already in a dialogue")

        if ctx.session.player is None or not ctx.room_id:
            return rejected("WRONG_STATE", message="No current room")

        manager = ctx.game_engine.dialogue_manager

        dialogue = manager.create_dialogue(ctx.session)
        dialogue.player = ctx.session.player
        dialogue.interlocutor = resolved.entity

        # 대화 인스턴스를 방처럼 취급한다. 원래 방은 종료 후 복귀에 쓴다.
        ctx.session.in_dialogue = True
        ctx.session.original_room_id = ctx.room_id
        ctx.session.dialogue_id = dialogue.id
        ctx.session.current_room_id = f"dialogue_{dialogue.id}"

        lines = await dialogue.get_new_dialogue()
        await _send_dialogue(ctx, dialogue, lines)

        return success(data={"dialogue_id": dialogue.id})


class DialogueChoiceHandler(ActionHandler):
    """선택지 선택"""

    verb = "dialogue_choice"

    async def handle(self, ctx: ActionContext) -> ActionResult:
        dialogue, failure = _get_dialogue(ctx)
        if failure is not None:
            return failure
        assert dialogue is not None

        choice = ctx.params.get("choice")
        if not isinstance(choice, int) or isinstance(choice, bool):
            return rejected("INVALID_PARAMS", message="params.choice must be an integer")

        if choice not in dialogue.choice_entity:
            return rejected(
                "INVALID_PARAMS",
                params={"available": sorted(dialogue.choice_entity)},
                message="choice is not offered in this dialogue",
            )

        try:
            lines = await dialogue.get_dialogueby_choice(choice)
        except Exception as e:
            logger.error(f"선택지 처리 실패 ({dialogue.id}, {choice}): {e}", exc_info=True)
            return error(message="Dialogue choice failed")

        if not dialogue.is_active:
            await _close_dialogue(ctx, dialogue)
            return success(data={"dialogue_id": dialogue.id, "ended": True})

        await _send_dialogue(ctx, dialogue, lines)

        return success(data={"dialogue_id": dialogue.id, "choice": choice})


class DialogueEndHandler(ActionHandler):
    """대화 종료"""

    verb = "dialogue_end"

    async def handle(self, ctx: ActionContext) -> ActionResult:
        dialogue, failure = _get_dialogue(ctx)
        if failure is not None:
            return failure
        assert dialogue is not None

        dialogue_id = dialogue.id
        await _close_dialogue(ctx, dialogue)

        return success(data={"dialogue_id": dialogue_id, "ended": True})


def handlers() -> list[ActionHandler]:
    """이 카테고리의 핸들러 목록

    상점 verb(shop_open, shop_buy, shop_sell)는 등록하지 않는다. 계약이 요구하는
    `item_prices` 기반 상점이 서버에 구현되어 있지 않고, 거래는 대화 안의 Lua
    exchange API 로만 이루어진다. 자세한 사유는 docs/protocol/consistency.md 참조.
    """
    return [TalkHandler(), DialogueChoiceHandler(), DialogueEndHandler()]
