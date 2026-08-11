# -*- coding: utf-8 -*-
"""어드민 변경 후 게임 상태 재동기화

기존 Node 웹어드민은 DB 를 직접 수정해 서버가 들고 있는 상태와 어긋났다.
어드민 채널은 변경 직후 영향받는 플레이어에게 방 정보를 다시 보낸다.

무효화할 매니저 캐시는 없다. 확인한 결과 DB 행을 메모리에 들고 있는 매니저가
없다. `MonsterManager._spawn_points` 와 `_global_spawn_limits` 는 JSON 설정에서
읽은 값이고, `PriceResolver` 는 요청마다 DB 를 조회하며, `faction_rules` 는
테이블을 읽지 않는 정적 규칙이다. 따라서 재동기화는 세션으로 밀어 보내는
쪽만 남는다.

프로토콜 계약: docs/protocol/admin.md
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# 방에 영향을 주는 리소스. 그 밖의 리소스는 변경해도 방 화면이 바뀌지 않는다
ROOM_AFFECTING = frozenset({"rooms", "monsters", "objects"})


class GameStateRefresher:
    """어드민 변경이 게임 상태에 미치는 영향을 세션에 반영한다."""

    def __init__(self, game_engine: Optional[Any] = None) -> None:
        self.game_engine = game_engine

    async def after_mutation(
        self, resource_name: str, row: Optional[dict[str, Any]]
    ) -> int:
        """변경된 행이 속한 방의 플레이어에게 방 정보를 다시 보낸다.

        Args:
            resource_name: 변경된 리소스 이름
            row: 변경 전후의 행. 방 위치를 여기서 찾는다

        Returns:
            방 정보를 다시 보낸 세션 수
        """
        if self.game_engine is None or resource_name not in ROOM_AFFECTING or not row:
            return 0

        try:
            room_ids = await self._affected_rooms(resource_name, row)
        except Exception as e:
            logger.error(f"어드민 변경 후 영향 방 산출 실패: {e}", exc_info=True)
            return 0

        if not room_ids:
            return 0

        return await self._resend_room_info(room_ids)

    async def _affected_rooms(
        self, resource_name: str, row: dict[str, Any]
    ) -> set[str]:
        """변경된 행이 속한 방 id 를 찾는다.

        방은 자기 자신이고, 몬스터는 좌표로, 오브젝트는 `location_type` 이
        방일 때만 `location_id` 로 방을 가리킨다.
        """
        if resource_name == "rooms":
            room_id = row.get("id")
            return {room_id} if isinstance(room_id, str) else set()

        if resource_name == "objects":
            location_type = str(row.get("location_type") or "").lower()
            location_id = row.get("location_id")

            if location_type == "room" and isinstance(location_id, str):
                return {location_id}
            return set()

        # 몬스터는 좌표로만 위치를 갖는다. 좌표가 겹치는 방이 있으므로 여럿일 수 있다
        x, y = row.get("x"), row.get("y")

        if x is None or y is None:
            return set()

        rooms = await self.game_engine.world_manager.get_rooms_in_area(x, y, 0)
        return {room.id for room in rooms if room.x == x and room.y == y}

    async def _resend_room_info(self, room_ids: set[str]) -> int:
        """해당 방에 있는 인증된 세션에 방 정보를 다시 보낸다."""
        sessions = self.game_engine.session_manager.get_authenticated_sessions()
        movement = self.game_engine.movement_manager
        sent = 0

        for session in sessions:
            room_id = getattr(session, "current_room_id", None)

            if room_id not in room_ids:
                continue

            try:
                await movement.send_room_info_to_player(session, room_id)
                sent += 1
            except Exception as e:
                logger.error(f"어드민 변경 후 방 정보 재전송 실패: {e}")

        if sent:
            logger.info(f"어드민 변경 후 방 정보 재전송: {sent}개 세션")

        return sent
