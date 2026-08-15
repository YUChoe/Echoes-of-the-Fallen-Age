# -*- coding: utf-8 -*-
"""핸들러 공용 헬퍼

여러 카테고리가 함께 쓰는 조회를 모은다.
"""

import logging
from typing import TYPE_CHECKING, Any

from ...game.models.gameobject import GameObject
from ...server.serialization import coerce_properties

if TYPE_CHECKING:
    from ..context import ActionContext

logger = logging.getLogger(__name__)


async def get_silver(ctx: "ActionContext") -> int:
    """플레이어의 실버 잔액을 조회한다.

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


async def apply_equipment_bonuses(player: Any, equipment: Any, game_engine: Any) -> None:
    """장비의 능력치 보너스를 플레이어에게 적용한다."""
    try:
        properties = coerce_properties(getattr(equipment, "properties", None))
        stats_bonus = properties.get("stats_bonus", {})

        if not isinstance(stats_bonus, dict):
            return

        for stat_name, bonus in stats_bonus.items():
            if isinstance(bonus, (int, float)) and not isinstance(bonus, bool) and bonus > 0:
                player.stats.add_equipment_bonus(stat_name, int(bonus))

        # 기존 구현은 존재하지 않는 session_manager.update_player 를 호출했고
        # 예외가 삼켜져 보너스가 저장되지 않았다.
        await game_engine.player_manager.save_player(player)
    except Exception as e:
        logger.error(f"장비 보너스 적용 중 오류: {e}")


async def remove_equipment_bonuses(player: Any, equipment: Any, game_engine: Any) -> None:
    """장비의 능력치 보너스를 플레이어에서 제거한다."""
    try:
        properties = coerce_properties(getattr(equipment, "properties", None))
        stats_bonus = properties.get("stats_bonus", {})

        if not isinstance(stats_bonus, dict):
            return

        for stat_name, bonus in stats_bonus.items():
            if isinstance(bonus, (int, float)) and not isinstance(bonus, bool) and bonus > 0:
                player.stats.remove_equipment_bonus(stat_name, int(bonus))

        await game_engine.player_manager.save_player(player)
    except Exception as e:
        logger.error(f"장비 보너스 제거 중 오류: {e}")


def reject_partial_quantity(ctx: "ActionContext", obj: GameObject) -> Any:
    """부분 수량 이동 요청을 거절한다.

    아이템은 개별 레코드로 존재하고 서버가 스택을 병합하지 않는다. 화폐만
    `properties.quantity` 를 쓰며 스택 분할이 구현되어 있지 않다. 따라서 uuid 는
    항상 전량을 가리키고, 그보다 적은 수량 요청은 수행할 수 없다.

    Returns:
        거절 결과. 요청이 전량과 일치하거나 생략됐으면 None
    """
    from ...server.serialization import stack_count
    from ..context import rejected

    requested = ctx.params.get("quantity")
    if requested is None:
        return None

    if not isinstance(requested, int) or isinstance(requested, bool) or requested < 1:
        return rejected("INVALID_PARAMS", message="quantity must be a positive integer")

    available = stack_count(obj.properties)
    if requested != available:
        return rejected(
            "INVALID_PARAMS",
            message=(
                f"partial stack transfer is not supported "
                f"(requested {requested}, stack holds {available})"
            ),
        )

    return None


async def reject_if_overweight(
    ctx: "ActionContext", weight: float
) -> Any:
    """무게 제한을 초과하면 거절한다.

    Args:
        ctx: 액션 컨텍스트
        weight: 추가로 들게 되는 무게

    Returns:
        거절 결과. 여유가 있으면 None
    """
    from ..context import rejected

    player = ctx.session.player
    if player is None or not ctx.player_id:
        return rejected("NOT_AUTHENTICATED")

    inventory = await ctx.game_engine.world_manager.get_inventory_objects(ctx.player_id)

    if player.can_carry_more(inventory, weight):
        return None

    info = player.get_carry_capacity_info(inventory)
    return rejected(
        "INVENTORY_FULL",
        params={
            "current_weight": round(float(info["current_weight"]), 2),
            "max_weight": round(float(info["max_weight"]), 2),
            "item_weight": round(float(weight), 2),
        },
        message="Carry weight exceeded",
    )
