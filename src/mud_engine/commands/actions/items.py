# -*- coding: utf-8 -*-
"""아이템 액션

줍기, 버리기, 사용, 장착, 건네기, 읽기를 담당한다. 대상은 uuid 로 지정되므로
번호 맵과 이름 매칭이 없다.
"""

import logging
from typing import Any, Optional

from .support import (
    apply_equipment_bonuses,
    reject_if_overweight,
    reject_partial_quantity,
    remove_equipment_bonuses,
)
from ..base import ActionHandler
from ..context import (
    ActionContext,
    ActionResult,
    BroadcastSpec,
    error,
    rejected,
    success,
)
from ..resolver import EntityKind
from ...core.event_bus import Event, EventType
from ...server.serialization import coerce_properties, is_readable, is_usable

logger = logging.getLogger(__name__)

# properties 에 이 키가 있으면 소모품으로 본다
RESTORE_KEYS = ("hp_restore", "stamina_restore", "mana_restore", "heal_amount")

# 전투 밖 아이템 사용에 드는 스태미나
USE_STAMINA_COST = 0.1


def _require_object(ctx: ActionContext) -> Any:
    """해석된 대상이 오브젝트인지 확인한다.

    Returns:
        오브젝트. 오브젝트가 아니면 None
    """
    resolved = ctx.entity
    if resolved is None or resolved.kind is not EntityKind.OBJECT:
        return None
    return resolved


class GetHandler(ActionHandler):
    """방이나 컨테이너에서 줍기"""

    verb = "get"
    requires_target = True

    async def handle(self, ctx: ActionContext) -> ActionResult:
        resolved = _require_object(ctx)
        if resolved is None:
            return rejected("NOT_APPLICABLE", message="Target is not an item")

        if resolved.source in ("inventory", "equipped"):
            return rejected("NOT_APPLICABLE", message="Already carried")

        obj = resolved.entity

        partial = reject_partial_quantity(ctx, obj)
        if partial is not None:
            return partial

        overweight = await reject_if_overweight(ctx, obj.weight)
        if overweight is not None:
            return overweight

        moved = await ctx.game_engine.world_manager.move_object_to_inventory(
            obj.id, ctx.player_id
        )
        if not moved:
            return error(message="Failed to move item to inventory")

        await self._publish_pickup(ctx, obj)

        return success(
            message_key="obj.get.success",
            params={"name": _name_params(obj)},
            broadcast=BroadcastSpec(
                message_key="obj.get.broadcast",
                params={
                    "name": _name_params(obj),
                    "username": ctx.session.player.username if ctx.session.player else "",
                },
                category="item",
            ),
            data={"object_id": obj.id, "source": resolved.source},
        )

    async def _publish_pickup(self, ctx: ActionContext, obj: Any) -> None:
        """줍기 이벤트를 발행한다."""
        if not ctx.game_engine.event_bus or not ctx.session.player:
            return

        await ctx.game_engine.event_bus.publish(
            Event(
                event_type=EventType.OBJECT_PICKED_UP,
                source=ctx.session.session_id,
                room_id=ctx.room_id,
                data={
                    "player_id": ctx.session.player.id,
                    "player_name": ctx.session.player.username,
                    "object_ids": [obj.id],
                    "room_id": ctx.room_id,
                    "count": 1,
                },
            )
        )


class DropHandler(ActionHandler):
    """방에 버리기"""

    verb = "drop"
    requires_target = True

    async def handle(self, ctx: ActionContext) -> ActionResult:
        resolved = _require_object(ctx)
        if resolved is None:
            return rejected("NOT_APPLICABLE", message="Target is not an item")

        if resolved.source not in ("inventory", "equipped"):
            return rejected("NOT_APPLICABLE", message="Item is not carried")

        obj = resolved.entity

        if obj.is_equipped:
            return rejected("WRONG_STATE", message="Unequip before dropping")

        partial = reject_partial_quantity(ctx, obj)
        if partial is not None:
            return partial

        if not ctx.room_id:
            return rejected("WRONG_STATE", message="No current room")

        moved = await ctx.game_engine.world_manager.move_object_to_room(
            obj.id, ctx.room_id
        )
        if not moved:
            return error(message="Failed to move item to room")

        if ctx.game_engine.event_bus and ctx.session.player:
            await ctx.game_engine.event_bus.publish(
                Event(
                    event_type=EventType.OBJECT_DROPPED,
                    source=ctx.session.session_id,
                    room_id=ctx.room_id,
                    data={
                        "player_id": ctx.session.player.id,
                        "player_name": ctx.session.player.username,
                        "object_ids": [obj.id],
                        "room_id": ctx.room_id,
                    },
                )
            )

        return success(
            message_key="obj.drop.success",
            params={"name": _name_params(obj)},
            broadcast=BroadcastSpec(
                message_key="obj.drop.broadcast",
                params={
                    "name": _name_params(obj),
                    "username": ctx.session.player.username if ctx.session.player else "",
                },
                category="item",
            ),
            data={"object_id": obj.id},
        )


class EquipHandler(ActionHandler):
    """장착"""

    verb = "equip"
    requires_target = True

    async def handle(self, ctx: ActionContext) -> ActionResult:
        resolved = _require_object(ctx)
        if resolved is None:
            return rejected("NOT_APPLICABLE", message="Target is not an item")

        if resolved.source not in ("inventory", "equipped"):
            return rejected("NOT_APPLICABLE", message="Item is not carried")

        obj = resolved.entity
        player = ctx.session.player
        if player is None:
            return rejected("NOT_AUTHENTICATED")

        if not obj.can_be_equipped():
            return rejected("NOT_APPLICABLE", message="Item cannot be equipped")

        if obj.is_equipped:
            return rejected("WRONG_STATE", message="Already equipped")

        world = ctx.game_engine.world_manager

        # 같은 슬롯의 장비를 먼저 해제한다
        replaced: Optional[str] = None
        for equipped in await world.get_equipped_objects(player.id):
            if equipped.equipment_slot == obj.equipment_slot:
                await remove_equipment_bonuses(player, equipped, ctx.game_engine)
                equipped.unequip()
                await world.update_object(equipped)
                replaced = equipped.id
                break

        obj.equip()
        await world.update_object(obj)
        await apply_equipment_bonuses(player, obj, ctx.game_engine)

        return success(
            message_key="obj.equip.success",
            params={"name": _name_params(obj)},
            data={"object_id": obj.id, "replaced": replaced},
        )


class UnequipHandler(ActionHandler):
    """해제"""

    verb = "unequip"
    requires_target = True

    async def handle(self, ctx: ActionContext) -> ActionResult:
        resolved = _require_object(ctx)
        if resolved is None:
            return rejected("NOT_APPLICABLE", message="Target is not an item")

        obj = resolved.entity
        player = ctx.session.player
        if player is None:
            return rejected("NOT_AUTHENTICATED")

        if not obj.is_equipped:
            return rejected("WRONG_STATE", message="Item is not equipped")

        await remove_equipment_bonuses(player, obj, ctx.game_engine)
        obj.unequip()
        await ctx.game_engine.world_manager.update_object(obj)

        return success(
            message_key="obj.unequip.success",
            params={"name": _name_params(obj)},
            data={"object_id": obj.id},
        )


class UnequipAllHandler(ActionHandler):
    """전체 해제"""

    verb = "unequip_all"

    async def handle(self, ctx: ActionContext) -> ActionResult:
        player = ctx.session.player
        if player is None or not ctx.player_id:
            return rejected("NOT_AUTHENTICATED")

        world = ctx.game_engine.world_manager
        equipped = await world.get_equipped_objects(ctx.player_id)

        if not equipped:
            return rejected("WRONG_STATE", message="Nothing equipped")

        removed: list[str] = []
        for item in equipped:
            # 기존 unequipall 은 보너스를 제거하지 않아 스탯이 남는 결함이 있었다
            await remove_equipment_bonuses(player, item, ctx.game_engine)
            item.unequip()
            await world.update_object(item)
            removed.append(item.id)

        return success(
            message_key="obj.unequip_all.success",
            params={"count": len(removed)},
            data={"object_ids": removed},
        )


class GiveHandler(ActionHandler):
    """다른 플레이어에게 건네기"""

    verb = "give"
    requires_target = True

    async def handle(self, ctx: ActionContext) -> ActionResult:
        resolved = _require_object(ctx)
        if resolved is None:
            return rejected("NOT_APPLICABLE", message="Target is not an item")

        if resolved.source not in ("inventory", "equipped"):
            return rejected("NOT_APPLICABLE", message="Item is not carried")

        obj = resolved.entity

        if obj.is_equipped:
            return rejected("WRONG_STATE", message="Unequip before giving")

        partial = reject_partial_quantity(ctx, obj)
        if partial is not None:
            return partial

        recipient_id = ctx.params.get("to")
        if not isinstance(recipient_id, str) or not recipient_id:
            return rejected("INVALID_PARAMS", message="params.to must be a player uuid")

        recipient = await self._find_recipient(ctx, recipient_id)
        if recipient is None:
            return rejected("NOT_FOUND", message="Recipient not in this room")

        # 받는 쪽 무게 여유 확인. 기존 구현에는 이 검사가 없었다.
        world = ctx.game_engine.world_manager
        recipient_inventory = await world.get_inventory_objects(recipient_id)
        if not recipient.player.can_carry_more(recipient_inventory, obj.weight):
            return rejected("INVENTORY_FULL", message="Recipient cannot carry more")

        moved = await world.move_object_to_inventory(obj.id, recipient_id)
        if not moved:
            return error(message="Failed to transfer item")

        giver = ctx.session.player.username if ctx.session.player else ""

        await recipient.send_message(
            {
                "type": "event",
                "category": "item",
                "message": {
                    "key": "obj.give.received",
                    "params": {"name": _name_params(obj), "username": giver},
                },
            }
        )

        return success(
            message_key="obj.give.success",
            params={
                "name": _name_params(obj),
                "target": recipient.player.get_display_name(),
            },
            data={"object_id": obj.id, "to": recipient_id},
        )

    async def _find_recipient(self, ctx: ActionContext, recipient_id: str) -> Any:
        """같은 방의 수신자 세션을 찾는다."""
        sessions = ctx.game_engine.session_manager.get_authenticated_sessions()

        for other in sessions:
            if (
                other.player
                and other.player.id == recipient_id
                and other.session_id != ctx.session.session_id
                and getattr(other, "current_room_id", None) == ctx.room_id
            ):
                return other

        return None


class UseHandler(ActionHandler):
    """사용"""

    verb = "use"
    requires_target = True

    async def handle(self, ctx: ActionContext) -> ActionResult:
        resolved = _require_object(ctx)
        if resolved is None:
            return rejected("NOT_APPLICABLE", message="Target is not an item")

        if resolved.source not in ("inventory", "equipped"):
            return rejected("NOT_APPLICABLE", message="Item is not carried")

        obj = resolved.entity
        in_combat = getattr(ctx.session, "in_combat", False)

        if not in_combat and getattr(ctx.session, "stamina", 0.0) < USE_STAMINA_COST:
            return rejected("WRONG_STATE", message="Stamina exhausted")

        lua_result = _run_lua_callback(ctx, obj, "use")
        properties = coerce_properties(obj.properties)

        # Lua 콜백은 문장과 소모 여부만 정한다. 효과는 템플릿 속성에서 온다.
        # 예전에는 콜백이 있으면 효과 적용을 건너뛰어, 체력 물약을 마셔도
        # `hp_restore` 가 쓰이지 않고 체력이 그대로였다.
        if lua_result is None and not is_usable(properties):
            return rejected("NOT_APPLICABLE", message="Item is not usable")

        effect = (
            await self._apply_effect(ctx, obj, properties)
            if is_usable(properties)
            else None
        )

        # 콜백이 있으면 그 뜻을 따르고, 없으면 종전대로 항상 소모한다
        consume = (
            bool(lua_result.get("consume", False))
            if lua_result is not None
            else True
        )
        if consume:
            await _consume_item(ctx, obj)
        _spend_stamina(ctx, in_combat)

        # 콜백 문장은 분위기를, 효과 문장은 수치를 전한다. 둘 다 있으면 콜백
        # 문장을 먼저 내보내고 효과 문장을 액션 결과로 남긴다
        flavour = (lua_result.get("message") or {}) if lua_result is not None else {}
        if flavour.get("key") and effect is not None:
            from ...server.serialization import build_event

            await ctx.session.send_message(
                build_event(
                    str(flavour["key"]),
                    flavour.get("params"),
                    category="item",
                )
            )

        shown = effect if effect is not None else flavour
        return success(
            message_key=shown.get("key"),
            params=shown.get("params"),
            category="item",
            data={"object_id": obj.id, "lua_callback": lua_result is not None},
        )

    async def _apply_effect(
        self, ctx: ActionContext, obj: Any, properties: dict[str, Any]
    ) -> dict[str, Any]:
        """회복 효과를 적용하고 표시할 키와 파라미터를 만든다."""
        player = ctx.session.player
        name = _name_params(obj)

        if "hp_restore" in properties and player and player.stats:
            amount = int(properties.get("hp_restore", 0))
            healed = await self._restore_hp(ctx, amount)
            return {
                "key": "obj.use.hp_restored",
                "params": {"name": name, "amount": healed},
            }

        if "stamina_restore" in properties:
            restored = _restore_stamina(ctx, float(properties["stamina_restore"]))
            return {
                "key": "obj.use.stamina_restored",
                "params": {"name": name, "amount": round(restored, 1)},
            }

        # mana_restore 와 heal_amount 는 적용 로직이 없다. 소모만 된다.
        return {"key": "obj.use.used", "params": {"name": name}}

    async def _restore_hp(self, ctx: ActionContext, amount: int) -> int:
        """HP 를 회복하고 실제 회복량을 반환한다."""
        from ...game.models.player import StatType

        player = ctx.session.player
        if player is None or not player.stats:
            return 0

        max_hp = player.stats.get_secondary_stat(StatType.HP)
        old_hp = player.stats.get_current_hp()
        new_hp = min(old_hp + amount, max_hp)
        player.stats.set_current_hp(new_hp)

        # 매니저를 거쳐 저장한다. 기존 구현은 PlayerRepository 를 직접 잡았다.
        await ctx.game_engine.player_manager.save_player(player)

        return new_hp - old_hp


class ReadHandler(ActionHandler):
    """읽기"""

    verb = "read"
    requires_target = True

    async def handle(self, ctx: ActionContext) -> ActionResult:
        resolved = _require_object(ctx)
        if resolved is None:
            return rejected("NOT_APPLICABLE", message="Target is not an item")

        obj = resolved.entity

        page = ctx.params.get("page")
        if page is not None and (
            not isinstance(page, int) or isinstance(page, bool) or page < 1
        ):
            return rejected("INVALID_PARAMS", message="page must be a positive integer")

        lua_result = _run_lua_callback(ctx, obj, "read")
        properties = coerce_properties(obj.properties)

        # 콜백 문장은 읽는 순간의 분위기를, `readable.content` 는 본문을 담는다.
        # 예전에는 콜백이 있으면 여기서 끝나 본문이 클라이언트에 닿지 않았다.
        flavour = (lua_result.get("message") or {}) if lua_result is not None else {}
        if flavour.get("key") and is_readable(properties):
            from ...server.serialization import build_event

            await ctx.session.send_message(
                build_event(
                    str(flavour["key"]),
                    flavour.get("params"),
                    category="item",
                )
            )

        if not is_readable(properties):
            if flavour.get("key"):
                return success(
                    message_key=str(flavour["key"]),
                    params=flavour.get("params"),
                    category="item",
                    data={"object_id": obj.id, "lua_callback": True},
                )
            return rejected("NOT_APPLICABLE", message="Item is not readable")

        readable = properties.get("readable", {})
        if not isinstance(readable, dict):
            return error(message="readable properties malformed")

        pages = readable.get("pages")

        if isinstance(pages, list) and pages:
            index = (page or 1) - 1
            if index >= len(pages):
                return rejected(
                    "INVALID_PARAMS",
                    params={"total": len(pages)},
                    message=f"page out of range (total {len(pages)})",
                )
            content = pages[index]
            return success(
                data={
                    "object_id": obj.id,
                    "page": index + 1,
                    "total_pages": len(pages),
                    "content": _localized_content(content),
                    "readable_type": readable.get("type", "note"),
                }
            )

        return success(
            data={
                "object_id": obj.id,
                "page": 1,
                "total_pages": 1,
                "content": _localized_content(readable.get("content", {})),
                "readable_type": readable.get("type", "note"),
            }
        )


# 공용 --------------------------------------------------------------------


def _name_params(obj: Any) -> dict[str, str]:
    """언어별 이름 dict. 클라이언트가 현재 locale 값을 골라 치환한다."""
    from ...server.serialization import localized_dict

    return localized_dict(obj.name)


def _localized_content(content: Any) -> dict[str, str]:
    """읽을 내용을 언어별 dict 로 만든다."""
    if isinstance(content, dict):
        return {
            "en": str(content.get("en", "")),
            "ko": str(content.get("ko", "")),
        }

    text = str(content) if content else ""
    return {"en": text, "ko": text}


def _restore_stamina(ctx: ActionContext, amount: float) -> float:
    """스태미나를 회복하고 실제 회복량을 반환한다.

    스태미나는 세션 상태이며 영속화하지 않는다.
    """
    old = getattr(ctx.session, "stamina", 0.0)
    maximum = getattr(ctx.session, "max_stamina", 0.0)

    ctx.session.stamina = min(old + amount, maximum)
    return ctx.session.stamina - old


def _spend_stamina(ctx: ActionContext, in_combat: bool) -> None:
    """전투 밖에서만 스태미나를 소모한다."""
    if in_combat:
        return

    current = getattr(ctx.session, "stamina", 0.0)
    ctx.session.stamina = max(0.0, current - USE_STAMINA_COST)


async def _consume_item(ctx: ActionContext, obj: Any) -> None:
    """사용한 아이템을 변환하거나 삭제한다.

    기존 구현은 Lua 경로와 폴백 경로에 같은 로직을 두 번 작성했다.
    """
    import json

    properties = coerce_properties(obj.properties)
    after_use = properties.get("after_use", {})
    transform_to = after_use.get("transform_to") if isinstance(after_use, dict) else None

    world = ctx.game_engine.world_manager

    if not transform_to:
        await world.remove_object(obj.id)
        return

    template_loader = world._monster_manager._template_loader
    template = template_loader.get_item_template(transform_to)

    if not template:
        logger.warning(f"변환 템플릿 없음: {transform_to}. 아이템을 삭제한다")
        await world.remove_object(obj.id)
        return

    new_properties = dict(template.get("properties", {}))
    new_properties["template_id"] = transform_to

    await ctx.game_engine.model_manager.game_objects.update(
        obj.id,
        {
            "name_en": template.get("name_en", ""),
            "name_ko": template.get("name_ko", ""),
            "description_en": template.get("description_en", ""),
            "description_ko": template.get("description_ko", ""),
            "weight": template.get("weight", 0.0),
            "properties": json.dumps(new_properties, ensure_ascii=False),
        },
    )


def _run_lua_callback(
    ctx: ActionContext, obj: Any, verb: str
) -> Optional[dict[str, Any]]:
    """아이템 Lua 콜백을 실행한다.

    Returns:
        콜백 결과. 스크립트나 핸들러가 없으면 None
    """
    handler = getattr(ctx.game_engine, "item_lua_callback_handler", None)
    if handler is None:
        return None

    properties = coerce_properties(obj.properties)
    template_id = properties.get("template_id")
    if not template_id:
        return None

    player = ctx.session.player
    if player is None:
        return None

    from ...server.serialization import localized_dict

    context = {
        "player": {
            "id": str(player.id),
            "display_name": player.get_display_name(),
            "locale": player.preferred_locale,
        },
        "item": {
            "id": str(obj.id),
            "template_id": template_id,
            "name": localized_dict(obj.name),
            "properties": properties,
        },
    }

    return handler.execute_verb_callback(template_id, verb, context)


def handlers() -> list[ActionHandler]:
    """이 카테고리의 핸들러 목록"""
    return [
        GetHandler(),
        DropHandler(),
        EquipHandler(),
        UnequipHandler(),
        UnequipAllHandler(),
        GiveHandler(),
        UseHandler(),
        ReadHandler(),
    ]
