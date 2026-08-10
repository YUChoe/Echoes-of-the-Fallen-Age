"""
전투 액션 단위 테스트

턴 강제, 스태미나 조건, 실패 시 턴 보존을 고정한다. 하니스로 검증하면 살아 있는
NPC를 공격해 개발 세계 데이터를 바꾸게 되므로 여기서 대역으로 확인한다.

특히 "실패한 액션이 턴을 소모하지 않는다"는 기존 구현의 결함을 고정한다.
"""

from types import SimpleNamespace

import pytest

from src.mud_engine.commands.actions.combat import (
    AttackHandler,
    EndTurnHandler,
    FleeHandler,
)
from src.mud_engine.commands.context import ActionContext, ActionResultType
from src.mud_engine.commands.resolver import EntityKind, ResolvedEntity
from src.mud_engine.game.combatant import CombatantType


class _Combatant:
    """Combatant 대역. serialize_combatant 가 읽는 필드를 모두 갖춘다."""

    def __init__(
        self,
        combatant_id: str,
        alive: bool = True,
        combatant_type: CombatantType = CombatantType.PLAYER,
    ) -> None:
        self.id = combatant_id
        self.name = combatant_id
        self.combatant_type = combatant_type
        self.current_hp = 10 if alive else 0
        self.max_hp = 10
        self.attack_power = 3
        self.defense = 1
        self.is_defending = False
        self.data: dict | None = None
        self._alive = alive

    def is_alive(self) -> bool:
        return self._alive


class _Combat:
    """CombatInstance 대역"""

    def __init__(self, current_id: str, combatants: list[_Combatant]) -> None:
        self.id = "combat-1"
        self.is_active = True
        self.turn_number = 1
        self.turn_order = [c.id for c in combatants]
        self.combatants = combatants
        self._current_id = current_id
        self.advance_calls = 0
        self._over = False

    def get_current_combatant(self):
        return self.get_combatant(self._current_id)

    def get_combatant(self, combatant_id: str):
        for c in self.combatants:
            if c.id == combatant_id:
                return c
        return None

    def advance_turn(self) -> None:
        self.advance_calls += 1

    def is_combat_over(self) -> bool:
        return self._over


class _CombatManager:
    def __init__(self, combat) -> None:
        self._combat = combat
        self.ended: list[str] = []

    def get_combat(self, combat_id: str):
        return self._combat if self._combat and combat_id == self._combat.id else None

    def end_combat(self, combat_id: str) -> None:
        self.ended.append(combat_id)


class _CombatHandler:
    def __init__(self, combat, action_result: dict) -> None:
        self.combat_manager = _CombatManager(combat)
        self._action_result = action_result
        self.actions: list[tuple] = []
        self.left: list[str] = []
        self.entered: list[str] = []

    async def process_player_action(self, combat_id, player_id, action, target_id):
        self.actions.append((combat_id, player_id, action, target_id))
        return self._action_result

    async def leave_combat(self, session, combat) -> None:
        self.left.append(combat.id)
        session.in_combat = False
        session.combat_id = None

    def enter_combat(self, session, combat, room_id) -> None:
        self.entered.append(combat.id)
        session.in_combat = True
        session.combat_id = combat.id

    async def start_combat(self, player, monster, room_id):
        return _Combat(player.id, [_Combatant(player.id), _Combatant(monster.id)])


def _make_ctx(
    *,
    combat=None,
    action_result: dict | None = None,
    in_combat: bool = True,
    stamina: float = 5.0,
    target: str | None = "monster-1",
    entity=None,
    verb: str = "attack",
) -> ActionContext:
    """전투 핸들러 호출에 필요한 최소 컨텍스트"""
    sent: list[dict] = []

    async def _send_message(message):
        sent.append(message)

    session = SimpleNamespace(
        session_id="session-1",
        is_authenticated=True,
        player=SimpleNamespace(
            id="player-1",
            username="tester",
            is_admin=False,
            get_display_name=lambda: "tester",
        ),
        in_combat=in_combat,
        combat_id=combat.id if combat else None,
        current_room_id="room-1",
        original_room_id="room-1",
        stamina=stamina,
        max_stamina=5.0,
        send_message=_send_message,
    )

    handler = _CombatHandler(combat, action_result or {"success": True})

    game_engine = SimpleNamespace(
        combat_handler=handler,
        movement_manager=SimpleNamespace(
            send_room_info_to_player=_noop_async,
            move_player_to_room=_noop_async,
        ),
    )

    ctx = ActionContext(
        session=session,
        game_engine=game_engine,  # type: ignore[arg-type]
        verb=verb,
        target=target,
        entity=entity,
    )
    ctx.sent = sent  # type: ignore[attr-defined]
    return ctx


async def _noop_async(*_args, **_kwargs):
    return True


class TestAttackTurnEnforcement:
    """공격의 턴 강제"""

    @pytest.mark.asyncio
    async def test_not_my_turn_rejected(self):
        """남의 턴이면 NOT_YOUR_TURN 으로 거절한다"""
        combat = _Combat("monster-1", [_Combatant("player-1"), _Combatant("monster-1")])
        ctx = _make_ctx(combat=combat, entity=ResolvedEntity(EntityKind.COMBATANT, None, "combat"))

        result = await AttackHandler().handle(ctx)

        assert result.rejection_code == "NOT_YOUR_TURN"
        assert combat.advance_calls == 0

    @pytest.mark.asyncio
    async def test_failed_attack_does_not_advance_turn(self):
        """공격이 실패하면 턴을 넘기지 않는다

        기존 구현은 process_player_action 결과를 무시하고 턴을 넘겨 턴을 잃었다.
        """
        combat = _Combat("player-1", [_Combatant("player-1"), _Combatant("monster-1")])
        ctx = _make_ctx(
            combat=combat,
            action_result={"success": False, "message": "거절"},
            entity=ResolvedEntity(EntityKind.COMBATANT, None, "combat"),
        )

        result = await AttackHandler().handle(ctx)

        assert result.result_type is ActionResultType.REJECTED
        assert combat.advance_calls == 0

    @pytest.mark.asyncio
    async def test_successful_attack_advances_turn(self):
        """성공하면 턴을 넘긴다"""
        combat = _Combat("player-1", [_Combatant("player-1"), _Combatant("monster-1")])
        ctx = _make_ctx(
            combat=combat,
            action_result={"success": True, "hit": True, "damage_dealt": 5},
            entity=ResolvedEntity(EntityKind.COMBATANT, None, "combat"),
        )

        result = await AttackHandler().handle(ctx)

        assert result.succeeded
        assert combat.advance_calls == 1
        assert result.data["damage_dealt"] == 5

    @pytest.mark.asyncio
    async def test_target_outside_combat_rejected(self):
        """전투 참가자가 아닌 uuid 는 거절한다"""
        combat = _Combat("player-1", [_Combatant("player-1")])
        ctx = _make_ctx(
            combat=combat,
            target="stranger",
            entity=ResolvedEntity(EntityKind.COMBATANT, None, "combat"),
        )

        result = await AttackHandler().handle(ctx)

        assert result.rejection_code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_dead_target_rejected(self):
        """이미 죽은 대상은 거절한다"""
        combat = _Combat(
            "player-1", [_Combatant("player-1"), _Combatant("monster-1", alive=False)]
        )
        ctx = _make_ctx(
            combat=combat,
            entity=ResolvedEntity(EntityKind.COMBATANT, None, "combat"),
        )

        result = await AttackHandler().handle(ctx)

        assert result.rejection_code == "NOT_APPLICABLE"
        assert combat.advance_calls == 0


class TestAttackStartsCombat:
    """전투 밖에서의 공격"""

    @pytest.mark.asyncio
    async def test_non_monster_target_rejected(self):
        """몬스터가 아닌 대상으로는 전투를 시작하지 않는다"""
        ctx = _make_ctx(
            in_combat=False,
            entity=ResolvedEntity(EntityKind.OBJECT, SimpleNamespace(id="obj-1"), "room"),
        )

        result = await AttackHandler().handle(ctx)

        assert result.rejection_code == "NOT_APPLICABLE"

    @pytest.mark.asyncio
    async def test_monster_target_starts_combat(self):
        """방의 몬스터를 공격하면 전투에 진입한다"""
        ctx = _make_ctx(
            in_combat=False,
            entity=ResolvedEntity(
                EntityKind.MONSTER, SimpleNamespace(id="monster-1"), "room"
            ),
        )

        result = await AttackHandler().handle(ctx)

        assert result.succeeded
        assert result.data["started"] is True
        assert ctx.session.in_combat is True
        assert ctx.game_engine.combat_handler.entered


class TestFlee:
    """도주"""

    @pytest.mark.asyncio
    async def test_insufficient_stamina_rejected(self):
        """스태미나가 부족하면 거절하고 액션을 실행하지 않는다"""
        combat = _Combat("player-1", [_Combatant("player-1")])
        ctx = _make_ctx(combat=combat, stamina=1.0, verb="flee")

        result = await FleeHandler().handle(ctx)

        assert result.rejection_code == "WRONG_STATE"
        assert ctx.game_engine.combat_handler.actions == []

    @pytest.mark.asyncio
    async def test_not_my_turn_rejected(self):
        """남의 턴이면 거절한다"""
        combat = _Combat("monster-1", [_Combatant("player-1"), _Combatant("monster-1")])
        ctx = _make_ctx(combat=combat, verb="flee")

        result = await FleeHandler().handle(ctx)

        assert result.rejection_code == "NOT_YOUR_TURN"

    @pytest.mark.asyncio
    async def test_failed_flee_spends_turn_and_stamina(self):
        """도주 실패는 턴과 스태미나를 소모한다"""
        combat = _Combat("player-1", [_Combatant("player-1")])
        ctx = _make_ctx(
            combat=combat,
            action_result={"success": True, "fled": False},
            verb="flee",
        )

        result = await FleeHandler().handle(ctx)

        assert result.succeeded
        assert result.data["fled"] is False
        assert combat.advance_calls == 1
        assert ctx.session.stamina == pytest.approx(2.0)

    @pytest.mark.asyncio
    async def test_successful_flee_leaves_combat(self):
        """도주 성공은 전투를 떠난다"""
        combat = _Combat("player-1", [_Combatant("player-1")])
        ctx = _make_ctx(
            combat=combat,
            action_result={"success": True, "fled": True},
            verb="flee",
        )
        ctx.game_engine.world_manager = SimpleNamespace(
            _room_manager=SimpleNamespace(
                get_coordinate_based_exits=_exits_none,
            )
        )

        result = await FleeHandler().handle(ctx)

        assert result.succeeded
        assert result.data["fled"] is True
        assert ctx.session.in_combat is False
        assert ctx.game_engine.combat_handler.left == ["combat-1"]

    @pytest.mark.asyncio
    async def test_superadmin_ignores_stamina(self):
        """SUPERADMIN 은 스태미나 조건을 건너뛴다"""
        combat = _Combat("player-1", [_Combatant("player-1")])
        ctx = _make_ctx(
            combat=combat,
            stamina=0.0,
            action_result={"success": True, "fled": False},
            verb="flee",
        )
        ctx.session.player.is_admin = True
        ctx.session.player.get_display_name = lambda: "SUPERADMIN"

        result = await FleeHandler().handle(ctx)

        assert result.succeeded


async def _exits_none(_room_id):
    return {}


class TestEndTurn:
    """턴 종료"""

    @pytest.mark.asyncio
    async def test_not_my_turn_rejected(self):
        """남의 턴이면 거절한다"""
        combat = _Combat("monster-1", [_Combatant("player-1"), _Combatant("monster-1")])
        ctx = _make_ctx(combat=combat, verb="end_turn")

        result = await EndTurnHandler().handle(ctx)

        assert result.rejection_code == "NOT_YOUR_TURN"

    @pytest.mark.asyncio
    async def test_end_turn_delegates_to_handler(self):
        """턴 종료는 CombatHandler 에 위임한다"""
        combat = _Combat("player-1", [_Combatant("player-1")])
        ctx = _make_ctx(combat=combat, verb="end_turn")

        result = await EndTurnHandler().handle(ctx)

        assert result.succeeded
        assert len(ctx.game_engine.combat_handler.actions) == 1

    @pytest.mark.asyncio
    async def test_no_combat_id_rejected(self):
        """전투 정보가 없으면 거절한다"""
        ctx = _make_ctx(combat=None, verb="end_turn")

        result = await EndTurnHandler().handle(ctx)

        assert result.rejection_code == "WRONG_STATE"
