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
    """핸들러 호출에 필요한 최소 컨텍스트"""
    session = SimpleNamespace(
        session_id="session-1",
        is_authenticated=True,
        player=SimpleNamespace(id="player-1", username="tester", is_admin=False),
        in_combat=False,
        combat_id=None,
        current_room_id="room-1",
        locale="ko",
        stamina=5.0,
        max_stamina=5.0,
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
