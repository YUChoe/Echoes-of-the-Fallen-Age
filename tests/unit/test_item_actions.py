"""
아이템·컨테이너 액션 단위 테스트

세계 데이터가 필요 없는 판정 로직을 고정한다. 하니스는 테스트 계정의 소지품에
의존하므로 읽기와 컨테이너 경로가 건너뛰어질 수 있다. 그 판정을 여기서 덮는다.
"""

import json
from types import SimpleNamespace

import pytest

from src.mud_engine.commands.actions.containers import _capacity_remaining
from src.mud_engine.commands.actions.items import ReadHandler, _localized_content
from src.mud_engine.commands.actions.support import reject_partial_quantity
from src.mud_engine.commands.context import ActionContext, ActionResultType
from src.mud_engine.commands.resolver import EntityKind, ResolvedEntity


def _make_object(properties: dict | str | None = None, name: dict | None = None):
    """GameObject 대역. 판정에 쓰이는 속성만 갖춘다."""
    return SimpleNamespace(
        id="obj-1",
        properties=properties if properties is not None else {},
        name=name if name is not None else {"en": "Book", "ko": "책"},
        weight=0.5,
        is_equipped=False,
        equipment_slot=None,
    )


def _make_ctx(params: dict | None = None, entity=None) -> ActionContext:
    """핸들러 호출에 필요한 최소 컨텍스트

    보낸 메시지는 `ctx.session.sent` 에 쌓인다. `read` 가 본문을 별도 메시지로
    보내므로 대역이 필요하다.
    """
    sent: list[dict] = []

    async def send_message(payload: dict) -> None:
        sent.append(payload)

    session = SimpleNamespace(
        session_id="session-1",
        is_authenticated=True,
        player=SimpleNamespace(id="player-1", username="tester", is_admin=False),
        in_combat=False,
        combat_id=None,
        current_room_id="room-1",
        stamina=5.0,
        max_stamina=5.0,
        send_message=send_message,
        sent=sent,
    )
    return ActionContext(
        session=session,
        game_engine=SimpleNamespace(item_lua_callback_handler=None),  # type: ignore[arg-type]
        verb="read",
        target="obj-1",
        params=params or {},
        entity=entity,
    )


class TestRejectPartialQuantity:
    """부분 수량 요청 거절"""

    def test_omitted_quantity_passes(self):
        """quantity 를 생략하면 통과한다"""
        assert reject_partial_quantity(_make_ctx(), _make_object()) is None

    def test_matching_quantity_passes(self):
        """보유량과 같으면 통과한다"""
        obj = _make_object({"quantity": 3})

        assert reject_partial_quantity(_make_ctx({"quantity": 3}), obj) is None

    def test_single_item_quantity_one_passes(self):
        """스택이 없는 아이템에 1을 요청하면 통과한다"""
        assert reject_partial_quantity(_make_ctx({"quantity": 1}), _make_object()) is None

    def test_partial_quantity_rejected(self):
        """보유량보다 적게 요청하면 거절한다"""
        obj = _make_object({"quantity": 10})
        result = reject_partial_quantity(_make_ctx({"quantity": 4}), obj)

        assert result is not None
        assert result.rejection_code == "INVALID_PARAMS"

    def test_excess_quantity_rejected(self):
        """보유량보다 많이 요청하면 거절한다"""
        result = reject_partial_quantity(_make_ctx({"quantity": 5}), _make_object())

        assert result is not None
        assert result.rejection_code == "INVALID_PARAMS"

    @pytest.mark.parametrize("value", [0, -1, "3", 1.5, True])
    def test_invalid_quantity_rejected(self, value):
        """정수가 아니거나 1 미만이면 거절한다"""
        result = reject_partial_quantity(_make_ctx({"quantity": value}), _make_object())

        assert result is not None
        assert result.rejection_code == "INVALID_PARAMS"

    def test_properties_as_json_string(self):
        """properties 가 JSON 문자열이어도 보유량을 읽는다"""
        obj = _make_object(json.dumps({"quantity": 7}))

        assert reject_partial_quantity(_make_ctx({"quantity": 7}), obj) is None
        assert reject_partial_quantity(_make_ctx({"quantity": 2}), obj) is not None


class TestContainerCapacity:
    """컨테이너 용량 계산"""

    def test_no_limit_returns_none(self):
        """max_capacity 가 없으면 상한이 없다"""
        assert _capacity_remaining(_make_object(), 5) is None

    def test_remaining_space(self):
        """남은 자리를 계산한다"""
        assert _capacity_remaining(_make_object({"max_capacity": 10}), 4) == 6

    def test_full_container(self):
        """가득 차면 0 이다"""
        assert _capacity_remaining(_make_object({"max_capacity": 3}), 3) == 0

    def test_non_integer_limit_ignored(self):
        """정수가 아닌 상한은 무시한다"""
        assert _capacity_remaining(_make_object({"max_capacity": "10"}), 1) is None
        assert _capacity_remaining(_make_object({"max_capacity": True}), 1) is None


class TestLocalizedContent:
    """읽을 내용의 언어별 변환"""

    def test_dict_content(self):
        """언어별 dict 는 그대로 옮긴다"""
        assert _localized_content({"en": "Hello", "ko": "안녕"}) == {
            "en": "Hello",
            "ko": "안녕",
        }

    def test_missing_language_becomes_empty(self):
        """없는 언어는 빈 문자열이다"""
        assert _localized_content({"ko": "안녕"}) == {"en": "", "ko": "안녕"}

    def test_plain_string_duplicated(self):
        """문자열은 두 언어에 같은 값을 넣는다"""
        assert _localized_content("plain") == {"en": "plain", "ko": "plain"}

    def test_empty_content(self):
        """빈 값은 빈 문자열이다"""
        assert _localized_content(None) == {"en": "", "ko": ""}


class TestReadHandler:
    """읽기 핸들러의 페이지 처리"""

    @staticmethod
    def _resolved(properties):
        return ResolvedEntity(
            kind=EntityKind.OBJECT,
            entity=_make_object(properties),
            source="inventory",
        )

    @pytest.mark.asyncio
    async def test_not_readable_rejected(self):
        """readable 속성이 없으면 거절한다"""
        ctx = _make_ctx(entity=self._resolved({}))

        result = await ReadHandler().handle(ctx)

        assert result.rejection_code == "NOT_APPLICABLE"

    @pytest.mark.asyncio
    async def test_single_page_content(self):
        """content 단일 페이지를 돌려준다"""
        ctx = _make_ctx(
            entity=self._resolved(
                {"readable": {"content": {"en": "Text", "ko": "본문"}, "type": "note"}}
            )
        )

        result = await ReadHandler().handle(ctx)

        assert result.succeeded
        assert result.data["page"] == 1
        assert result.data["total_pages"] == 1
        assert result.data["content"]["ko"] == "본문"
        assert result.data["readable_type"] == "note"

    @pytest.mark.asyncio
    async def test_multi_page_defaults_to_first(self):
        """page 를 생략하면 첫 페이지다"""
        ctx = _make_ctx(
            entity=self._resolved(
                {"readable": {"pages": [{"ko": "1장"}, {"ko": "2장"}]}}
            )
        )

        result = await ReadHandler().handle(ctx)

        assert result.data["page"] == 1
        assert result.data["total_pages"] == 2
        assert result.data["content"]["ko"] == "1장"

    @pytest.mark.asyncio
    async def test_multi_page_selection(self):
        """지정한 페이지를 돌려준다"""
        ctx = _make_ctx(
            params={"page": 2},
            entity=self._resolved(
                {"readable": {"pages": [{"ko": "1장"}, {"ko": "2장"}]}}
            ),
        )

        result = await ReadHandler().handle(ctx)

        assert result.data["page"] == 2
        assert result.data["content"]["ko"] == "2장"

    @pytest.mark.asyncio
    async def test_page_out_of_range_rejected(self):
        """범위를 넘는 페이지는 거절한다

        기존 구현은 오류 문장을 성공 결과의 본문으로 돌려주었다.
        """
        ctx = _make_ctx(
            params={"page": 5},
            entity=self._resolved({"readable": {"pages": [{"ko": "1장"}]}}),
        )

        result = await ReadHandler().handle(ctx)

        assert result.result_type is ActionResultType.REJECTED
        assert result.rejection_code == "INVALID_PARAMS"
        assert result.params["total"] == 1

    @pytest.mark.parametrize("value", [0, -1, "2", 1.5, True])
    @pytest.mark.asyncio
    async def test_invalid_page_rejected(self, value):
        """정수가 아니거나 1 미만인 page 는 거절한다"""
        ctx = _make_ctx(
            params={"page": value},
            entity=self._resolved({"readable": {"pages": [{"ko": "1장"}]}}),
        )

        result = await ReadHandler().handle(ctx)

        assert result.rejection_code == "INVALID_PARAMS"

    @pytest.mark.asyncio
    async def test_non_object_target_rejected(self):
        """오브젝트가 아닌 대상은 거절한다"""
        ctx = _make_ctx(
            entity=ResolvedEntity(
                kind=EntityKind.MONSTER, entity=_make_object(), source="room"
            )
        )

        result = await ReadHandler().handle(ctx)

        assert result.rejection_code == "NOT_APPLICABLE"

    @pytest.mark.asyncio
    async def test_empty_pages_falls_back_to_content(self):
        """pages 가 빈 배열이면 content 를 쓴다"""
        ctx = _make_ctx(
            entity=self._resolved(
                {"readable": {"pages": [], "content": {"ko": "본문"}}}
            )
        )

        result = await ReadHandler().handle(ctx)

        assert result.succeeded
        assert result.data["content"]["ko"] == "본문"


class TestLuaCallbackResult:
    """아이템 Lua 콜백 결과 변환

    콜백은 `{message = {key, params}, consume = bool}` 을 돌려준다. 서버는
    문장을 만들지 않으므로 키와 치환 파라미터만 옮긴다.
    """

    def _handler(self):
        from src.mud_engine.game.item_lua_callback_handler import (
            ItemLuaCallbackHandler,
        )
        from src.mud_engine.game.lua_script_loader import LuaScriptLoader

        loader = LuaScriptLoader()
        if not loader.is_available():
            pytest.skip("lupa 를 쓸 수 없다")
        return ItemLuaCallbackHandler(loader), loader

    def _table(self, loader, source: str):
        """Lua 소스가 돌려주는 테이블을 얻는다"""
        loader._lua.execute("function _probe() return %s end" % source)
        return loader._lua.globals()._probe()

    def test_키와_파라미터를_옮긴다(self):
        handler, loader = self._handler()
        table = self._table(
            loader,
            '{message = {key = "obj.x.use", params = {who = "tester"}},'
            " consume = true}",
        )

        result = handler._convert_callback_result(table)

        assert result == {
            "message": {"key": "obj.x.use", "params": {"who": "tester"}},
            "consume": True,
        }

    def test_이름은_언어별_dict_그대로_실린다(self):
        # 클라이언트가 현재 locale 을 고른다. 서버는 고르지 않는다
        handler, loader = self._handler()
        table = self._table(
            loader,
            '{message = {key = "obj.x.use",'
            ' params = {item = {en = "Potion", ko = "물약"}}}}',
        )

        result = handler._convert_callback_result(table)

        assert result["message"]["params"]["item"] == {
            "en": "Potion",
            "ko": "물약",
        }

    def test_consume_기본값은_거짓이다(self):
        handler, loader = self._handler()
        table = self._table(loader, '{message = {key = "obj.x.read"}}')

        result = handler._convert_callback_result(table)

        assert result["consume"] is False

    def test_키가_없으면_문장을_버리고_소모는_따른다(self):
        # 예전 형태(언어별 완성 문장)를 돌려주는 스크립트가 남아 있어도
        # 소모 여부는 지켜야 한다
        handler, loader = self._handler()
        table = self._table(
            loader, '{message = {en = "You drink it."}, consume = true}'
        )

        result = handler._convert_callback_result(table)

        assert result == {"message": None, "consume": True}

    def test_테이블이_아니면_폴백한다(self):
        handler, _ = self._handler()

        assert handler._convert_callback_result("문장") is None
        assert handler._convert_callback_result(None) is None


class TestUseHandler:
    """사용 처리

    Lua 콜백은 문장과 소모 여부만 정하고 효과는 템플릿 속성에서 온다. 예전에는
    콜백이 있으면 효과 적용을 건너뛰어 체력 물약을 마셔도 체력이 그대로였다.

    소모 경로는 세계 데이터를 만지므로 여기서는 `consume = false` 로 둔다.
    회복 효과는 세션 상태만 바꾸는 `stamina_restore` 를 쓴다.
    """

    def _ctx(self, properties: dict, lua_result: dict | None):
        from src.mud_engine.commands.actions.items import UseHandler  # noqa: F401

        sent: list[dict] = []

        async def send_message(payload: dict) -> None:
            sent.append(payload)

        session = SimpleNamespace(
            session_id="session-1",
            is_authenticated=True,
            player=SimpleNamespace(
                id="player-1",
                username="tester",
                is_admin=False,
                preferred_locale="ko",
                get_display_name=lambda: "tester",
            ),
            in_combat=False,
            combat_id=None,
            current_room_id="room-1",
            stamina=1.0,
            max_stamina=5.0,
            send_message=send_message,
        )

        handler_stub = SimpleNamespace(
            execute_verb_callback=lambda *_args, **_kwargs: lua_result
        )
        obj = _make_object(properties)

        ctx = ActionContext(
            session=session,
            game_engine=SimpleNamespace(  # type: ignore[arg-type]
                item_lua_callback_handler=handler_stub
            ),
            verb="use",
            target="obj-1",
            params={},
            entity=ResolvedEntity(
                kind=EntityKind.OBJECT, entity=obj, source="inventory"
            ),
        )
        return ctx, sent

    @pytest.mark.asyncio
    async def test_콜백이_있어도_효과를_적용한다(self):
        from src.mud_engine.commands.actions.items import UseHandler

        ctx, sent = self._ctx(
            {"stamina_restore": 2.0, "template_id": "stamina_potion"},
            {"message": {"key": "obj.x.use", "params": {}}, "consume": False},
        )

        result = await UseHandler().handle(ctx)

        assert result.succeeded
        # 회복 2.0 에서 사용 비용을 뺀 값이 남는다
        assert ctx.session.stamina > 1.0
        # 수치를 담은 효과 문장이 액션 결과로 남는다
        assert result.message_key == "obj.use.stamina_restored"
        assert result.category == "item"

    @pytest.mark.asyncio
    async def test_콜백_문장은_별도_event_로_먼저_나간다(self):
        from src.mud_engine.commands.actions.items import UseHandler

        ctx, sent = self._ctx(
            {"stamina_restore": 2.0, "template_id": "stamina_potion"},
            {"message": {"key": "obj.x.use", "params": {"who": "tester"}},
             "consume": False},
        )

        await UseHandler().handle(ctx)

        assert len(sent) == 1
        assert sent[0]["type"] == "event"
        assert sent[0]["category"] == "item"
        assert sent[0]["message"]["key"] == "obj.x.use"

    @pytest.mark.asyncio
    async def test_효과가_없으면_콜백_문장을_쓴다(self):
        # 잊혀진 경전처럼 회복 속성이 없는 아이템이다
        from src.mud_engine.commands.actions.items import UseHandler

        ctx, sent = self._ctx(
            {"template_id": "forgotten_scripture"},
            {"message": {"key": "obj.y.use", "params": {}}, "consume": False},
        )

        result = await UseHandler().handle(ctx)

        assert result.succeeded
        assert result.message_key == "obj.y.use"
        assert sent == []

    @pytest.mark.asyncio
    async def test_콜백도_효과도_없으면_거절한다(self):
        from src.mud_engine.commands.actions.items import UseHandler

        ctx, _ = self._ctx({"template_id": "smooth_stone"}, None)

        result = await UseHandler().handle(ctx)

        assert result.rejection_code == "NOT_APPLICABLE"


class TestReadWithCallback:
    """콜백이 있는 읽기

    콜백 문장은 분위기를, `readable.content` 는 본문을 담는다. 예전에는 콜백이
    있으면 본문이 클라이언트에 닿지 않았다.
    """

    def _ctx(self, properties: dict, lua_result: dict | None):
        sent: list[dict] = []

        async def send_message(payload: dict) -> None:
            sent.append(payload)

        session = SimpleNamespace(
            session_id="session-1",
            is_authenticated=True,
            player=SimpleNamespace(
                id="player-1",
                username="tester",
                is_admin=False,
                preferred_locale="ko",
                get_display_name=lambda: "tester",
            ),
            in_combat=False,
            combat_id=None,
            current_room_id="room-1",
            stamina=5.0,
            max_stamina=5.0,
            send_message=send_message,
        )

        ctx = ActionContext(
            session=session,
            game_engine=SimpleNamespace(  # type: ignore[arg-type]
                item_lua_callback_handler=SimpleNamespace(
                    execute_verb_callback=lambda *_a, **_k: lua_result
                )
            ),
            verb="read",
            target="obj-1",
            params={},
            entity=ResolvedEntity(
                kind=EntityKind.OBJECT,
                entity=_make_object(properties),
                source="inventory",
            ),
        )
        return ctx, sent

    @pytest.mark.asyncio
    async def test_본문과_콜백_문장이_모두_나간다(self):
        ctx, sent = self._ctx(
            {
                "template_id": "forgotten_scripture",
                "readable": {"content": {"en": "Hear us", "ko": "들으소서"}},
            },
            {"message": {"key": "obj.z.read", "params": {}}},
        )

        result = await ReadHandler().handle(ctx)

        assert result.succeeded
        assert [m["type"] for m in sent] == ["event", "readable_content"]
        assert sent[0]["message"]["key"] == "obj.z.read"
        assert sent[1]["content"]["ko"] == "들으소서"

    @pytest.mark.asyncio
    async def test_본문이_없으면_콜백_문장만_남는다(self):
        ctx, sent = self._ctx(
            {"template_id": "rumour_note"},
            {"message": {"key": "obj.z.read", "params": {}}},
        )

        result = await ReadHandler().handle(ctx)

        assert result.succeeded
        assert result.message_key == "obj.z.read"
        assert sent == []


class TestReadableContentMessage:
    """읽기 응답 메시지

    본문은 번역 키가 아니라 콘텐츠라 `event` 로 보낼 수 없다. `open` 이
    `container_contents` 를 보내는 것과 같은 규약으로 전용 메시지를 쓴다.
    """

    @pytest.mark.asyncio
    async def test_본문을_전용_메시지로_보낸다(self):
        ctx = _make_ctx(
            entity=ResolvedEntity(
                kind=EntityKind.OBJECT,
                entity=_make_object(
                    {"readable": {"type": "scroll", "content": {"ko": "본문"}}}
                ),
                source="inventory",
            )
        )

        await ReadHandler().handle(ctx)

        assert len(ctx.session.sent) == 1
        payload = ctx.session.sent[0]
        assert payload["type"] == "readable_content"
        assert payload["object_id"] == "obj-1"
        assert payload["readable_type"] == "scroll"
        assert payload["page"] == 1
        assert payload["total_pages"] == 1
        assert payload["content"]["ko"] == "본문"

    @pytest.mark.asyncio
    async def test_여러_쪽이면_쪽수를_담는다(self):
        ctx = _make_ctx(
            params={"page": 2},
            entity=ResolvedEntity(
                kind=EntityKind.OBJECT,
                entity=_make_object(
                    {"readable": {"pages": [{"ko": "첫"}, {"ko": "둘"}]}}
                ),
                source="inventory",
            ),
        )

        await ReadHandler().handle(ctx)

        payload = ctx.session.sent[0]
        assert payload["page"] == 2
        assert payload["total_pages"] == 2
        assert payload["content"]["ko"] == "둘"

    @pytest.mark.asyncio
    async def test_요청_seq_를_되돌려준다(self):
        # 클라이언트가 어느 요청의 응답인지 알아야 한다
        ctx = _make_ctx(
            entity=ResolvedEntity(
                kind=EntityKind.OBJECT,
                entity=_make_object({"readable": {"content": {"ko": "본문"}}}),
                source="inventory",
            )
        )
        ctx.seq = 52

        await ReadHandler().handle(ctx)

        assert ctx.session.sent[0]["seq"] == 52
