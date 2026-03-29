# -*- coding: utf-8 -*-
"""플레이어 이동 관리자"""

import logging
from typing import TYPE_CHECKING, Optional, Any
from datetime import datetime

from ..event_bus import Event, EventType
from ..types import SessionType

if TYPE_CHECKING:
    from ..game_engine import GameEngine
    from ...game.combat import CombatInstance

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
                await session.send_error("존재하지 않는 방입니다.")
                return False

            # 이전 방 ID 저장
            old_room_id = getattr(session, 'current_room_id', None)

            # 세션의 현재 방 업데이트
            session.current_room_id = room_id

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

            # 이전 방의 다른 플레이어들에게 퇴장 알림
            if old_room_id:
                leave_message = {
                    "type": "room_message",
                    "message": f"🚶 {session.player.get_display_name()}님이 떠났습니다.",
                    "timestamp": datetime.now().isoformat()
                }
                await self.game_engine.broadcast_to_room(old_room_id, leave_message, exclude_session=session.session_id)

            # 새 방의 다른 플레이어들에게 입장 알림
            enter_message = {
                "type": "room_message",
                "message": f"🚶 {session.player.get_display_name()}님이 도착했습니다.",
                "timestamp": datetime.now().isoformat()
            }
            await self.game_engine.broadcast_to_room(room_id, enter_message, exclude_session=session.session_id)

            # 따라가는 플레이어들도 함께 이동 - 현재 미구현
            # if not skip_followers:
            #     await self.handle_player_movement_with_followers(session, room_id, old_room_id)

            # 방 플레이어 목록 업데이트 (이전 방과 새 방 모두)
            if old_room_id:
                await self.update_room_player_list(old_room_id)
            await self.update_room_player_list(room_id)

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
            from ..localization import get_localization_manager
            localization = get_localization_manager()
            locale = session.player.preferred_locale if session.player else "en"
            message = localization.get_message("movement.error", locale)
            await session.send_error(message)
            return False

    async def send_room_info_to_player(self, session: SessionType, room_id: str) -> None:
        """
        플레이어에게 방 정보를 전송합니다.

        Args:
            session: 플레이어 세션
            room_id: 방 ID
        """
        try:
            locale = session.player.preferred_locale if session.player else "en"
            room_info = await self.game_engine.get_room_info(room_id, locale)
            if room_info:
                # 디버깅: 몬스터 정보 로깅
                monsters = room_info.get('monsters', [])
                logger.debug(f"방 {room_id}에서 {len(monsters)}마리 몬스터 발견")
                for i, monster in enumerate(monsters):
                    logger.debug(f"몬스터 {i+1}: {monster.get_localized_name(locale)}, 타입: {monster.monster_type}, 행동: {monster.behavior}")

                # 세션에 엔티티 번호 매핑 저장
                entity_map = {}
                entity_index = 1

                # 몬스터 번호 매핑 (1-9번)
                for monster in room_info.get('monsters', []):
                    if entity_index <= 9:  # 최대 9번까지
                        entity_map[entity_index] = {
                            'type': 'monster',
                            'id': monster.id,
                            'name': monster.get_localized_name(locale),
                            'entity': monster
                        }
                        entity_index += 1
                # TODO: 우후도 계산은 어떻게?

                # 아이템 번호 매핑 (11번부터 시작)
                item_index = 11
                # grouped_objects가 있으면 그것을 사용, 없으면 일반 objects 사용 WorldManager._group_stackable_objects 에서 생성
                grouped_objects = room_info.get('grouped_objects', [])
                logger.info(f"grouped_objects[{grouped_objects}]")
                if grouped_objects:
                    for group in grouped_objects:
                        # 그룹의 첫 번째 객체 ID를 사용
                        first_obj = group.get('objects', [])[0] if group.get('objects') else None
                        if first_obj:
                            entity_map[item_index] = {
                                'type': 'object',
                                'id': first_obj.id,
                                'name': group.get('display_name_ko' if locale == 'ko' else 'display_name_en', ''),
                                'entity': first_obj,
                                'group': group  # 그룹 정보도 저장
                            }
                            item_index += 1
                else:
                    for obj in room_info.get('objects', []):
                        entity_map[item_index] = {
                            'type': 'object',
                            'id': obj.id,
                            'name': obj.get_localized_name(locale),
                            'entity': obj
                        }
                        item_index += 1

                # 세션에 저장
                session.room_entity_map = entity_map
                # 세션이 전투중이면 combatInst 에 entity_map 저장
                if session.in_combat:
                    combat_inst: CombatInstance = self.game_engine.combat_manager.get_combat(session.combat_id)
                    combat_inst.set_entity_map(entity_map)

                # 디버깅: entity_map 로깅
                logger.debug(f"entity_map created: {entity_map}")
                for num, info in entity_map.items():
                    logger.info(f"entity_map {num}: {info['type']} - {info['name']} (ID: {info['id'][-12:]})")

                room_data = {
                    "id": room_info['room'].id,
                    "description": room_info['room'].get_localized_description(locale),
                    "exits": room_info['exits'],
                    "objects": [
                        {
                            "id": obj.id,
                            "name": obj.get_localized_name(locale),
                            "type": "item"  # object_type 제거됨, 기본값 사용
                        }
                        for obj in room_info['objects']
                    ],
                    "grouped_objects": room_info.get('grouped_objects', []),  # 그룹화된 오브젝트 추가
                    "monsters": [
                        {
                            "id": monster.id,
                            "name": monster.get_localized_name(locale),
                            "current_hp": monster.current_hp,
                            "max_hp": monster.max_hp,
                            "faction_id": monster.faction_id,
                            "monster_type": monster.monster_type.value if hasattr(monster.monster_type, 'value') else str(monster.monster_type),
                            "behavior": monster.behavior.value if hasattr(monster.behavior, 'value') else str(monster.behavior),
                            "is_aggressive": monster.is_aggressive(),
                            "is_passive": monster.is_passive(),
                            "is_neutral": monster.is_neutral()
                        }
                        for monster in room_info.get('monsters', [])
                    # ],
                    # "npcs": [
                    #     {
                    #         "id": npc.id,
                    #         "name": npc.get_localized_name(locale),
                    #         "description": npc.get_localized_description(locale),
                    #         "npc_type": npc.npc_type,
                    #         "is_merchant": npc.is_merchant()
                    #     }
                    #     for npc in room_info.get('npcs', [])
                    ]
                }

                await session.send_message({
                    "type": "room_info",
                    "room": room_data,
                    "entity_map": entity_map
                })

                # UI 업데이트 정보 전송
                # await self.game_engine.ui_manager.send_ui_update(session, room_info)

                logger.debug(f"방 정보 전송 완료: {session.player.username} -> 방 {room_id}")

        except Exception as e:
            logger.error(f"방 정보 전송 실패 ({session.player.username}, {room_id}): {e}")

    async def update_room_player_list(self, room_id: str) -> None:
        """
        방의 플레이어 목록을 실시간으로 업데이트합니다.

        Args:
            room_id: 업데이트할 방 ID
        """
        try:
            # 방에 있는 모든 플레이어들 찾기
            players_in_room = []
            for session in self.game_engine.session_manager.get_authenticated_sessions():
                if (session.player and
                    getattr(session, 'current_room_id', None) == room_id):

                    player_info = {
                        "id": session.player.id,
                        "name": session.player.username,
                        "session_id": session.session_id,
                        "following": getattr(session, 'following_player', None)
                    }
                    players_in_room.append(player_info)

            # 방에 있는 모든 플레이어들에게 업데이트된 목록 전송
            update_message = {
                "type": "room_players_update",
                "room_id": room_id,
                "players": players_in_room,
                "player_count": len(players_in_room)
            }

            await self.game_engine.broadcast_to_room(room_id, update_message)
            logger.debug(f"방 {room_id} 플레이어 목록 업데이트: {len(players_in_room)}명")

        except Exception as e:
            logger.error(f"방 플레이어 목록 업데이트 실패 ({room_id}): {e}")

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
                    await other_session.send_message({
                        "type": "follow_stopped",
                        "message": f"👥 {disconnected_player}님이 연결을 해제하여 따라가기가 중지되었습니다.",
                        "reason": "player_disconnected"
                    })

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
            from ..localization import get_localization_manager
            localization = get_localization_manager()
            locale = session.player.preferred_locale if session.player else "en"
            await session.send_error(localization.get_message("system.stamina_exhausted", locale))
            return False

        try:
            # 현재 위치 확인
            current_room_id = getattr(session, 'current_room_id', None)
            if not current_room_id:
                await session.send_error("현재 위치를 확인할 수 없습니다.")
                return False

            current_room = await self.game_engine.world_manager.get_room(current_room_id)
            if not current_room or current_room.x is None or current_room.y is None:
                await session.send_error("현재 방의 좌표 정보가 없습니다.")
                return False

            # 목적지 좌표 계산
            from ...utils.coordinate_utils import get_direction_from_string, calculate_new_coordinates

            direction_enum = get_direction_from_string(direction)
            if not direction_enum:
                from ..localization import get_localization_manager
                localization = get_localization_manager()
                locale = session.player.preferred_locale if session.player else "en"
                message = localization.get_message("go.invalid_direction", locale, direction=direction)
                await session.send_error(message)
                return False

            new_x, new_y = calculate_new_coordinates(current_room.x, current_room.y, direction_enum)

            # 막힌 출구 확인
            if hasattr(current_room, 'blocked_exits') and direction.lower() in (current_room.blocked_exits or []):
                from ..localization import get_localization_manager
                localization = get_localization_manager()
                locale = session.player.preferred_locale if session.player else "en"
                message = localization.get_message("movement.no_exit", locale, direction=direction)
                await session.send_error(message)
                return False

            # 목적지 방 확인
            target_room = await self.game_engine.world_manager.get_room_at_coordinates(new_x, new_y)
            if not target_room:
                from ..localization import get_localization_manager
                localization = get_localization_manager()
                locale = session.player.preferred_locale if session.player else "en"
                message = localization.get_message("movement.no_exit", locale, direction=direction)
                await session.send_error(message)
                return False

            # 이동 성공 메시지를 먼저 전송
            from ..localization import get_localization_manager
            localization = get_localization_manager()
            locale = session.player.preferred_locale if session.player else "en"
            move_message = localization.get_message("movement.success", locale, direction=direction)
            await session.send_success(move_message)

            # 스태미나 소모
            session.stamina = max(0.0, session.stamina - 1.0)

            # 기존 이동 메서드 사용
            return await self.move_player_to_room(session, target_room.id, skip_followers)

        except Exception as e:
            logger.error(f"방향 기반 이동 실패 ({session.player.username}, {direction}): {e}")
            from ..localization import get_localization_manager
            localization = get_localization_manager()
            locale = session.player.preferred_locale if session.player else "en"
            message = localization.get_message("movement.error", locale)
            await session.send_error(message)
            return False

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
                await session.send_error(f"좌표 ({x}, {y})에 방이 없습니다.")
                return False

            # 기존 이동 메서드 사용
            return await self.move_player_to_room(session, target_room.id, skip_followers)

        except Exception as e:
            logger.error(f"좌표 기반 이동 실패 ({session.player.username}, {x}, {y}): {e}")
            from ..localization import get_localization_manager
            localization = get_localization_manager()
            locale = session.player.preferred_locale if session.player else "en"
            message = localization.get_message("movement.error", locale)
            await session.send_error(message)
            return False