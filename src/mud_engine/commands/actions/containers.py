# -*- coding: utf-8 -*-
"""컨테이너 액션

열어 내용 조회, 넣기, 꺼내기를 담당한다. 서버가 열림 상태를 유지하지 않으므로
`open` 은 조회 동작이며 대응하는 `close` 가 없다.
"""

import logging
from typing import Any, Optional

from .support import reject_if_overweight, reject_partial_quantity
from ..base import ActionHandler
from ..context import ActionContext, ActionResult, error, rejected, success
from ..resolver import EntityKind
from ...server.serialization import build_container_contents, coerce_properties, is_container

logger = logging.getLogger(__name__)

# 컨테이너에서 꺼낼 때의 목적지 위치 종류
INVENTORY_LOCATION = "INVENTORY"


async def _resolve_container(
    ctx: ActionContext, container_id: Any
) -> tuple[Optional[Any], Optional[ActionResult]]:
    """params 의 컨테이너 uuid 를 해석하고 컨테이너인지 확인한다.

    Returns:
        (컨테이너 오브젝트, 거절 결과). 성공하면 두 번째 값이 None
    """
    if not isinstance(container_id, str) or not container_id:
        return None, rejected(
            "INVALID_PARAMS", message="params.container must be a uuid"
        )

    resolved = await ctx.game_engine.command_manager.dispatcher.resolver.resolve(
        ctx.session, container_id
    )

    if resolved is None or resolved.kind is not EntityKind.OBJECT:
        return None, rejected("NOT_FOUND", message="Container not in current context")

    if not is_container(resolved.entity.properties):
        return None, rejected("NOT_APPLICABLE", message="Target is not a container")

    return resolved.entity, None


def _capacity_remaining(container: Any, item_count: int) -> Optional[int]:
    """컨테이너의 남은 자리를 계산한다.

    Returns:
        남은 자리. 상한이 설정되지 않았으면 None
    """
    properties = coerce_properties(container.properties)
    max_capacity = properties.get("max_capacity")

    if not isinstance(max_capacity, int) or isinstance(max_capacity, bool):
        return None

    return max_capacity - item_count


class OpenHandler(ActionHandler):
    """컨테이너 내용 조회

    서버가 열림 상태를 유지하지 않으므로 조회 동작이다.
    """

    verb = "open"
    requires_target = True

    async def handle(self, ctx: ActionContext) -> ActionResult:
        resolved = ctx.entity
        if resolved is None or resolved.kind is not EntityKind.OBJECT:
            return rejected("NOT_APPLICABLE", message="Target is not an object")

        container = resolved.entity

        if not is_container(container.properties):
            return rejected("NOT_APPLICABLE", message="Target is not a container")

        items = await ctx.game_engine.world_manager.get_container_items(container.id)

        await ctx.session.send_message(
            build_container_contents(container.id, items, seq=ctx.seq)
        )

        return success(data={"container_id": container.id, "item_count": len(items)})


class PutHandler(ActionHandler):
    """컨테이너에 넣기"""

    verb = "put"
    requires_target = True

    async def handle(self, ctx: ActionContext) -> ActionResult:
        resolved = ctx.entity
        if resolved is None or resolved.kind is not EntityKind.OBJECT:
            return rejected("NOT_APPLICABLE", message="Target is not an item")

        if resolved.source not in ("inventory", "equipped"):
            return rejected("NOT_APPLICABLE", message="Item is not carried")

        item = resolved.entity

        if item.is_equipped:
            return rejected("WRONG_STATE", message="Unequip before storing")

        partial = reject_partial_quantity(ctx, item)
        if partial is not None:
            return partial

        container, failure = await _resolve_container(
            ctx, ctx.params.get("container")
        )
        if failure is not None:
            return failure
        assert container is not None

        if container.id == item.id:
            return rejected("NOT_APPLICABLE", message="Cannot store a container in itself")

        world = ctx.game_engine.world_manager
        contents = await world.get_container_items(container.id)

        # 용량 검증. 데이터에 max_capacity 가 있으나 기존 구현은 검사하지 않았다.
        remaining = _capacity_remaining(container, len(contents))
        if remaining is not None and remaining < 1:
            return rejected(
                "INVENTORY_FULL",
                params={"container_capacity": len(contents)},
                message="Container is full",
            )

        stored = await world.move_item_to_container(item.id, container.id)
        if not stored:
            return error(message="Failed to store item")

        return success(
            message_key="obj.put.success",
            params={
                "name": _name_params(item),
                "container": _name_params(container),
            },
            data={"object_id": item.id, "container_id": container.id},
        )


class TakeFromHandler(ActionHandler):
    """컨테이너에서 꺼내기"""

    verb = "take_from"
    requires_target = True

    async def handle(self, ctx: ActionContext) -> ActionResult:
        resolved = ctx.entity
        if resolved is None or resolved.kind is not EntityKind.OBJECT:
            return rejected("NOT_APPLICABLE", message="Target is not an item")

        if resolved.source != "container":
            return rejected("NOT_APPLICABLE", message="Item is not in a container")

        item = resolved.entity

        partial = reject_partial_quantity(ctx, item)
        if partial is not None:
            return partial

        # params.container 를 주면 검증한다. 생략하면 해석 결과를 신뢰한다.
        requested = ctx.params.get("container")
        if requested is not None:
            container, failure = await _resolve_container(ctx, requested)
            if failure is not None:
                return failure
            assert container is not None
            if container.id != resolved.container_id:
                return rejected(
                    "NOT_FOUND", message="Item is not in the given container"
                )

        overweight = await reject_if_overweight(ctx, item.weight)
        if overweight is not None:
            return overweight

        taken = await ctx.game_engine.world_manager.move_item_from_container(
            item.id, INVENTORY_LOCATION, ctx.player_id
        )
        if not taken:
            return error(message="Failed to take item")

        return success(
            message_key="obj.take_from.success",
            params={"name": _name_params(item)},
            data={"object_id": item.id, "container_id": resolved.container_id},
        )


def _name_params(obj: Any) -> dict[str, str]:
    """언어별 이름 dict"""
    from ...server.serialization import localized_dict

    return localized_dict(obj.name)


def handlers() -> list[ActionHandler]:
    """이 카테고리의 핸들러 목록"""
    return [OpenHandler(), PutHandler(), TakeFromHandler()]
