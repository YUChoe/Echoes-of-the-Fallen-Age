# -*- coding: utf-8 -*-
"""어드민 통계와 맵

`admin_stats` 는 `AdminManager` 가 이미 dict 를 반환하므로 그대로 전달한다.
`admin_map` 은 `MapExporter` 가 만든 쿼리 결과를 전달하며, HTML 렌더링은
Godot 어드민 패널이 담당한다.

두 응답 모두 좌표와 종족 분포, 접속자 정보를 노출하므로 어드민 채널 전용이다.

프로토콜 계약: docs/protocol/admin.md
"""

import logging
from typing import Any, Optional

from ...utils.exceptions import AdminOperationError
from ...utils.map_exporter import MapExporter
from ..serialization import admin_map_result, admin_stats_result
from .admin_session import AdminSession

logger = logging.getLogger(__name__)

# 통계에 담을 테이블별 행 수
COUNT_TABLES = {
    "rooms": "rooms",
    "monsters": "monsters",
    "players": "players",
    "objects": "game_objects",
    "factions": "factions",
}


class AdminInsightHandlers:
    """`admin_stats` 와 `admin_map` 을 처리한다."""

    def __init__(self, game_engine: Optional[Any] = None) -> None:
        self.game_engine = game_engine
        self._map: Optional[MapExporter] = None

    def register_all(self, server: Any) -> None:
        """어드민 서버에 처리기를 등록한다."""
        server.register("admin_stats", self.handle_stats)
        server.register("admin_map", self.handle_map)

    async def handle_stats(
        self, session: AdminSession, message: dict[str, Any]
    ) -> None:
        """`admin_stats` 를 처리한다."""
        seq = message.get("seq")

        if self.game_engine is None:
            await session.send_rejected(
                "admin_stats", "INTERNAL_ERROR", "game engine not initialised", seq
            )
            return

        try:
            stats = dict(await self.game_engine.admin_manager.get_admin_stats())
            stats["counts"] = await self._counts()
        except AdminOperationError as e:
            await session.send_rejected("admin_stats", e.reason_code, e.detail, seq)
            return
        except Exception as e:
            logger.error(f"어드민 통계 조회 실패: {e}", exc_info=True)
            await session.send_rejected(
                "admin_stats", "INTERNAL_ERROR", str(e), seq
            )
            return

        await session.send_message(admin_stats_result(seq, stats))

    async def handle_map(self, session: AdminSession, message: dict[str, Any]) -> None:
        """`admin_map` 을 처리한다."""
        seq = message.get("seq")

        if self.game_engine is None:
            await session.send_rejected(
                "admin_map", "INTERNAL_ERROR", "game engine not initialised", seq
            )
            return

        include_descriptions = message.get("include_descriptions") is True

        try:
            data = await self._exporter().build_map_data(include_descriptions)
        except Exception as e:
            logger.error(f"어드민 맵 생성 실패: {e}", exc_info=True)
            await session.send_rejected("admin_map", "INTERNAL_ERROR", str(e), seq)
            return

        await session.send_message(
            admin_map_result(seq, data["bounds"], data["rooms"])
        )

    # 보조 -------------------------------------------------------------------

    def _exporter(self) -> MapExporter:
        """맵 데이터 생성기를 만들어 재사용한다."""
        if self._map is None:
            self._map = MapExporter(self.game_engine.db_manager)
        return self._map

    async def _counts(self) -> dict[str, int]:
        """테이블별 행 수와 접속자 수.

        `AdminManager.get_admin_stats()` 에 없는 값이라 여기서 채운다.
        """
        db = self.game_engine.db_manager
        counts: dict[str, int] = {}

        for name, table in COUNT_TABLES.items():
            row = await db.fetch_one(f"SELECT COUNT(*) AS total FROM {table}")
            counts[name] = int(row["total"]) if row else 0

        counts["players_online"] = len(
            self.game_engine.session_manager.get_authenticated_sessions()
        )

        return counts
