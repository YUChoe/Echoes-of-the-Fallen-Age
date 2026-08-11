# -*- coding: utf-8 -*-
"""플레이어 이동 관리자"""

import logging
from typing import TYPE_CHECKING, Optional, Any
from datetime import datetime

from ..event_bus import Event, EventType
from ..types import SessionType
from ...server.serialization import (
    build_entity_enter,
    build_entity_leave,
    build_event,
    build_room_info,
    serialize_monster,
    serialize_object,
    serialize_player,
)

# 미니맵 렌더링용 주변 방 조회 반경 (칸)
MINIMAP_RADIUS = 2

if TYPE_CHECKING:
    from ..game_engine import GameEngine

logger = logging.getLogger(__name__)


class PlayerMovementManager:
    """플레이어 이동 및 따라가기 시스템을 담당하는 매니저"""

    def __init__(self, game_engine: 'GameEngine'):
        self.game_engine = game_engine

    async def move_player_to_room(self, session: SessionType, room_id: str, skip_followers: bool = False) -> bool:
        """
        플레이어를 특정 방으로 이동시킵니다.

        Args:
            session: 플레이어 세션
            room_id: 목적지 방 ID
            skip_followers: 따라가는 플레이어들 이동 생략 여부

        Returns:
            bool: 이동 성공 여부
        """
        if not session.is_authenticated or not session.player:
            return False

        try:
            logger.debug(f"플레이어 이동 시작: {session.player.username} -> {room_id}")

            # 방이 존재하는지 확인
            room = await self.game_engine.world_manager.get_room(room_id)
            if not room:
                logger.warning(f"존재하지 않는 방으로 이동 시도: {room_id} (플레이어: {session.player.username})")
                await session.send_event("movement.room_not_found", category="movement")
                return False

            # 이전 방 ID 저장
            old_room_id = getattr(session, 'current_room_id', None)

            # 세션의 현재 방 업데이트
            session.current_room_id = room_id
            session.current_room_type = getattr(room, 'room_type', 'unknown')

            # 방 퇴장 이벤트 발행 (이전 방이 있는 경우)
            if old_room_id:
                await self.game_engine.event_bus.publish(Event(
                    event_type=EventType.ROOM_LEFT,
                    source=session.session_id,
                    room_id=old_room_id,
                    data={
                        "player_id": session.player.id,
                        "username": session.player.username,
                        "session_id": session.session_id,
                        "old_room_id": old_room_id,
                        "new_room_id": room_id
                    }
                ))

            # 방 입장 이벤트 발행
            await self.game_engine.event_bus.publish(Event(
                event_type=EventType.ROOM_ENTERED,
                source=session.session_id,
                room_id=room_id,
                data={
                    "player_id": session.player.id,
                    "username": session.player.username,
                    "session_id": session.session_id,
                    "room_id": room_id,
                    "old_room_id": old_room_id
                }
            ))

            # 이전 방의 다른 플레이어들에게 퇴장 알림. 계약의 증분 갱신 메시지다
            if old_room_id:
                await self.game_engine.broadcast_to_room(
                    old_room_id,
                    build_entity_leave(old_room_id, str(session.player.id)),
                    exclude_session=session.session_id,
                )

            # 새 방의 다른 플레이어들에게 입장 알림
            await self.game_engine.broadcast_to_room(
                room_id,
                build_entity_enter(room_id, serialize_player(session.player)),
                exclude_session=session.session_id,
            )

            # 따라가는 플레이어들도 함께 이동 - 현재 미구현
            # if not skip_followers:
            #     await self.handle_player_movement_with_followers(session, room_id, old_room_id)

            # 방 인원 변화는 위의 entity_enter / entity_leave 로 이미 알렸다.
            # 전체 목록을 다시 보내지 않는다

            # 방 정보를 플레이어에게 전송 (follower든 아니든 항상 전송)
            await self.send_room_info_to_player(session, room_id)

            # 플레이어 좌표 업데이트
            await self._update_player_coordinates(session, room_id)

            # 방 정보를 가져와서 좌표로 로그 표시
            try:
                room = await self.game_engine.world_manager.get_room(room_id)
                if room and hasattr(room, 'x') and hasattr(room, 'y'):
                    logger.info(f"플레이어 {session.player.username}이 ({room.x}, {room.y})로 이동")
                else:
                    logger.info(f"플레이어 {session.player.username}이 방 {room_id}로 이동")
            except Exception:
                logger.info(f"플레이어 {session.player.username}이 방 {room_id}로 이동")
            return True

            # 선공형 몬스터 체크 및 즉시 공격 처리
            # await self._check_aggressive_monsters_on_entry(session, room_id)

        except Exception as e:
            logger.error(f"플레이어 방 이동 실패 ({session.player.username} -> {room_id}): {e}")
            await session.send_message(
                build_event("movement.error", category="movement")
            )
            return False

    async def send_room_info_to_player(self, session: SessionType, room_id: str) -> None:
        """
        플레이어에게 방 정보를 전송합니다.

        Args:
            session: 플레이어 세션
            room_id: 방 ID
        """
        try:
            room_info = await self.game_engine.get_room_info(room_id)
            if room_info:
                room = room_info['room']
                exits = room_info.get('exits', {})

                # 좌표 기반 출구 계산은 room_connections 연결을 'enter' 키로 함께
                # 담는다. 계약은 방향 출구와 통로 유무를 분리하므로 나눠서 담는다.
                has_passage = 'enter' in exits
                directions = [d for d in exits if d != 'enter']

                nearby_rooms = []
                if room.x is not None and room.y is not None:
                    nearby_rooms = await self.game_engine.world_manager.get_rooms_in_area(
                        room.x, room.y, MINIMAP_RADIUS
                    )

                time_of_day = "day"
                if hasattr(self.game_engine, 'time_manager'):
                    time_of_day = self.game_engine.time_manager.get_current_time().value

                await session.send_message(
                    build_room_info(
                        room,
                        directions,
                        self._serialize_room_entities(session, room_info, room_id),
                        nearby_rooms,
                        time_of_day,
                        has_passage=has_passage,
                    )
                )

                logger.debug(f"방 정보 전송 완료: {session.player.username} -> 방 {room_id}")

        except Exception as e:
            logger.error(f"방 정보 전송 실패 ({session.player.username}, {room_id}): {e}")

    def _serialize_room_entities(
        self, session: SessionType, room_info: dict[str, Any], room_id: str
    ) -> list[dict[str, Any]]:
        """방 안의 몬스터, 오브젝트, 다른 플레이어를 엔티티 배열로 만든다.

        Args:
            session: 방 정보를 받는 세션. 우호도 판정의 관찰자다
            room_info: `get_location_summary` 결과
            room_id: 방 ID

        Returns:
            엔티티 페이로드 배열
        """
        viewer_faction = session.player.faction_id if session.player else None
        lua_loader = self.game_engine.dialogue_manager.lua_loader

        entities: list[dict[str, Any]] = [
            serialize_monster(
                monster,
                viewer_faction=viewer_faction,
                can_talk=lua_loader.has_dialogue_script(monster.id),
            )
            for monster in room_info.get('monsters', [])
        ]

        entities.extend(
            serialize_object(obj) for obj in room_info.get('objects', [])
        )

        # 같은 방의 다른 플레이어. 활력은 본인에게만 보이므로 제외한다.
        for other in self.game_engine.session_manager.get_authenticated_sessions():
            if (
                other.player
                and other.session_id != session.session_id
                and getattr(other, 'current_room_id', None) == room_id
            ):
                entities.append(serialize_player(other.player, include_vitals=False))

        return entities

    # `update_room_player_list()` 를 제거했다. 호출처가 없었고 계약 밖 타입
    # `room_players_update` 로 방 인원 전체를 매번 다시 보내는 방식이었다.
    # 계약은 증분 갱신(`entity_enter` / `entity_leave`)을 규정한다.

    async def handle_player_disconnect_cleanup(self, session: SessionType) -> None:
        """
        플레이어 연결 해제 시 따라가기 및 전투 관련 정리 작업

        Args:
            session: 연결 해제된 플레이어의 세션
        """
        if not session.player:
            return

        try:
            disconnected_player = session.player.username
            player_id = session.player.id

            # 전투 중이었다면 연결 해제 상태로 표시 (전투 유지)
            if getattr(session, 'in_combat', False):
                combat_id = getattr(session, 'combat_id', None)
                if combat_id:
                    # 전투 인스턴스 종료 대신 연결 해제 상태로 표시
                    self.game_engine.combat_manager.mark_player_disconnected(player_id)
                    logger.info(f"플레이어 {disconnected_player} 연결 해제 - 전투 {combat_id} 유지 (2분 타임아웃)")

                # 세션 전투 상태는 유지 (재접속 시 복구용)
                # session.in_combat = False  # 주석 처리 - 유지
                # session.combat_id = None   # 주석 처리 - 유지
                # session.original_room_id = None  # 주석 처리 - 유지

            # 이 플레이어를 따라가던 다른 플레이어들의 따라가기 해제
            for other_session in self.game_engine.session_manager.get_authenticated_sessions():
                if (other_session.player and
                    hasattr(other_session, 'following_player') and
                    other_session.following_player == disconnected_player):

                    # 따라가기 해제
                    delattr(other_session, 'following_player')

                    # 알림 전송
                    await other_session.send_message(
                        build_event(
                            "follow.stopped_disconnected",
                            {"username": disconnected_player},
                            category="social",
                        )
                    )

            logger.info(f"플레이어 연결 해제 정리 완료: {disconnected_player}")

        except Exception as e:
            logger.error(f"플레이어 연결 해제 정리 실패: {e}")

    async def _update_player_coordinates(self, session: SessionType, room_id: str) -> None:
        """
        플레이어의 좌표를 업데이트합니다.
        방 정보에서 좌표를 가져와 데이터베이스에 저장합니다.
        """
        try:
            room = await self.game_engine.world_manager.get_room(room_id)
            if not room or room.x is None or room.y is None:
                return

            session.player.last_room_x = room.x
            session.player.last_room_y = room.y

            from ...game.repositories import PlayerRepository
            from ...database import get_database_manager

            db_manager = await get_database_manager()
            player_repo = PlayerRepository(db_manager)
            await player_repo.update(session.player.id, {
                'last_room_x': room.x,
                'last_room_y': room.y,
            })
            logger.debug(f"플레이어 {session.player.username} 좌표 업데이트: ({room.x}, {room.y})")

        except Exception as e:
            logger.error(f"플레이어 좌표 업데이트 실패: {e}")

    # === 좌표 기반 이동 시스템 ===

    async def move_player_by_direction(self, session: SessionType, direction: str, skip_followers: bool = False) -> bool:
        """
        플레이어를 특정 방향으로 이동시킵니다 (좌표 기반).

        Args:
            session: 플레이어 세션
            direction: 이동 방향 (north, south, east, west 등)
            skip_followers: 따라가는 플레이어들 이동 생략 여부

        Returns:
            bool: 이동 성공 여부
        """
        if not session.is_authenticated or not session.player:
            return False

        # 스태미나 체크 (전투 밖 액션)
        if getattr(session, 'stamina', 5.0) < 1.0:
            await session.send_message(
                build_event("system.stamina_exhausted", category="movement")
            )
            return False

        try:
            # 현재 위치 확인
            current_room_id = getattr(session, 'current_room_id', None)
            if not current_room_id:
                await session.send_message(
                    build_event("movement.no_location", category="movement")
                )
                return False

            current_room = await self.game_engine.world_manager.get_room(current_room_id)
            if not current_room or current_room.x is None or current_room.y is None:
                await session.send_message(
                    build_event("movement.error", category="movement")
                )
                return False

            # 목적지 좌표 계산
            from ...utils.coordinate_utils import get_direction_from_string, calculate_new_coordinates

            direction_enum = get_direction_from_string(direction)
            if not direction_enum:
                await session.send_message(
                    build_event(
                        "go.invalid_direction",
                        {"direction": direction},
                        category="movement",
                    )
                )
                return False

            new_x, new_y = calculate_new_coordinates(current_room.x, current_room.y, direction_enum)

            # 막힌 출구 확인
            if hasattr(current_room, 'blocked_exits') and direction.lower() in (current_room.blocked_exits or []):
                await self._notify_no_exit(session, direction)
                return False

            # 목적지 방 확인
            target_room = await self.game_engine.world_manager.get_room_at_coordinates(new_x, new_y)
            if not target_room:
                await self._notify_no_exit(session, direction)
                return False

            # 이동 성공 알림은 보내지 않는다. 이어지는 room_info 가 이동을 알린다.

            # 스태미나 소모
            session.stamina = max(0.0, session.stamina - 1.0)

            # 기존 이동 메서드 사용
            return await self.move_player_to_room(session, target_room.id, skip_followers)

        except Exception as e:
            logger.error(f"방향 기반 이동 실패 ({session.player.username}, {direction}): {e}")
            await session.send_message(
                build_event("movement.error", category="movement")
            )
            return False

    async def _notify_no_exit(self, session: SessionType, direction: str) -> None:
        """해당 방향으로 갈 수 없음을 알린다."""
        await session.send_message(
            build_event(
                "movement.no_exit", {"direction": direction}, category="movement"
            )
        )

    async def move_player_to_coordinates(self, session: SessionType, x: int, y: int, skip_followers: bool = False) -> bool:
        """
        플레이어를 특정 좌표로 이동시킵니다.

        Args:
            session: 플레이어 세션
            x: 목적지 X 좌표
            y: 목적지 Y 좌표
            skip_followers: 따라가는 플레이어들 이동 생략 여부

        Returns:
            bool: 이동 성공 여부
        """
        if not session.is_authenticated or not session.player:
            return False

        try:
            # 목적지 방 확인
            target_room = await self.game_engine.world_manager.get_room_at_coordinates(x, y)
            if not target_room:
                await session.send_message(
                    build_event(
                        "movement.no_room_at",
                        {"x": x, "y": y},
                        category="movement",
                    )
                )
                return False

            # 기존 이동 메서드 사용
            return await self.move_player_to_room(session, target_room.id, skip_followers)

        except Exception as e:
            logger.error(f"좌표 기반 이동 실패 ({session.player.username}, {x}, {y}): {e}")
            await session.send_message(
                build_event("movement.error", category="movement")
            )
            return False