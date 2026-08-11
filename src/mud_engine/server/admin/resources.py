# -*- coding: utf-8 -*-
"""어드민 리소스 정의

기존 Node 웹어드민의 `db-client.ts` 가 제공하던 8개 리소스를 서버가 대신
제공한다. 각 리소스는 테이블, 기본키, 노출 정책만 선언하고 SQL 은
`TableGateway` 가 담당한다.

기본키는 문서가 아니라 실제 스키마에서 확인한 값이다. `item_prices` 는
`template_id` 단일키이고 `faction_relations` 는 복합키다.

프로토콜 계약: docs/protocol/admin.md
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class AdminResource:
    """어드민이 편집할 수 있는 테이블 하나

    Attributes:
        name: 계약의 `resource` 값
        table: 대상 테이블명
        primary_key: 기본키 컬럼. 복합키면 둘 이상
        hidden_columns: 응답에서 제거할 컬럼. 비밀번호 해시처럼 노출하면 안 되는 값
        readonly_columns: 생성·수정에서 거절할 컬럼
        generates_id: 생성 시 서버가 uuid 기본키를 만들어 주는지
    """

    name: str
    table: str
    primary_key: tuple[str, ...]
    hidden_columns: frozenset[str] = field(default_factory=frozenset)
    readonly_columns: frozenset[str] = field(default_factory=frozenset)
    generates_id: bool = True

    @property
    def has_composite_key(self) -> bool:
        """기본키가 두 컬럼 이상인지"""
        return len(self.primary_key) > 1


# 생성·수정에서 공통으로 막는 컬럼. 생성 시각은 서버가 정한다
_TIMESTAMPS = frozenset({"created_at", "updated_at"})

RESOURCES: dict[str, AdminResource] = {
    resource.name: resource
    for resource in (
        AdminResource(
            name="players",
            table="players",
            primary_key=("id",),
            # 비밀번호 해시는 목록에도 상세에도 싣지 않는다. 변경은 어드민
            # 액션으로 처리하며 이 경로로 직접 쓰지 못하게 막는다
            hidden_columns=frozenset({"password_hash"}),
            readonly_columns=frozenset({"id", "password_hash"}) | _TIMESTAMPS,
        ),
        AdminResource(
            name="rooms",
            table="rooms",
            primary_key=("id",),
            readonly_columns=frozenset({"id"}) | _TIMESTAMPS,
        ),
        AdminResource(
            name="room_connections",
            table="room_connections",
            primary_key=("id",),
            readonly_columns=frozenset({"id"}) | _TIMESTAMPS,
        ),
        AdminResource(
            name="monsters",
            table="monsters",
            primary_key=("id",),
            readonly_columns=frozenset({"id"}) | _TIMESTAMPS,
        ),
        AdminResource(
            name="objects",
            table="game_objects",
            primary_key=("id",),
            readonly_columns=frozenset({"id"}) | _TIMESTAMPS,
        ),
        AdminResource(
            name="item_prices",
            table="item_prices",
            # 기본키가 uuid 가 아니라 아이템 템플릿 식별자다. 서버가 만들 수 없다
            primary_key=("template_id",),
            readonly_columns=frozenset({"template_id"}),
            generates_id=False,
        ),
        AdminResource(
            name="factions",
            table="factions",
            # 종족 id 는 'ash_knights' 처럼 사람이 정하는 값이다
            primary_key=("id",),
            readonly_columns=frozenset({"id"}) | _TIMESTAMPS,
            generates_id=False,
        ),
        AdminResource(
            name="faction_relations",
            table="faction_relations",
            primary_key=("faction_a_id", "faction_b_id"),
            readonly_columns=frozenset({"faction_a_id", "faction_b_id"}) | _TIMESTAMPS,
            generates_id=False,
        ),
    )
}


def get_resource(name: object) -> Optional[AdminResource]:
    """리소스 이름으로 정의를 찾는다. 알 수 없으면 None."""
    if not isinstance(name, str):
        return None
    return RESOURCES.get(name)


def redact(resource: AdminResource, row: dict) -> dict:
    """응답에 싣지 않을 컬럼을 제거한다."""
    if not resource.hidden_columns:
        return row
    return {key: value for key, value in row.items() if key not in resource.hidden_columns}
