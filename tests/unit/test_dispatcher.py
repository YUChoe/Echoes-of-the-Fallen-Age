"""
액션 디스패처 단위 테스트

디스패처는 모든 액션이 지나는 경로다. 인증, verb 조회, 권한, 상태 게이팅,
대상 해석 순서와 각 단계의 거절 코드를 고정한다.
"""

from types import SimpleNamespace

import pytest

from src.mud_engine.commands.base import ActionHandler
from src.mud_engine.commands.context import (
    ActionContext,
    ActionResult,
    ActionResultType,
    success,
)
from src.mud_engine.commands.dispatcher import ActionDispatcher


class _RecordingHandler(ActionHandler):
    """호출 여부를 기록하는 핸들러"""

    def __init__(self, verb: str, **flags: bool) -> None:
        self.verb = verb
        self.called_with: ActionContext | None = None
        for name, value in flags.items():
            setattr(self, name, value)

    async def handle(self, ctx: ActionContext) -> ActionResult:
        self.called_with = ctx
        return success(message_key="ok")


class _ExplodingHandler(ActionHandler):
    """예외를 던지는 핸들러"""

    verb = "explode"

    async def handle(self, ctx: ActionContext) -> ActionResult:
        raise RuntimeError("의도된 실패")


def _make_session(
    *,
    authenticated: bool = True,
    is_admin: bool = False,
    in_combat: bool = False,
    room_id: str | None = "room-1",
) -> SimpleNamespace:
    """디스패처가 참조하는 속성만 갖춘 세션 대역"""
    player = (
        SimpleNamespace(id="player-1", username="tester", is_admin=is_admin)
        if authenticated
        else None
    )
    return SimpleNamespace(
        session_id="session-1",
        is_authenticated=authenticated,
        player=player,
        in_combat=in_combat,
        combat_id=None,
        current_room_id=room_id,
    )


def _make_dispatcher() -> ActionDispatcher:
    """게임 엔진을 쓰지 않는 디스패처"""
    return ActionDispatcher(game_engine=SimpleNamespace())  # type: ignore[arg-type]


class TestRegistration:
    """핸들러 등록"""

    def test_register_exposes_verb(self):
        """등록한 verb 를 조회할 수 있다"""
        dispatcher = _make_dispatcher()
        handler = _RecordingHandler("look")

        dispatcher.register(handler)

        assert dispatcher.get_handler("look") is handler
        assert dispatcher.known_verbs() == ["look"]

    def test_register_rejects_empty_verb(self):
        """verb 가 없는 핸들러는 거부한다"""
        dispatcher = _make_dispatcher()

        with pytest.raises(ValueError, match="verb"):
            dispatcher.register(_RecordingHandler(""))

    def test_register_rejects_duplicate(self):
        """같은 verb 를 두 번 등록하지 않는다"""
        dispatcher = _make_dispatcher()
        dispatcher.register(_RecordingHandler("look"))

        with pytest.raises(ValueError, match="중복"):
            dispatcher.register(_RecordingHandler("look"))

    def test_register_all_counts(self):
        """여러 핸들러를 한 번에 등록한다"""
        dispatcher = _make_dispatcher()

        dispatcher.register_all(
            [_RecordingHandler("look"), _RecordingHandler("move")]
        )

        assert dispatcher.known_verbs() == ["look", "move"]


class TestAuthentication:
    """1단계 인증 검사"""

    @pytest.mark.asyncio
    async def test_unauthenticated_is_rejected(self):
        """미인증 세션은 NOT_AUTHENTICATED 로 거절한다"""
        dispatcher = _make_dispatcher()
        handler = _RecordingHandler("look")
        dispatcher.register(handler)

        result = await dispatcher.dispatch(
            ActionContext(
                session=_make_session(authenticated=False),
                game_engine=dispatcher.game_engine,
                verb="look",
            )
        )

        assert result.result_type is ActionResultType.REJECTED
        assert result.rejection_code == "NOT_AUTHENTICATED"
        assert handler.called_with is None

    @pytest.mark.asyncio
    async def test_authentication_precedes_verb_lookup(self):
        """미인증이면 verb 가 없어도 인증 오류를 먼저 낸다"""
        dispatcher = _make_dispatcher()

        result = await dispatcher.dispatch(
            ActionContext(
                session=_make_session(authenticated=False),
                game_engine=dispatcher.game_engine,
                verb="nonexistent",
            )
        )

        assert result.rejection_code == "NOT_AUTHENTICATED"


class TestVerbLookup:
    """2단계 verb 조회"""

    @pytest.mark.asyncio
    async def test_unknown_verb_is_rejected(self):
        """등록되지 않은 verb 는 NOT_APPLICABLE 로 거절한다"""
        dispatcher = _make_dispatcher()

        result = await dispatcher.dispatch(
            ActionContext(
                session=_make_session(),
                game_engine=dispatcher.game_engine,
                verb="fly",
            )
        )

        assert result.rejection_code == "NOT_APPLICABLE"

    @pytest.mark.asyncio
    async def test_known_verb_reaches_handler(self):
        """등록된 verb 는 핸들러에 도달한다"""
        dispatcher = _make_dispatcher()
        handler = _RecordingHandler("look")
        dispatcher.register(handler)

        result = await dispatcher.dispatch(
            ActionContext(
                session=_make_session(),
                game_engine=dispatcher.game_engine,
                verb="look",
            )
        )

        assert result.succeeded
        assert handler.called_with is not None


class TestPermission:
    """3단계 권한 검사"""

    @pytest.mark.asyncio
    async def test_admin_only_rejects_normal_player(self):
        """관리자 전용 verb 를 일반 플레이어가 쓰면 거절한다"""
        dispatcher = _make_dispatcher()
        handler = _RecordingHandler("spawn", admin_only=True)
        dispatcher.register(handler)

        result = await dispatcher.dispatch(
            ActionContext(
                session=_make_session(is_admin=False),
                game_engine=dispatcher.game_engine,
                verb="spawn",
            )
        )

        assert result.rejection_code == "PERMISSION_DENIED"
        assert handler.called_with is None

    @pytest.mark.asyncio
    async def test_admin_only_allows_admin(self):
        """관리자는 통과한다"""
        dispatcher = _make_dispatcher()
        dispatcher.register(_RecordingHandler("spawn", admin_only=True))

        result = await dispatcher.dispatch(
            ActionContext(
                session=_make_session(is_admin=True),
                game_engine=dispatcher.game_engine,
                verb="spawn",
            )
        )

        assert result.succeeded


class TestStateGating:
    """4단계 상태 게이팅"""

    @pytest.mark.asyncio
    async def test_combat_only_outside_combat_is_rejected(self):
        """전투 전용 verb 를 전투 밖에서 쓰면 WRONG_STATE"""
        dispatcher = _make_dispatcher()
        dispatcher.register(_RecordingHandler("flee", combat_only=True))

        result = await dispatcher.dispatch(
            ActionContext(
                session=_make_session(in_combat=False),
                game_engine=dispatcher.game_engine,
                verb="flee",
            )
        )

        assert result.rejection_code == "WRONG_STATE"

    @pytest.mark.asyncio
    async def test_combat_only_inside_combat_passes(self):
        """전투 중이면 전투 전용 verb 가 통과한다"""
        dispatcher = _make_dispatcher()
        dispatcher.register(_RecordingHandler("flee", combat_only=True))

        result = await dispatcher.dispatch(
            ActionContext(
                session=_make_session(in_combat=True),
                game_engine=dispatcher.game_engine,
                verb="flee",
            )
        )

        assert result.succeeded

    @pytest.mark.asyncio
    async def test_forbidden_in_combat_is_rejected(self):
        """전투 중 금지 verb 는 WRONG_STATE"""
        dispatcher = _make_dispatcher()
        dispatcher.register(_RecordingHandler("move", forbidden_in_combat=True))

        result = await dispatcher.dispatch(
            ActionContext(
                session=_make_session(in_combat=True),
                game_engine=dispatcher.game_engine,
                verb="move",
            )
        )

        assert result.rejection_code == "WRONG_STATE"

    @pytest.mark.asyncio
    async def test_forbidden_in_combat_passes_outside(self):
        """전투 밖에서는 통과한다"""
        dispatcher = _make_dispatcher()
        dispatcher.register(_RecordingHandler("move", forbidden_in_combat=True))

        result = await dispatcher.dispatch(
            ActionContext(
                session=_make_session(in_combat=False),
                game_engine=dispatcher.game_engine,
                verb="move",
            )
        )

        assert result.succeeded


class TestTargetResolution:
    """5단계 대상 해석"""

    @pytest.mark.asyncio
    async def test_missing_target_is_rejected(self):
        """대상이 필요한 verb 에 target 이 없으면 TARGET_REQUIRED"""
        dispatcher = _make_dispatcher()
        dispatcher.register(_RecordingHandler("examine", requires_target=True))

        result = await dispatcher.dispatch(
            ActionContext(
                session=_make_session(),
                game_engine=dispatcher.game_engine,
                verb="examine",
            )
        )

        assert result.rejection_code == "TARGET_REQUIRED"

    @pytest.mark.asyncio
    async def test_unresolvable_target_is_rejected(self, monkeypatch):
        """접근 범위 밖의 uuid 는 NOT_FOUND"""
        dispatcher = _make_dispatcher()
        dispatcher.register(_RecordingHandler("examine", requires_target=True))

        async def _resolve_none(session, target_id):
            return None

        monkeypatch.setattr(dispatcher.resolver, "resolve", _resolve_none)

        result = await dispatcher.dispatch(
            ActionContext(
                session=_make_session(),
                game_engine=dispatcher.game_engine,
                verb="examine",
                target="missing-uuid",
            )
        )

        assert result.rejection_code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_resolved_entity_is_passed_to_handler(self, monkeypatch):
        """해석 결과가 컨텍스트에 담겨 핸들러로 전달된다"""
        dispatcher = _make_dispatcher()
        handler = _RecordingHandler("examine", requires_target=True)
        dispatcher.register(handler)

        sentinel = object()

        async def _resolve_found(session, target_id):
            return sentinel

        monkeypatch.setattr(dispatcher.resolver, "resolve", _resolve_found)

        result = await dispatcher.dispatch(
            ActionContext(
                session=_make_session(),
                game_engine=dispatcher.game_engine,
                verb="examine",
                target="found-uuid",
            )
        )

        assert result.succeeded
        assert handler.called_with is not None
        assert handler.called_with.entity is sentinel

    @pytest.mark.asyncio
    async def test_target_is_not_resolved_when_not_required(self, monkeypatch):
        """대상이 필요 없는 verb 는 해석을 시도하지 않는다"""
        dispatcher = _make_dispatcher()
        dispatcher.register(_RecordingHandler("look"))

        called = False

        async def _resolve(session, target_id):
            nonlocal called
            called = True
            return None

        monkeypatch.setattr(dispatcher.resolver, "resolve", _resolve)

        result = await dispatcher.dispatch(
            ActionContext(
                session=_make_session(),
                game_engine=dispatcher.game_engine,
                verb="look",
                target="ignored-uuid",
            )
        )

        assert result.succeeded
        assert called is False


class TestHandlerFailure:
    """핸들러 예외 처리"""

    @pytest.mark.asyncio
    async def test_exception_becomes_error_result(self):
        """핸들러 예외는 ERROR 결과로 바뀌고 전파되지 않는다"""
        dispatcher = _make_dispatcher()
        dispatcher.register(_ExplodingHandler())

        result = await dispatcher.dispatch(
            ActionContext(
                session=_make_session(),
                game_engine=dispatcher.game_engine,
                verb="explode",
            )
        )

        assert result.result_type is ActionResultType.ERROR


class TestBuildContext:
    """action 메시지 → 컨텍스트 변환"""

    def test_full_message(self):
        """필드를 그대로 옮긴다"""
        dispatcher = _make_dispatcher()
        session = _make_session()

        ctx = dispatcher.build_context(
            session,
            {
                "type": "action",
                "seq": 7,
                "verb": "get",
                "target": "obj-1",
                "params": {"quantity": 3},
            },
        )

        assert ctx.verb == "get"
        assert ctx.target == "obj-1"
        assert ctx.params == {"quantity": 3}
        assert ctx.seq == 7

    def test_missing_optional_fields(self):
        """없는 필드는 기본값으로 채운다"""
        dispatcher = _make_dispatcher()

        ctx = dispatcher.build_context(_make_session(), {"type": "action", "verb": "look"})

        assert ctx.target is None
        assert ctx.params == {}
        assert ctx.seq is None

    def test_wrong_types_are_discarded(self):
        """타입이 어긋난 필드는 버린다"""
        dispatcher = _make_dispatcher()

        ctx = dispatcher.build_context(
            _make_session(),
            {"type": "action", "verb": "get", "target": 42, "params": "nope", "seq": "1"},
        )

        assert ctx.target is None
        assert ctx.params == {}
        assert ctx.seq is None

    def test_missing_verb_becomes_empty(self):
        """verb 가 없으면 빈 문자열이 되어 조회에서 거절된다"""
        dispatcher = _make_dispatcher()

        ctx = dispatcher.build_context(_make_session(), {"type": "action"})

        assert ctx.verb == ""


class TestContextHelpers:
    """ActionContext 파생 속성"""

    def test_player_and_room_ids(self):
        """세션에서 플레이어와 방 id 를 꺼낸다"""
        dispatcher = _make_dispatcher()
        ctx = dispatcher.build_context(_make_session(room_id="room-9"), {"verb": "look"})

        assert ctx.player_id == "player-1"
        assert ctx.room_id == "room-9"

    def test_ids_none_without_player(self):
        """미인증 세션은 플레이어 id 가 없다"""
        dispatcher = _make_dispatcher()
        ctx = dispatcher.build_context(
            _make_session(authenticated=False), {"verb": "look"}
        )

        assert ctx.player_id is None
