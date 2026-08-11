# -*- coding: utf-8 -*-
"""테이블 단위 일반 CRUD 게이트웨이

어드민 채널이 8개 리소스를 편집하기 위한 SQL 을 한곳에 모은다. 리소스마다
리포지토리를 만들지 않는 이유는 어드민이 모델이 아니라 DB 행을 그대로 다루기
때문이다. 계약이 `rows` 에 원본 컬럼명을 유지하도록 규정한다.

`BaseRepository` 는 기본키가 `id` 단일 컬럼이라고 가정하고 모델 인스턴스를
돌려준다. `item_prices` 는 기본키가 `template_id` 이고 `faction_relations` 는
복합키라 그 경로를 쓸 수 없다. 이 게이트웨이는 기본키를 인자로 받는다.

컬럼 이름은 모두 실제 테이블 컬럼과 대조한 뒤에만 SQL 에 넣는다. 값은 항상
바인딩 파라미터로 전달한다.
"""

import json
import logging
from typing import Any, Optional, Sequence

from .connection import DatabaseManager

logger = logging.getLogger(__name__)

# 정렬 방향으로 허용하는 값
SORT_ORDERS = ("asc", "desc")


class TableGatewayError(Exception):
    """게이트웨이 사용 오류

    호출자가 잘못된 컬럼이나 기본키를 넘겼을 때 발생한다. DB 오류가 아니다.
    """


class TableGateway:
    """테이블 하나에 대한 목록·상세·생성·수정·삭제"""

    def __init__(
        self,
        db_manager: DatabaseManager,
        table: str,
        primary_key: Sequence[str],
    ) -> None:
        """
        Args:
            db_manager: 데이터베이스 매니저
            table: 대상 테이블명. 호출자가 신뢰할 수 있는 값만 넘긴다
            primary_key: 기본키 컬럼. 복합키면 둘 이상
        """
        self._db = db_manager
        self._table = table
        self._primary_key = tuple(primary_key)
        self._columns: Optional[frozenset[str]] = None

    @property
    def primary_key(self) -> tuple[str, ...]:
        """기본키 컬럼 이름"""
        return self._primary_key

    async def columns(self) -> frozenset[str]:
        """테이블의 실제 컬럼 집합. 최초 1회만 조회한다."""
        if self._columns is None:
            info = await self._db.get_table_info(self._table)
            self._columns = frozenset(col["name"] for col in info)
        return self._columns

    async def _validate_columns(self, names: Sequence[str]) -> None:
        """컬럼 이름이 실제 테이블에 있는지 확인한다.

        SQL 에 이름을 직접 넣기 전에 반드시 거친다.

        Raises:
            TableGatewayError: 존재하지 않는 컬럼이 있는 경우
        """
        known = await self.columns()
        unknown = [name for name in names if name not in known]

        if unknown:
            raise TableGatewayError(
                f"unknown column(s) on {self._table}: {', '.join(sorted(unknown))}"
            )

    async def _key_clause(self, key: dict[str, Any]) -> tuple[str, list[Any]]:
        """기본키 WHERE 절과 바인딩 값을 만든다.

        Raises:
            TableGatewayError: 기본키 컬럼이 빠졌거나 남는 항목이 있는 경우
        """
        missing = [column for column in self._primary_key if column not in key]
        if missing:
            raise TableGatewayError(
                f"missing primary key column(s): {', '.join(missing)}"
            )

        extra = [name for name in key if name not in self._primary_key]
        if extra:
            raise TableGatewayError(
                f"not a primary key column: {', '.join(sorted(extra))}"
            )

        clause = " AND ".join(f"{column} = ?" for column in self._primary_key)
        values = [key[column] for column in self._primary_key]
        return clause, values

    async def _filter_clause(
        self, filters: Optional[dict[str, Any]]
    ) -> tuple[str, list[Any]]:
        """동등 비교 WHERE 절을 만든다. 필터가 없으면 빈 절을 돌려준다."""
        if not filters:
            return "", []

        await self._validate_columns(list(filters))

        clause = " WHERE " + " AND ".join(f"{column} = ?" for column in filters)
        return clause, [_bind_value(value) for value in filters.values()]

    async def list_rows(
        self,
        filters: Optional[dict[str, Any]] = None,
        sort_field: Optional[str] = None,
        sort_order: str = "asc",
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """행 목록을 조회한다.

        정렬 기준을 지정하지 않으면 기본키로 정렬한다. 페이지네이션이 안정적으로
        동작하려면 순서가 결정적이어야 한다.

        Args:
            filters: 컬럼별 동등 비교 조건
            sort_field: 정렬 컬럼
            sort_order: `asc` 또는 `desc`
            limit: 최대 행 수
            offset: 건너뛸 행 수

        Raises:
            TableGatewayError: 컬럼이나 정렬 방향이 올바르지 않은 경우
        """
        if sort_order not in SORT_ORDERS:
            raise TableGatewayError(f"sort order must be asc or desc: {sort_order}")

        if sort_field is not None:
            await self._validate_columns([sort_field])
            order_columns = [sort_field]
        else:
            order_columns = list(self._primary_key)

        where, values = await self._filter_clause(filters)
        order_by = ", ".join(f"{column} {sort_order.upper()}" for column in order_columns)

        query = (
            f"SELECT * FROM {self._table}{where} "
            f"ORDER BY {order_by} LIMIT ? OFFSET ?"
        )

        return await self._db.fetch_all(query, tuple(values + [limit, offset]))

    async def count_rows(self, filters: Optional[dict[str, Any]] = None) -> int:
        """조건에 맞는 행 수를 센다."""
        where, values = await self._filter_clause(filters)
        query = f"SELECT COUNT(*) AS total FROM {self._table}{where}"

        result = await self._db.fetch_one(query, tuple(values))
        return int(result["total"]) if result else 0

    async def get_row(self, key: dict[str, Any]) -> Optional[dict[str, Any]]:
        """기본키로 행 하나를 조회한다."""
        clause, values = await self._key_clause(key)
        query = f"SELECT * FROM {self._table} WHERE {clause}"

        return await self._db.fetch_one(query, tuple(values))

    async def insert_row(self, values: dict[str, Any]) -> dict[str, Any]:
        """행을 삽입하고 삽입된 행을 돌려준다.

        기본키 값은 호출자가 채워서 넘긴다. 생성 규칙은 리소스마다 다르므로
        게이트웨이가 판단하지 않는다.

        Raises:
            TableGatewayError: 컬럼이 올바르지 않거나 삽입 후 행을 찾지 못한 경우
        """
        if not values:
            raise TableGatewayError("no values to insert")

        await self._validate_columns(list(values))

        columns = list(values)
        placeholders = ", ".join("?" for _ in columns)
        bound = [_bind_value(values[column]) for column in columns]

        query = (
            f"INSERT INTO {self._table} ({', '.join(columns)}) "
            f"VALUES ({placeholders})"
        )

        await self._db.execute(query, tuple(bound))
        await self._db.commit()

        key = {column: values[column] for column in self._primary_key if column in values}
        inserted = await self.get_row(key) if len(key) == len(self._primary_key) else None

        if inserted is None:
            raise TableGatewayError("inserted row could not be read back")

        logger.info(f"{self._table} 행 삽입: {key}")
        return inserted

    async def update_row(
        self, key: dict[str, Any], values: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """기본키로 행을 수정하고 수정된 행을 돌려준다.

        Returns:
            수정된 행. 대상이 없으면 None

        Raises:
            TableGatewayError: 컬럼이나 기본키가 올바르지 않은 경우
        """
        if not values:
            raise TableGatewayError("no values to update")

        await self._validate_columns(list(values))
        clause, key_values = await self._key_clause(key)

        if await self.get_row(key) is None:
            return None

        set_clause = ", ".join(f"{column} = ?" for column in values)
        bound = [_bind_value(value) for value in values.values()]

        query = f"UPDATE {self._table} SET {set_clause} WHERE {clause}"

        await self._db.execute(query, tuple(bound + key_values))
        await self._db.commit()

        logger.info(f"{self._table} 행 수정: {key}")
        return await self.get_row(key)

    async def delete_row(self, key: dict[str, Any]) -> bool:
        """기본키로 행을 삭제한다.

        Returns:
            삭제했으면 True. 대상이 없으면 False
        """
        clause, values = await self._key_clause(key)

        if await self.get_row(key) is None:
            return False

        query = f"DELETE FROM {self._table} WHERE {clause}"

        await self._db.execute(query, tuple(values))
        await self._db.commit()

        logger.info(f"{self._table} 행 삭제: {key}")
        return True


def _bind_value(value: Any) -> Any:
    """파이썬 값을 SQLite 바인딩 값으로 바꾼다.

    dict 와 list 는 이 스키마에서 TEXT 컬럼의 JSON 이다. bool 은 SQLite 가
    정수로 저장하므로 그대로 넘겨도 되지만 명시적으로 변환한다.
    """
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value
