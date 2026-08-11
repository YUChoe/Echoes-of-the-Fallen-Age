# -*- coding: utf-8 -*-
"""어드민 리소스 CRUD 처리기

`admin_list`, `admin_get`, `admin_create`, `admin_update`, `admin_delete` 를
처리한다. SQL 은 `TableGateway` 가 담당하고 여기서는 요청 검증, 기본키 해석,
노출 정책만 다룬다.

기본키가 단일 컬럼인 리소스는 계약대로 `id` 를 받는다. `faction_relations`
처럼 복합키인 리소스는 `key` 오브젝트를 받는다. 단일키 리소스에도 `key` 를
쓸 수 있으며 두 표현은 같은 결과를 낸다.

프로토콜 계약: docs/protocol/admin.md
"""

import logging
import uuid
from typing import Any, Optional

from ...database.table_gateway import TableGateway, TableGatewayError
from ..serialization import (
    admin_get_result,
    admin_list_result,
    admin_mutate_result,
)
from .admin_session import AdminSession
from .references import ReferenceChecker
from .refresh import GameStateRefresher
from .resources import AdminResource, get_resource, redact

logger = logging.getLogger(__name__)

# 목록 요청의 기본 페이지 크기와 상한. 한 라인의 최대 길이가 256KB 이므로
# 상한 없이 열어두면 응답이 프레이밍 한계를 넘을 수 있다
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


class AdminQueryHandlers:
    """8개 리소스의 목록·상세·생성·수정·삭제를 처리한다."""

    def __init__(
        self, db_manager: Any, game_engine: Optional[Any] = None
    ) -> None:
        self._db = db_manager
        self._gateways: dict[str, TableGateway] = {}
        self._references = ReferenceChecker(db_manager)
        self._refresher = GameStateRefresher(game_engine)

    @property
    def refresher(self) -> GameStateRefresher:
        """게임 상태 재동기화기. main.py 가 게임 엔진을 나중에 배선한다."""
        return self._refresher

    def register_all(self, server: Any) -> None:
        """어드민 서버에 처리기를 등록한다."""
        server.register("admin_list", self.handle_list)
        server.register("admin_get", self.handle_get)
        server.register("admin_create", self.handle_create)
        server.register("admin_update", self.handle_update)
        server.register("admin_delete", self.handle_delete)

    def _gateway(self, resource: AdminResource) -> TableGateway:
        """리소스별 게이트웨이를 만들어 재사용한다. 컬럼 조회를 반복하지 않는다."""
        gateway = self._gateways.get(resource.name)

        if gateway is None:
            gateway = TableGateway(self._db, resource.table, resource.primary_key)
            self._gateways[resource.name] = gateway

        return gateway

    # 요청 처리 --------------------------------------------------------------

    async def handle_list(
        self, session: AdminSession, message: dict[str, Any]
    ) -> None:
        """`admin_list` 를 처리한다."""
        seq = message.get("seq")
        resource = get_resource(message.get("resource"))

        if resource is None:
            await self._reject_resource(session, "admin_list", message, seq)
            return

        page = _positive_int(message.get("page"), default=1)
        page_size = min(
            _positive_int(message.get("page_size"), default=DEFAULT_PAGE_SIZE),
            MAX_PAGE_SIZE,
        )

        filters = message.get("filter")
        if filters is not None and not isinstance(filters, dict):
            await session.send_rejected(
                "admin_list", "INVALID_PARAMS", "filter must be an object", seq
            )
            return

        sort_field, sort_order, sort_error = _parse_sort(message.get("sort"))
        if sort_error is not None:
            await session.send_rejected(
                "admin_list", "INVALID_PARAMS", sort_error, seq
            )
            return

        gateway = self._gateway(resource)

        try:
            total = await gateway.count_rows(filters)
            rows = await gateway.list_rows(
                filters=filters,
                sort_field=sort_field,
                sort_order=sort_order,
                limit=page_size,
                offset=(page - 1) * page_size,
            )
        except TableGatewayError as e:
            await session.send_rejected("admin_list", "INVALID_PARAMS", str(e), seq)
            return

        await session.send_message(
            admin_list_result(
                seq,
                resource.name,
                page,
                page_size,
                total,
                [redact(resource, row) for row in rows],
            )
        )

    async def handle_get(self, session: AdminSession, message: dict[str, Any]) -> None:
        """`admin_get` 을 처리한다."""
        seq = message.get("seq")
        resource = get_resource(message.get("resource"))

        if resource is None:
            await self._reject_resource(session, "admin_get", message, seq)
            return

        key = self._resolve_key(resource, message)
        if key is None:
            await self._reject_key(session, "admin_get", resource, seq)
            return

        try:
            row = await self._gateway(resource).get_row(key)
        except TableGatewayError as e:
            await session.send_rejected("admin_get", "INVALID_PARAMS", str(e), seq)
            return

        if row is None:
            await session.send_rejected(
                "admin_get", "NOT_FOUND", f"{resource.name} not found: {key}", seq
            )
            return

        await session.send_message(
            admin_get_result(seq, resource.name, key, redact(resource, row))
        )

    async def handle_create(
        self, session: AdminSession, message: dict[str, Any]
    ) -> None:
        """`admin_create` 를 처리한다."""
        seq = message.get("seq")
        resource = get_resource(message.get("resource"))

        if resource is None:
            await self._reject_resource(session, "admin_create", message, seq)
            return

        values = message.get("values")
        if not isinstance(values, dict) or not values:
            await session.send_rejected(
                "admin_create",
                "VALIDATION_FAILED",
                "values must be a non-empty object",
                seq,
            )
            return

        values = dict(values)

        # 기본키를 서버가 만드는 리소스는 클라이언트가 보낸 값을 무시하고
        # uuid 를 채운다. 사람이 정하는 id 를 쓰는 리소스는 요청에 있어야 한다
        if resource.generates_id and not resource.has_composite_key:
            values[resource.primary_key[0]] = str(uuid.uuid4())

        missing = [column for column in resource.primary_key if column not in values]
        if missing:
            await session.send_rejected(
                "admin_create",
                "VALIDATION_FAILED",
                f"missing primary key column(s): {', '.join(missing)}",
                seq,
            )
            return

        forbidden = self._forbidden_columns(resource, values, allow_primary_key=True)
        if forbidden:
            await session.send_rejected(
                "admin_create",
                "VALIDATION_FAILED",
                f"column(s) not writable: {', '.join(forbidden)}",
                seq,
            )
            return

        key = {column: values[column] for column in resource.primary_key}

        try:
            row = await self._gateway(resource).insert_row(values)
        except TableGatewayError as e:
            await session.send_rejected(
                "admin_create", "VALIDATION_FAILED", str(e), seq
            )
            return

        self._audit(session, "create", resource, key, values)
        await self._refresher.after_mutation(resource.name, row)

        await session.send_message(
            admin_mutate_result(
                seq, resource.name, key, True, redact(resource, row)
            )
        )

    async def handle_update(
        self, session: AdminSession, message: dict[str, Any]
    ) -> None:
        """`admin_update` 를 처리한다."""
        seq = message.get("seq")
        resource = get_resource(message.get("resource"))

        if resource is None:
            await self._reject_resource(session, "admin_update", message, seq)
            return

        key = self._resolve_key(resource, message)
        if key is None:
            await self._reject_key(session, "admin_update", resource, seq)
            return

        values = message.get("values")
        if not isinstance(values, dict) or not values:
            await session.send_rejected(
                "admin_update",
                "VALIDATION_FAILED",
                "values must be a non-empty object",
                seq,
            )
            return

        forbidden = self._forbidden_columns(resource, values)
        if forbidden:
            await session.send_rejected(
                "admin_update",
                "VALIDATION_FAILED",
                f"column(s) not writable: {', '.join(forbidden)}",
                seq,
            )
            return

        gateway = self._gateway(resource)

        # 이동을 포함한 변경이면 떠난 방과 도착한 방 모두 갱신해야 한다
        previous = await gateway.get_row(key)

        try:
            row = await gateway.update_row(key, dict(values))
        except TableGatewayError as e:
            await session.send_rejected(
                "admin_update", "VALIDATION_FAILED", str(e), seq
            )
            return

        if row is None:
            await session.send_rejected(
                "admin_update", "NOT_FOUND", f"{resource.name} not found: {key}", seq
            )
            return

        self._audit(session, "update", resource, key, values)
        await self._refresher.after_mutation(resource.name, previous)
        await self._refresher.after_mutation(resource.name, row)

        await session.send_message(
            admin_mutate_result(
                seq, resource.name, key, True, redact(resource, row)
            )
        )

    async def handle_delete(
        self, session: AdminSession, message: dict[str, Any]
    ) -> None:
        """`admin_delete` 를 처리한다.

        다른 레코드가 참조하는 행은 `REFERENCED` 로 거절하고 참조 목록을 함께
        돌려준다. 선언된 외래키만으로는 부족해 실제 참조를 규칙으로 검사한다.
        """
        seq = message.get("seq")
        resource = get_resource(message.get("resource"))

        if resource is None:
            await self._reject_resource(session, "admin_delete", message, seq)
            return

        key = self._resolve_key(resource, message)
        if key is None:
            await self._reject_key(session, "admin_delete", resource, seq)
            return

        gateway = self._gateway(resource)

        try:
            row = await gateway.get_row(key)
        except TableGatewayError as e:
            await session.send_rejected("admin_delete", "INVALID_PARAMS", str(e), seq)
            return

        if row is None:
            await session.send_rejected(
                "admin_delete", "NOT_FOUND", f"{resource.name} not found: {key}", seq
            )
            return

        references = await self._references.find_references(resource, row)

        if references:
            total = sum(item["count"] for item in references)
            await session.send_rejected(
                "admin_delete",
                "REFERENCED",
                f"{resource.name} is referenced by {total} row(s)",
                seq,
                references,
            )
            return

        try:
            deleted = await gateway.delete_row(key)
        except TableGatewayError as e:
            await session.send_rejected("admin_delete", "INVALID_PARAMS", str(e), seq)
            return

        if not deleted:
            await session.send_rejected(
                "admin_delete", "NOT_FOUND", f"{resource.name} not found: {key}", seq
            )
            return

        self._audit(session, "delete", resource, key, None)
        await self._refresher.after_mutation(resource.name, row)

        await session.send_message(admin_mutate_result(seq, resource.name, key, True))

    # 보조 -------------------------------------------------------------------

    @staticmethod
    def _resolve_key(
        resource: AdminResource, message: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """요청의 `id` 또는 `key` 를 기본키 딕셔너리로 바꾼다.

        Returns:
            기본키 딕셔너리. 표현이 올바르지 않으면 None
        """
        key = message.get("key")

        if isinstance(key, dict):
            if set(key) != set(resource.primary_key):
                return None
            return dict(key)

        record_id = message.get("id")

        if isinstance(record_id, (str, int)) and not resource.has_composite_key:
            return {resource.primary_key[0]: record_id}

        return None

    @staticmethod
    def _forbidden_columns(
        resource: AdminResource,
        values: dict[str, Any],
        allow_primary_key: bool = False,
    ) -> list[str]:
        """쓰기가 금지된 컬럼을 찾는다.

        Args:
            allow_primary_key: 생성 요청은 기본키를 담아야 하므로 예외로 둔다
        """
        blocked = resource.readonly_columns | resource.hidden_columns

        if allow_primary_key:
            blocked = blocked - set(resource.primary_key)

        return sorted(column for column in values if column in blocked)

    @staticmethod
    async def _reject_resource(
        session: AdminSession,
        action: str,
        message: dict[str, Any],
        seq: Optional[int],
    ) -> None:
        """알 수 없는 리소스를 거절한다."""
        await session.send_rejected(
            action,
            "INVALID_PARAMS",
            f"unknown resource: {message.get('resource')!r}",
            seq,
        )

    @staticmethod
    async def _reject_key(
        session: AdminSession,
        action: str,
        resource: AdminResource,
        seq: Optional[int],
    ) -> None:
        """기본키 표현이 올바르지 않음을 알린다."""
        columns = ", ".join(resource.primary_key)

        if resource.has_composite_key:
            detail = f"{resource.name} requires key object with: {columns}"
        else:
            detail = f"{resource.name} requires id or key object with: {columns}"

        await session.send_rejected(action, "INVALID_PARAMS", detail, seq)

    @staticmethod
    def _audit(
        session: AdminSession,
        operation: str,
        resource: AdminResource,
        key: dict[str, Any],
        values: Optional[dict[str, Any]],
    ) -> None:
        """변경 작업을 로그에 남긴다.

        DB 테이블 저장 여부는 Task 7.7 에서 결정한다. 그때까지는 실행 주체,
        대상, 변경 내용, 시각을 로그로만 남긴다.
        """
        principal = session.principal.name if session.principal else "unknown"
        changed = sorted(values) if values else []

        logger.info(
            f"어드민 변경: {operation} {resource.name} {key} "
            f"주체={principal} 컬럼={changed}"
        )


def _positive_int(value: Any, default: int) -> int:
    """양의 정수를 얻는다. 그 밖의 값은 기본값으로 대체한다.

    bool 은 int 의 하위 타입이므로 명시적으로 배제한다.
    """
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return default
    return value


def _parse_sort(sort: Any) -> tuple[Optional[str], str, Optional[str]]:
    """`sort` 를 정렬 컬럼과 방향으로 나눈다.

    Returns:
        (컬럼, 방향, 오류 설명). 오류가 있으면 앞의 둘은 무의미하다
    """
    if sort is None:
        return None, "asc", None

    if not isinstance(sort, dict):
        return None, "asc", "sort must be an object"

    field_name = sort.get("field")
    if not isinstance(field_name, str):
        return None, "asc", "sort.field must be a string"

    order = sort.get("order", "asc")
    if order not in ("asc", "desc"):
        return None, "asc", f"sort.order must be asc or desc: {order!r}"

    return field_name, order, None
