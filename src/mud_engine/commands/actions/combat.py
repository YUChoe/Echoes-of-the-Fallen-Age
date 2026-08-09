# -*- coding: utf-8 -*-
"""전투 액션

공격, 도주, 전투 중 아이템 사용, 턴 종료를 담당한다. 대상은 uuid 로 지정되므로
전투 인스턴스의 번호 맵을 쓰지 않는다.

턴 순서 강제는 `CombatHandler.process_player_action` 이 수행한다. 이 모듈은
그 결과를 보고 턴 진행 여부를 결정한다. 기존 구현은 실패해도 턴을 넘겼다.

몬스터 턴은 3초 틱 스케줄러만 처리한다. 기존 flee 와 item 명령어는 액션 처리
중에 직접 몬스터 턴 루프를 돌려 틱과 경쟁했으나 여기서는 그러지 않는다.
"""

import logging
import random
from typing import Any, Optional

from .items import UseHandler
from ..base import ActionHandler
from ..context import ActionContext, ActionResult, error, rejected, success
from ..resolver import EntityKind
from ...game.combatant import CombatAction
from ...server.serialization import build_combat_state

logger = logging.getLogger(__name__)

# 도주에 필요한 스태미나
FLEE_STAMINA_COST = 3.0


def _get_combat(ctx: ActionContext) -> tuple[Optional[Any], Optional[ActionResult]]:
    """세션의 활성 전투를 가져온다.

    Returns:
        (전투 인스턴스, 거절 결과). 성공하면 두 번째 값이 None
    """
    combat_id = getattr(ctx.session, "combat_id", None)
    if not combat_id:
        return None, rejected("WRONG_STATE", message="No combat id on session")

    combat = ctx.game_engine.combat_handler.combat_manager.get_combat(combat_id)
    if combat is None or not combat.is_active:
        return None, rejected("WRONG_STATE", message="Combat not found or ended")

    return combat, None


def _require_my_turn(ctx: ActionContext, combat: Any) -> Optional[ActionResult]:
    """현재 턴이 요청자의 턴인지 확인한다.

    `process_player_action` 도 같은 검사를 하지만, 그 전에 거절해야 스태미나
    소모나 아이템 소모 같은 부수 효과를 막을 수 있다.
    """
    current = combat.get_current_combatant()
    player = ctx.session.player

    if player is None:
        return rejected("NOT_AUTHENTICATED")

    if current is None or current.id != player.id:
        return rejected("NOT_YOUR_TURN", message="Not your turn")

    return None


async def _push_combat_state(ctx: ActionContext, combat: Any) -> None:
    """요청자에게 전투 상태를 보낸다."""
    if ctx.session.player is None:
        return

    await ctx.session.send_message(
        build_combat_state(combat, ctx.session.player.id, seq=ctx.seq)
    )


async def _finish_if_over(ctx: ActionContext, combat: Any) -> bool:
    """전투가 끝났으면 정리하고 방 정보를 보낸다.

    Returns:
        전투가 끝났으면 True
    """
    if not combat.is_combat_over():
        return False

    await ctx.game_engine.combat_handler.leave_combat(ctx.session, combat)

    room_id = getattr(ctx.session, "current_room_id", None)
    if room_id:
        await ctx.game_engine.movement_manager.send_room_info_to_player(
            ctx.session, room_id
        )

    return True


class AttackHandler(ActionHandler):
    """공격. 전투 밖에서는 전투를 시작한다."""

    verb = "attack"
    requires_target = True

    async def handle(self, ctx: ActionContext) -> ActionResult:
        resolved = ctx.entity
        if resolved is None:
            return rejected("NOT_FOUND", message="Target not resolved")

        if getattr(ctx.session, "in_combat", False):
            return await self._attack_in_combat(ctx, resolved)

        return await self._start_combat(ctx, resolved)

    async def _start_combat(self, ctx: ActionContext, resolved: Any) -> ActionResult:
        """전투를 시작한다. 대상은 방의 몬스터여야 한다."""
        if resolved.kind is not EntityKind.MONSTER:
            return rejected("NOT_APPLICABLE", message="Target is not attackable")

        if not ctx.room_id or ctx.session.player is None:
            return rejected("WRONG_STATE", message="No current room")

        combat = await ctx.game_engine.combat_handler.start_combat(
            ctx.session.player, resolved.entity, ctx.room_id
        )

        ctx.game_engine.combat_handler.enter_combat(ctx.session, combat, ctx.room_id)
        await _push_combat_state(ctx, combat)

        return success(data={"combat_id": combat.id, "started": True})

    async def _attack_in_combat(
        self, ctx: ActionContext, resolved: Any
    ) -> ActionResult:
        """전투 중 공격."""
        combat, failure = _get_combat(ctx)
        if failure is not None:
            return failure
        assert combat is not None

        not_my_turn = _require_my_turn(ctx, combat)
        if not_my_turn is not None:
            return not_my_turn

        # 전투 참가자 중에서 대상을 찾는다. 전투 밖 엔티티는 때릴 수 없다.
        target = combat.get_combatant(ctx.target)
        if target is None:
            return rejected("NOT_FOUND", message="Target is not in this combat")

        if not target.is_alive():
            return rejected("NOT_APPLICABLE", message="Target is already dead")

        result = await ctx.game_engine.combat_handler.process_player_action(
            combat.id, ctx.session.player.id, CombatAction.ATTACK, target.id
        )

        if not result.get("success"):
            # 실패했으면 턴을 넘기지 않는다. 기존 구현은 넘겨서 턴을 잃었다.
            return rejected(
                "NOT_APPLICABLE", message=str(result.get("message", "Attack failed"))
            )

        combat.advance_turn()

        if await _finish_if_over(ctx, combat):
            return success(data={"combat_over": True, **_attack_data(result)})

        await _push_combat_state(ctx, combat)

        return success(data=_attack_data(result))


class FleeHandler(ActionHandler):
    """도주"""

    verb = "flee"
    combat_only = True

    async def handle(self, ctx: ActionContext) -> ActionResult:
        combat, failure = _get_combat(ctx)
        if failure is not None:
            return failure
        assert combat is not None

        not_my_turn = _require_my_turn(ctx, combat)
        if not_my_turn is not None:
            return not_my_turn

        if not self._has_stamina(ctx):
            return rejected("WRONG_STATE", message="Stamina exhausted")

        result = await ctx.game_engine.combat_handler.process_player_action(
            combat.id, ctx.session.player.id, CombatAction.FLEE, None
        )

        if not result.get("success"):
            return rejected(
                "NOT_APPLICABLE", message=str(result.get("message", "Flee failed"))
            )

        ctx.session.stamina = max(
            0.0, getattr(ctx.session, "stamina", 0.0) - FLEE_STAMINA_COST
        )

        if not result.get("fled"):
            # 도주 실패는 턴만 소모한다. 몬스터 턴은 3초 틱이 처리한다.
            combat.advance_turn()
            await _push_combat_state(ctx, combat)
            return success(
                message_key="combat.flee_failed", data={"fled": False}
            )

        return await self._escape(ctx, combat)

    def _has_stamina(self, ctx: ActionContext) -> bool:
        """도주에 필요한 스태미나가 있는지 확인한다."""
        player = ctx.session.player
        is_superadmin = (
            player is not None
            and getattr(player, "is_admin", False)
            and player.get_display_name() == "SUPERADMIN"
        )

        if is_superadmin:
            return True

        return getattr(ctx.session, "stamina", 0.0) >= FLEE_STAMINA_COST

    async def _escape(self, ctx: ActionContext, combat: Any) -> ActionResult:
        """도주 성공 처리. 원래 방의 임의 출구로 빠져나간다."""
        original_room_id = getattr(ctx.session, "original_room_id", None)

        # 전투 상태를 먼저 해제해야 이동이 정상 동작한다
        await ctx.game_engine.combat_handler.leave_combat(ctx.session, combat)
        ctx.game_engine.combat_handler.combat_manager.end_combat(combat.id)

        if not original_room_id:
            logger.warning("도주했으나 원래 방을 알 수 없다")
            return success(message_key="combat.flee_success", data={"fled": True})

        destination = await self._pick_escape_room(ctx, original_room_id)

        if destination is None:
            await ctx.game_engine.movement_manager.send_room_info_to_player(
                ctx.session, original_room_id
            )
            return success(message_key="combat.flee_success", data={"fled": True})

        ctx.session.current_room_id = original_room_id
        await ctx.game_engine.movement_manager.move_player_to_room(
            ctx.session, destination
        )

        return success(
            message_key="combat.flee_success",
            data={"fled": True, "room_id": destination},
        )

    async def _pick_escape_room(
        self, ctx: ActionContext, room_id: str
    ) -> Optional[str]:
        """도주할 방을 고른다. 출구가 없으면 None."""
        exits = await ctx.game_engine.world_manager._room_manager.get_coordinate_based_exits(
            room_id
        )

        directions = [d for d in exits if d != "enter"]
        if not directions:
            return None

        return exits[random.choice(directions)]


class UseItemHandler(ActionHandler):
    """전투 중 아이템 사용

    아이템 효과는 `use` 와 같은 구현을 쓰고, 성공하면 턴을 소모한다.
    """

    verb = "use_item"
    requires_target = True
    combat_only = True

    async def handle(self, ctx: ActionContext) -> ActionResult:
        combat, failure = _get_combat(ctx)
        if failure is not None:
            return failure
        assert combat is not None

        # 기존 item 명령어는 턴 검사가 없어 남의 턴에도 아이템을 쓰고
        # 턴을 넘길 수 있었다.
        not_my_turn = _require_my_turn(ctx, combat)
        if not_my_turn is not None:
            return not_my_turn

        result = await UseHandler().handle(ctx)

        if not result.succeeded:
            # 사용에 실패하면 턴을 소모하지 않는다
            return result

        combat.advance_turn()

        if await _finish_if_over(ctx, combat):
            result.data["combat_over"] = True
            return result

        await _push_combat_state(ctx, combat)

        return result


class EndTurnHandler(ActionHandler):
    """턴 종료"""

    verb = "end_turn"
    combat_only = True

    async def handle(self, ctx: ActionContext) -> ActionResult:
        combat, failure = _get_combat(ctx)
        if failure is not None:
            return failure
        assert combat is not None

        not_my_turn = _require_my_turn(ctx, combat)
        if not_my_turn is not None:
            return not_my_turn

        result = await ctx.game_engine.combat_handler.process_player_action(
            combat.id, ctx.session.player.id, CombatAction.ENDTURN, None
        )

        if not result.get("success"):
            return error(message=str(result.get("message", "End turn failed")))

        if await _finish_if_over(ctx, combat):
            return success(data={"combat_over": True})

        await _push_combat_state(ctx, combat)

        return success()


def _attack_data(result: dict[str, Any]) -> dict[str, Any]:
    """공격 결과에서 클라이언트에 보낼 값만 추린다."""
    return {
        "hit": bool(result.get("hit", False)),
        "damage_dealt": int(result.get("damage_dealt", 0)),
        "is_critical": bool(result.get("is_critical", False)),
        "target_hp": result.get("target_hp"),
        "target_max_hp": result.get("target_max_hp"),
    }


def handlers() -> list[ActionHandler]:
    """이 카테고리의 핸들러 목록"""
    return [AttackHandler(), FleeHandler(), UseItemHandler(), EndTurnHandler()]
