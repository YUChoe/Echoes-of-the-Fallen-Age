# -*- coding: utf-8 -*-
"""어드민 삭제의 참조 무결성 검사

선언된 외래키만으로는 부족하다. 실제 DB 에서 확인한 참조는 다음과 같다.

- `players.faction_id`, `faction_relations.faction_a_id/b_id` 만 FK 로 선언돼 있다
- `monsters.faction_id` 는 FK 가 없다. 이미 `factions` 에 없는 `townspeople` 을
  가리키는 몬스터가 1건 있다
- `game_objects.location_id` 는 `location_type` 에 따라 방·소유자·컨테이너를
  가리킨다. FK 가 없고 `location_type` 값이 `room`/`ROOM` 처럼 대소문자가
  섞여 있어 비교를 대소문자 무시로 해야 한다
- `room_connections` 와 `monsters` 는 방 id 가 아니라 좌표로 방을 가리킨다.
  좌표가 같은 방이 둘 있으므로(현재 1쌍) 하나를 지워도 참조가 끊기지 않는다

프로토콜 계약: docs/protocol/admin.md
"""

from dataclasses import dataclass
from typing import Any, Optional

from ...database.table_gateway import TableGateway
from .resources import RESOURCES, AdminResource

# 응답에 담을 참조 행 표본의 최대 개수
MAX_SAMPLES = 5


@dataclass(frozen=True)
class ReferenceRule:
    """삭제 대상을 가리키는 참조 하나

    Attributes:
        resource: 참조하는 쪽 리소스 이름. 응답에 그대로 실린다
        columns: 참조하는 쪽의 컬럼
        source_columns: 삭제 대상 행에서 값을 뽑을 컬럼
        type_column: 참조 종류를 구분하는 컬럼. 대소문자를 무시해 비교한다
        type_value: `type_column` 이 가져야 할 값
        unique_source: 참이면 `source_columns` 로 삭제 대상 행이 유일할 때만
            참조로 본다. 좌표처럼 여러 행이 같은 값을 가질 수 있는 경우다
    """

    resource: str
    columns: tuple[str, ...]
    source_columns: tuple[str, ...]
    type_column: Optional[str] = None
    type_value: Optional[str] = None
    unique_source: bool = False


# 삭제 대상 리소스 이름 → 그것을 가리키는 참조들
RULES: dict[str, tuple[ReferenceRule, ...]] = {
    "factions": (
        ReferenceRule("players", ("faction_id",), ("id",)),
        ReferenceRule("monsters", ("faction_id",), ("id",)),
        ReferenceRule("faction_relations", ("faction_a_id",), ("id",)),
        ReferenceRule("faction_relations", ("faction_b_id",), ("id",)),
    ),
    "rooms": (
        ReferenceRule(
            "objects", ("location_id",), ("id",), "location_type", "room"
        ),
        ReferenceRule(
            "room_connections",
            ("from_x", "from_y"),
            ("x", "y"),
            unique_source=True,
        ),
        ReferenceRule(
            "room_connections", ("to_x", "to_y"), ("x", "y"), unique_source=True
        ),
        ReferenceRule("monsters", ("x", "y"), ("x", "y"), unique_source=True),
    ),
    "players": (
        ReferenceRule(
            "objects", ("location_id",), ("id",), "location_type", "inventory"
        ),
    ),
    "monsters": (
        ReferenceRule(
            "objects", ("location_id",), ("id",), "location_type", "inventory"
        ),
    ),
    "objects": (
        ReferenceRule(
            "objects", ("location_id",), ("id",), "location_type", "container"
        ),
    ),
}


class ReferenceChecker:
    """삭제 전에 참조를 세고 표본을 모은다."""

    def __init__(self, db_manager: Any) -> None:
        self._db = db_manager
        self._gateways: dict[str, TableGateway] = {}

    def _gateway(self, resource: AdminResource) -> TableGateway:
        """리소스별 게이트웨이를 만들어 재사용한다."""
        gateway = self._gateways.get(resource.name)

        if gateway is None:
            gateway = TableGateway(self._db, resource.table, resource.primary_key)
            self._gateways[resource.name] = gateway

        return gateway

    async def find_references(
        self, target: AdminResource, row: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """삭제 대상 행을 가리키는 참조를 모은다.

        Args:
            target: 삭제 대상 리소스
            row: 삭제 대상 행. 참조 값을 여기서 뽑는다

        Returns:
            참조별 요약. 참조가 없으면 빈 리스트
        """
        found: list[dict[str, Any]] = []

        for rule in RULES.get(target.name, ()):
            summary = await self._check_rule(target, row, rule)
            if summary is not None:
                found.append(summary)

        return found

    async def _check_rule(
        self, target: AdminResource, row: dict[str, Any], rule: ReferenceRule
    ) -> Optional[dict[str, Any]]:
        """규칙 하나를 검사한다. 참조가 없으면 None."""
        values = [row.get(column) for column in rule.source_columns]

        if any(value is None for value in values):
            return None

        if rule.unique_source and not await self._is_unique_source(
            target, rule, values
        ):
            # 같은 값을 가진 행이 더 있으므로 이 행을 지워도 참조가 끊기지 않는다
            return None

        referrer = RESOURCES[rule.resource]
        gateway = self._gateway(referrer)

        filters = dict(zip(rule.columns, values))
        ci_filters = (
            {rule.type_column: rule.type_value} if rule.type_column else None
        )

        # 자기 자신은 참조로 세지 않는다. 컨테이너가 스스로를 담을 수 없다
        count = await gateway.count_rows(filters, ci_filters)
        rows = await gateway.list_rows(
            filters=filters, ci_filters=ci_filters, limit=MAX_SAMPLES
        )

        samples = [
            {column: sample[column] for column in referrer.primary_key}
            for sample in rows
            if not _is_same_row(target, referrer, row, sample)
        ]

        if referrer.name == target.name:
            count -= len(rows) - len(samples)

        if count <= 0:
            return None

        return {
            "resource": rule.resource,
            "columns": list(rule.columns),
            "count": count,
            "samples": samples,
        }

    async def _is_unique_source(
        self, target: AdminResource, rule: ReferenceRule, values: list[Any]
    ) -> bool:
        """삭제 대상 행이 `source_columns` 값으로 유일한지 확인한다."""
        gateway = self._gateway(target)
        filters = dict(zip(rule.source_columns, values))

        return await gateway.count_rows(filters) <= 1


def _is_same_row(
    target: AdminResource,
    referrer: AdminResource,
    row: dict[str, Any],
    sample: dict[str, Any],
) -> bool:
    """참조 행이 삭제 대상 행 자신인지 판정한다."""
    if referrer.table != target.table:
        return False

    return all(sample.get(column) == row.get(column) for column in target.primary_key)
