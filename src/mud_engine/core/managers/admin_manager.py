# -*- coding: utf-8 -*-
"""관리자 기능 관리자

어드민 채널(TCP 4001)이 호출한다. 세션을 인자로 받지 않고 결과 데이터를
반환하며, 실패는 `AdminOperationError` 로 알린다. 완성된 한국어 문장을 세션에
보내던 방식은 어드민 채널 전환(Task 7.6)에서 제거했다.

실행 주체는 `actor` 로 받아 로그와 세계 변경 이벤트에만 쓴다. 어드민 주체는
게임 플레이어가 아니므로 플레이어 id 를 갖지 않는다.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict

from ..event_bus import Event, EventType
from ...server.serialization import build_event
from ...utils.exceptions import AdminOperationError

if TYPE_CHECKING:
    from ..game_engine import GameEngine

logger = logging.getLogger(__name__)

# 실행 주체를 알 수 없을 때 로그에 남기는 값
UNKNOWN_ACTOR = "unknown"


class AdminManager:
    """관리자 기능을 담당하는 매니저"""

    def __init__(self, game_engine: 'GameEngine'):
        self.game_engine = game_engine

    async def create_room_realtime(
        self, room_data: Dict[str, Any], actor: str = UNKNOWN_ACTOR
    ) -> Dict[str, Any]:
        """실시간으로 새로운 방을 생성합니다.

        Args:
            room_data: 방 생성 데이터
            actor: 실행 주체. 로그와 이벤트에만 쓴다

        Returns:
            생성된 방 id 를 담은 딕셔너리

        Raises:
            AdminOperationError: 생성에 실패한 경우
        """
        try:
            new_room = await self.game_engine.world_manager.create_room(room_data)
        except Exception as e:
            logger.error(f"실시간 방 생성 실패: {e}")
            raise AdminOperationError("INTERNAL_ERROR", f"room creation failed: {e}") from e

        await self._publish_world_update(
            actor, {"action": "room_created", "room_id": new_room.id}
        )

        logger.info(f"실시간 방 생성: {new_room.id} (주체: {actor})")
        return {"room_id": new_room.id}

    async def update_room_realtime(
        self, room_id: str, updates: Dict[str, Any], actor: str = UNKNOWN_ACTOR
    ) -> Dict[str, Any]:
        """실시간으로 방 정보를 수정합니다.

        수정된 방에 있는 플레이어에게는 어드민 채널의 재동기화 계층이 방 정보를
        다시 보낸다. 매니저는 세계 변경 이벤트만 발행한다.

        Args:
            room_id: 수정할 방 id
            updates: 변경할 값
            actor: 실행 주체

        Returns:
            수정된 방 id 를 담은 딕셔너리

        Raises:
            AdminOperationError: 방이 없거나 수정에 실패한 경우
        """
        try:
            updated_room = await self.game_engine.world_manager.update_room(room_id, updates)
        except Exception as e:
            logger.error(f"실시간 방 수정 실패 ({room_id}): {e}")
            raise AdminOperationError("INTERNAL_ERROR", f"room update failed: {e}") from e

        if not updated_room:
            raise AdminOperationError("NOT_FOUND", f"room not found: {room_id}")

        await self._publish_world_update(
            actor,
            {"action": "room_updated", "room_id": room_id, "updates": updates},
        )

        logger.info(f"실시간 방 수정: {room_id} (주체: {actor})")
        return {"room_id": room_id}

    async def validate_and_repair_world(self) -> Dict[str, Any]:
        """게임 세계의 무결성을 검증하고 자동으로 수정합니다.

        기존에 명령어로 노출되지 않았던 기능이다.

        Returns:
            검증 결과와 수정 결과

        Raises:
            AdminOperationError: 검증에 실패한 경우
        """
        try:
            issues = await self.game_engine.world_manager.validate_world_integrity()

            repair_result: Dict[str, Any] = {}
            if any(issues.values()):
                repair_result = await self.game_engine.world_manager.repair_world_integrity()
        except Exception as e:
            logger.error(f"게임 세계 무결성 검증 실패: {e}")
            raise AdminOperationError(
                "INTERNAL_ERROR", f"world validation failed: {e}"
            ) from e

        total_issues = sum(len(issue_list) for issue_list in issues.values())
        total_fixed = sum(repair_result.values())

        logger.info(
            f"게임 세계 무결성 검증 완료: 발견 {total_issues}건, 수정 {total_fixed}건"
        )

        return {
            "validation": issues,
            "repair": repair_result,
            "issues_found": total_issues,
            "issues_fixed": total_fixed,
        }

    async def kick_player(
        self,
        target_username: str,
        actor: str = UNKNOWN_ACTOR,
        reason: str = "관리자에 의해 추방",
    ) -> Dict[str, Any]:
        """플레이어를 서버에서 추방합니다.

        Args:
            target_username: 추방할 플레이어 이름
            actor: 실행 주체
            reason: 추방 이유

        Returns:
            추방한 플레이어 이름과 사유

        Raises:
            AdminOperationError: 접속 중이 아니거나 추방에 실패한 경우
        """
        target_session = self._find_session(target_username)

        if target_session is None:
            raise AdminOperationError(
                "PLAYER_NOT_ONLINE", f"player not online: {target_username}"
            )

        try:
            # 추방 통보. 계약에 전용 타입이 없어 event 로 보낸다. 연결이 곧
            # 끊어지므로 클라이언트는 이 키로 사유를 표시한다
            await target_session.send_message(
                build_event("system.kicked", {"reason": reason, "admin": actor})
            )

            await self.game_engine.remove_player_session(
                target_session, f"관리자 추방: {reason}"
            )
        except Exception as e:
            logger.error(f"플레이어 추방 실패 ({target_username}): {e}")
            raise AdminOperationError("INTERNAL_ERROR", f"kick failed: {e}") from e

        logger.info(f"플레이어 추방: {target_username} (주체: {actor}, 사유: {reason})")
        return {"target_player": target_username, "reason": reason}

    async def get_admin_stats(self) -> Dict[str, Any]:
        """관리자용 서버 통계 정보를 반환합니다.

        Returns:
            엔진·플레이어·방·객체 통계

        Raises:
            AdminOperationError: 조회에 실패한 경우
        """
        try:
            authenticated_sessions = (
                self.game_engine.session_manager.get_authenticated_sessions()
            )

            return {
                "engine": self.game_engine.get_stats(),
                "players": {
                    "total_online": len(authenticated_sessions),
                    "online": [
                        {
                            "username": session.player.username,
                            "session_id": session.session_id,
                            "current_room": getattr(session, 'current_room_id', None),
                            "ip_address": session.ip_address,
                        }
                        for session in authenticated_sessions
                        if session.player
                    ],
                },
                "rooms": await self._get_room_statistics(),
                "objects": await self._get_object_statistics(),
            }
        except Exception as e:
            logger.error(f"관리자 통계 조회 실패: {e}")
            raise AdminOperationError("INTERNAL_ERROR", f"stats failed: {e}") from e

    # 보조 -------------------------------------------------------------------

    def _find_session(self, username: str) -> Any:
        """접속 중인 플레이어의 세션을 찾는다. 없으면 None."""
        for session in self.game_engine.session_manager.get_authenticated_sessions():
            if session.player and session.player.username == username:
                return session
        return None

    async def _publish_world_update(self, actor: str, data: Dict[str, Any]) -> None:
        """세계 변경 이벤트를 발행한다."""
        await self.game_engine.event_bus.publish(Event(
            event_type=EventType.WORLD_UPDATED,
            source=actor,
            data={**data, "actor": actor},
        ))

    async def _get_room_statistics(self) -> Dict[str, Any]:
        """방 통계 정보 조회"""
        try:
            rooms = await self.game_engine.world_manager.get_all_rooms_for_stats()
            occupied = {
                getattr(session, 'current_room_id', None)
                for session in self.game_engine.session_manager.get_authenticated_sessions()
            }

            return {
                "total_rooms": len(rooms),
                "rooms_with_players": len([room for room in rooms if room.id in occupied]),
            }
        except Exception as e:
            logger.error(f"방 통계 조회 실패: {e}")
            return {"total_rooms": 0, "rooms_with_players": 0}

    async def _get_object_statistics(self) -> Dict[str, Any]:
        """객체 통계 정보 조회"""
        try:
            objects = await self.game_engine.world_manager.get_all_objects_for_stats()

            by_location: Dict[str, int] = {}
            for obj in objects:
                key = str(getattr(obj, 'location_type', 'unknown') or 'unknown').lower()
                by_location[key] = by_location.get(key, 0) + 1

            return {"total_objects": len(objects), "by_location_type": by_location}
        except Exception as e:
            logger.error(f"객체 통계 조회 실패: {e}")
            return {"total_objects": 0, "by_location_type": {}}
