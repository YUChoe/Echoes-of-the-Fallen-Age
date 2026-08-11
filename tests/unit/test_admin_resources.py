"""
어드민 리소스 정의와 CRUD 보조 로직 단위 테스트

기본키 해석, 쓰기 금지 컬럼, 노출 정책, 정렬·페이지 파싱을 확인한다.
기본키 값은 문서가 아니라 실제 스키마에서 확인한 것이다.
계약: docs/protocol/admin.md
"""

import pytest

from src.mud_engine.database.table_gateway import TableGatewayError, _bind_value
from src.mud_engine.server import serialization as ser
from src.mud_engine.server.admin.queries import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    AdminQueryHandlers,
    _parse_sort,
    _positive_int,
)
from src.mud_engine.server.admin.resources import RESOURCES, get_resource, redact


# 리소스 정의 ----------------------------------------------------------------


def test_all_eight_resources_are_defined():
    """계약이 규정한 8개 리소스를 모두 제공한다"""
    assert set(RESOURCES) == {
        "players",
        "rooms",
        "room_connections",
        "monsters",
        "objects",
        "item_prices",
        "factions",
        "faction_relations",
    }


def test_objects_maps_to_game_objects_table():
    """리소스 이름과 테이블명이 다른 유일한 경우다"""
    assert RESOURCES["objects"].table == "game_objects"


def test_item_prices_primary_key_is_template_id():
    """실제 스키마의 기본키는 id 가 아니라 template_id 다"""
    resource = RESOURCES["item_prices"]

    assert resource.primary_key == ("template_id",)
    assert resource.has_composite_key is False
    assert resource.generates_id is False


def test_faction_relations_has_composite_key():
    """faction_relations 는 단일 id 컬럼이 없다"""
    resource = RESOURCES["faction_relations"]

    assert resource.primary_key == ("faction_a_id", "faction_b_id")
    assert resource.has_composite_key is True


def test_unknown_resource_returns_none():
    """알 수 없는 이름과 문자열이 아닌 값을 모두 걸러낸다"""
    assert get_resource("nope") is None
    assert get_resource(None) is None
    assert get_resource(42) is None


# 노출 정책 ------------------------------------------------------------------


def test_password_hash_is_redacted_from_player_rows():
    """비밀번호 해시는 응답에 싣지 않는다"""
    row = {"id": "u1", "username": "player5426", "password_hash": "$2b$12$..."}

    assert redact(RESOURCES["players"], row) == {"id": "u1", "username": "player5426"}


def test_redact_leaves_other_resources_untouched():
    """숨길 컬럼이 없으면 행을 그대로 돌려준다"""
    row = {"id": "r1", "description_ko": "광장"}

    assert redact(RESOURCES["rooms"], row) is row


def test_password_hash_is_not_writable():
    """비밀번호는 이 경로로 직접 쓸 수 없다"""
    forbidden = AdminQueryHandlers._forbidden_columns(
        RESOURCES["players"], {"username": "x", "password_hash": "y"}
    )

    assert forbidden == ["password_hash"]


def test_primary_key_is_writable_only_on_create():
    """생성은 기본키를 담아야 하고 수정은 담을 수 없다"""
    resource = RESOURCES["factions"]
    values = {"id": "wild", "name_ko": "야생"}

    assert AdminQueryHandlers._forbidden_columns(resource, values) == ["id"]
    assert (
        AdminQueryHandlers._forbidden_columns(resource, values, allow_primary_key=True)
        == []
    )


# 기본키 해석 ----------------------------------------------------------------


def test_single_key_resource_accepts_id():
    """단일키 리소스는 계약대로 id 를 받는다"""
    key = AdminQueryHandlers._resolve_key(
        RESOURCES["rooms"], {"id": "0a1b2c3d"}
    )

    assert key == {"id": "0a1b2c3d"}


def test_single_key_resource_accepts_key_object():
    """단일키에도 key 오브젝트를 쓸 수 있다"""
    key = AdminQueryHandlers._resolve_key(
        RESOURCES["item_prices"], {"key": {"template_id": "silver_coin"}}
    )

    assert key == {"template_id": "silver_coin"}


def test_composite_key_resource_rejects_id():
    """복합키 리소스에는 id 표현이 성립하지 않는다"""
    key = AdminQueryHandlers._resolve_key(
        RESOURCES["faction_relations"], {"id": "ash_knights"}
    )

    assert key is None


def test_composite_key_requires_every_column():
    """복합키는 컬럼이 하나라도 빠지면 거절한다"""
    resource = RESOURCES["faction_relations"]

    assert (
        AdminQueryHandlers._resolve_key(resource, {"key": {"faction_a_id": "wild"}})
        is None
    )
    assert AdminQueryHandlers._resolve_key(
        resource, {"key": {"faction_a_id": "wild", "faction_b_id": "ash_knights"}}
    ) == {"faction_a_id": "wild", "faction_b_id": "ash_knights"}


def test_key_object_with_extra_column_is_rejected():
    """기본키가 아닌 컬럼이 섞이면 거절한다"""
    key = AdminQueryHandlers._resolve_key(
        RESOURCES["rooms"], {"key": {"id": "r1", "x": 0}}
    )

    assert key is None


# 요청 파싱 ------------------------------------------------------------------


def test_page_defaults_reject_invalid_values():
    """0, 음수, 불리언, 문자열은 기본값으로 대체한다"""
    assert _positive_int(3, DEFAULT_PAGE_SIZE) == 3
    assert _positive_int(0, DEFAULT_PAGE_SIZE) == DEFAULT_PAGE_SIZE
    assert _positive_int(-1, DEFAULT_PAGE_SIZE) == DEFAULT_PAGE_SIZE
    assert _positive_int(True, DEFAULT_PAGE_SIZE) == DEFAULT_PAGE_SIZE
    assert _positive_int("10", DEFAULT_PAGE_SIZE) == DEFAULT_PAGE_SIZE
    assert _positive_int(None, DEFAULT_PAGE_SIZE) == DEFAULT_PAGE_SIZE


def test_page_size_cap_is_below_line_limit():
    """상한이 있어야 응답이 라인 길이 한계를 넘지 않는다"""
    assert MAX_PAGE_SIZE >= DEFAULT_PAGE_SIZE
    assert min(_positive_int(10_000, DEFAULT_PAGE_SIZE), MAX_PAGE_SIZE) == MAX_PAGE_SIZE


def test_sort_absent_defaults_to_ascending_primary_key():
    """정렬을 지정하지 않으면 컬럼 없이 오름차순이다"""
    assert _parse_sort(None) == (None, "asc", None)


def test_sort_parses_field_and_order():
    """계약 형식의 sort 를 컬럼과 방향으로 나눈다"""
    assert _parse_sort({"field": "level", "order": "desc"}) == ("level", "desc", None)


def test_sort_rejects_bad_shapes():
    """형식이 어긋나면 오류 설명을 돌려준다"""
    assert _parse_sort("level")[2] == "sort must be an object"
    assert _parse_sort({"order": "asc"})[2] == "sort.field must be a string"
    assert "sort.order" in (_parse_sort({"field": "x", "order": "up"})[2] or "")


# 바인딩 값 변환 --------------------------------------------------------------


def test_bind_value_converts_bool_to_int():
    """SQLite 는 boolean 을 정수로 저장한다"""
    assert _bind_value(True) == 1
    assert _bind_value(False) == 0


def test_bind_value_serialises_json_columns():
    """dict 와 list 는 이 스키마에서 TEXT 컬럼의 JSON 이다"""
    assert _bind_value(["west", "north"]) == '["west", "north"]'
    assert _bind_value({"hp": 45}) == '{"hp": 45}'


def test_bind_value_keeps_scalars():
    """그 밖의 값은 그대로 넘긴다"""
    assert _bind_value("ash_knights") == "ash_knights"
    assert _bind_value(12) == 12
    assert _bind_value(None) is None


# 메시지 봉투 ----------------------------------------------------------------


def test_admin_list_result_shape():
    """목록 응답 형식"""
    message = ser.admin_list_result(10, "monsters", 1, 50, 66, [{"id": "m1"}])

    assert message["type"] == "admin_list_result"
    assert message["seq"] == 10
    assert message["resource"] == "monsters"
    assert message["total"] == 66
    assert message["rows"] == [{"id": "m1"}]


def test_admin_get_result_carries_key_object():
    """상세 응답은 기본키를 오브젝트로 담는다"""
    message = ser.admin_get_result(
        11, "faction_relations", {"faction_a_id": "wild", "faction_b_id": "ash"}, {}
    )

    assert message["type"] == "admin_get_result"
    assert message["key"] == {"faction_a_id": "wild", "faction_b_id": "ash"}


def test_admin_mutate_result_omits_row_on_delete():
    """삭제 응답에는 행을 담지 않는다"""
    message = ser.admin_mutate_result(12, "rooms", {"id": "r1"}, True)

    assert message["success"] is True
    assert "row" not in message


def test_table_gateway_error_is_not_a_db_error():
    """게이트웨이 오류는 호출자 잘못을 뜻한다"""
    with pytest.raises(TableGatewayError):
        raise TableGatewayError("unknown column")
