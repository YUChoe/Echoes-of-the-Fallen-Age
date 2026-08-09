# -*- coding: utf-8 -*-
"""핸들러 공용 헬퍼

여러 카테고리가 함께 쓰는 조회를 모은다.
"""

import logging
from typing import TYPE_CHECKING, Any

from ...game.models.gameobject import GameObject

if TYPE_CHECKING:
    from ..context import ActionContext

logger = logging.getLogger(__name__)


async def get_gold(ctx: "ActionContext") -> int:
    """플레이어의 화폐 합계를 조회한다.

    `CurrencyManager` 는 현재 `DialogueManager` 가 소유한다. 교환 시스템과 함께
    초기화되므로 없을 수 있어 방어적으로 접근한다.

    Returns:
        화폐 합계. 조회할 수 없으면 0
    """
    if not ctx.player_id:
        return 0

    dialogue_manager = getattr(ctx.game_engine, "dialogue_manager", None)
    currency_manager = getattr(dialogue_manager, "currency_manager", None)

    if currency_manager is None:
        logger.debug("CurrencyManager 가 초기화되지 않아 화폐를 0으로 보고한다")
        return 0

    try:
        return int(await currency_manager.get_balance(ctx.player_id))
    except Exception as e:
        logger.error(f"화폐 조회 실패 ({ctx.player_id}): {e}")
        return 0


async def get_carried_objects(ctx: "ActionContext") -> list[GameObject]:
    """인벤토리와 장착 아이템을 합쳐 중복 없이 돌려준다.

    두 조회의 포함 관계를 가정하지 않는다. uuid 로 중복을 제거한다.
    """
    if not ctx.player_id:
        return []

    world = ctx.game_engine.world_manager

    merged: dict[str, GameObject] = {}
    for obj in await world.get_inventory_objects(ctx.player_id):
        merged[str(obj.id)] = obj
    for obj in await world.get_equipped_objects(ctx.player_id):
        merged[str(obj.id)] = obj

    return list(merged.values())


def entity_payload(ctx: "ActionContext", resolved: Any) -> dict[str, Any]:
    """해석된 대상을 엔티티 페이로드로 만든다.

    Args:
        ctx: 액션 컨텍스트. 관찰자 종족을 얻는 데 쓴다
        resolved: `EntityResolver` 가 돌려준 `ResolvedEntity`

    Returns:
        엔티티 페이로드
    """
    from ...server.serialization import (
        serialize_monster,
        serialize_object,
        serialize_player,
    )
    from ..resolver import EntityKind

    if resolved.kind is EntityKind.MONSTER:
        viewer_faction = ctx.session.player.faction_id if ctx.session.player else None
        lua_loader = ctx.game_engine.dialogue_manager.lua_loader

        return serialize_monster(
            resolved.entity,
            viewer_faction=viewer_faction,
            can_talk=lua_loader.has_dialogue_script(resolved.entity.id),
        )

    if resolved.kind is EntityKind.OBJECT:
        return serialize_object(resolved.entity)

    if resolved.kind is EntityKind.PLAYER:
        return serialize_player(resolved.entity, include_vitals=False)

    # 전투 참가자는 전투 상태 메시지가 담당하므로 여기서 다루지 않는다
    return {"id": str(getattr(resolved.entity, "id", "")), "kind": "combatant"}
