# -*- coding: utf-8 -*-
"""관리자 기능 관리자"""

import logging
from typing import TYPE_CHECKING, Dict, Any
from datetime import datetime

from ..event_bus import Event, EventType
from ..types import SessionType

if TYPE_CHECKING:
    from ..game_engine import GameEngine

logger = logging.getLogger(__name__)


class AdminManager:
    """관리자 기능을 담당하는 매니저"""

    def __init__(self, game_engine: 'GameEngine'):
        self.game_engine = game_engine

    async def create_room_realtime(self, room_data: Dict[str, Any], admin_session: SessionType) -> bool:
        """
        실시간으로 새로운 방을 생성합니다.

        Args:
            room_data: 방 생성 데이터
            admin_session: 관리자 세션

        Returns:
            bool: 생성 성공 여부
        """
        try:
            # 방 생성
            new_room = await self.game_engine.world_manager.create_room(room_data)

            # 관리자에게 성공 알림
            await admin_session.send_success(
                f"새 방이 생성되었습니다: {new_room.get_localized_name('ko')} (ID: {new_room.id})"
            )

            # 세계 변경 이벤트 발행
            await self.game_engine.event_bus.publish(Event(
                event_type=EventType.WORLD_UPDATED,
                source=admin_session.session_id,
                data={
                    "action": "room_created",
                    "room_id": new_room.id,
                    "admin_id": admin_session.player.id if admin_session.player else None
                }
            ))

            logger.info(f"실시간 방 생성: {new_room.id} (관리자: {admin_session.player.username if admin_session.player else 'Unknown'})")
            return True

        except Exception as e:
            logger.error(f"실시간 방 생성 실패: {e}")
            await admin_session.send_error(f"방 생성 실패: {str(e)}")
            return False

    async def update_room_realtime(self, room_id: str, updates: Dict[str, Any], admin_session: SessionType) -> bool:
        """
        실시간으로 방 정보를 수정합니다.

        Args:
            room_id: 수정할 방 ID
            updates: 수정 데이터
            admin_session: 관리자 세션

        Returns:
            bool: 수정 성공 여부
        """
        try:
            # 방 수정
            updated_room = await self.game_engine.world_manager.update_room(room_id, updates)
            if not updated_room:
                await admin_session.send_error("존재하지 않는 방입니다.")
                return False

            # 관리자에게 성공 알림
            await admin_session.send_success(
                f"방이 수정되었습니다: {updated_room.get_localized_name('ko')} (ID: {room_id})"
            )

            # 해당 방에 있는 모든 플레이어에게 변경사항 알림
            await self.game_engine.broadcast_to_room(room_id, {
                "type": "room_updated",
                "message": "방 정보가 업데이트되었습니다.",
                "room": {
                    "id": updated_room.id,
                    "name": updated_room.name,
                    "description": updated_room.description,
                    "exits": updated_room.exits
                }
            })

            # 세계 변경 이벤트 발행
            await self.game_engine.event_bus.publish(Event(
                event_type=EventType.WORLD_UPDATED,
                source=admin_session.session_id,
                data={
                    "action": "room_updated",
                    "room_id": room_id,
                    "updates": updates,
                    "admin_id": admin_session.player.id if admin_session.player else None
                }
            ))

            logger.info(f"실시간 방 수정: {room_id} (관리자: {admin_session.player.username if admin_session.player else 'Unknown'})")
            return True

        except Exception as e:
            logger.error(f"실시간 방 수정 실패 ({room_id}): {e}")
            await admin_session.send_error(f"방 수정 실패: {str(e)}")
            return False

    async def create_object_realtime(self, object_data: Dict[str, Any], admin_session: SessionType) -> bool:
        """
        실시간으로 새로운 게임 객체를 생성합니다.

        Args:
            object_data: 객체 생성 데이터
            admin_session: 관리자 세션

        Returns:
            bool: 생성 성공 여부
        """
        try:
            # 객체 생성
            new_object = await self.game_engine.world_manager.create_game_object(object_data)

            # 관리자에게 성공 알림
            await admin_session.send_success(
                f"새 객체가 생성되었습니다: {new_object.get_localized_name('ko')} (ID: {new_object.id})"
            )

            # 객체가 생성된 방에 있는 플레이어들에게 알림
            if new_object.location_type == "room" and new_object.location_id:
                await self.game_engine.broadcast_to_room(new_object.location_id, {
                    "type": "object_created",
                    "message": f"새로운 객체가 나타났습니다: {new_object.get_localized_name('ko')}",
                    "object": {
                        "id": new_object.id,
                        "name": new_object.name,
                        "type": new_object.object_type
                    }
                })

            # 세계 변경 이벤트 발행
            await self.game_engine.event_bus.publish(Event(
                event_type=EventType.WORLD_UPDATED,
                source=admin_session.session_id,
                data={
                    "action": "object_created",
                    "object_id": new_object.id,
                    "location_id": new_object.location_id,
                    "admin_id": admin_session.player.id if admin_session.player else None
                }
            ))

            logger.info(f"실시간 객체 생성: {new_object.id} (관리자: {admin_session.player.username if admin_session.player else 'Unknown'})")
            return True

        except Exception as e:
            logger.error(f"실시간 객체 생성 실패: {e}")
            await admin_session.send_error(f"객체 생성 실패: {str(e)}")
            return False

    async def validate_and_repair_world(self, admin_session: SessionType = None) -> Dict[str, Any]:
        """
        게임 세계의 무결성을 검증하고 자동으로 수정합니다.

        Args:
            admin_session: 관리자 세션 (결과 알림용, 선택사항)

        Returns:
            Dict: 검증 및 수정 결과
        """
        try:
            # 무결성 검증
            issues = await self.game_engine.world_manager.validate_world_integrity()

            # 문제가 있는 경우 자동 수정
            repair_result = {}
            if any(issues.values()):
                repair_result = await self.game_engine.world_manager.repair_world_integrity()

            result = {
                "validation": issues,
                "repair": repair_result,
                "timestamp": datetime.now().isoformat()
            }

            # 관리자에게 결과 알림
            if admin_session:
                total_issues = sum(len(issue_list) for issue_list in issues.values())
                total_fixed = sum(repair_result.values())

                if total_issues == 0:
                    await admin_session.send_success("게임 세계 무결성 검증 완료: 문제 없음")
                else:
                    await admin_session.send_success(
                        f"게임 세계 무결성 검증 및 수정 완료: {total_issues}개 문제 발견, {total_fixed}개 수정"
                    )

            logger.info(f"게임 세계 무결성 검증 및 수정 완료: {result}")
            return result

        except Exception as e:
            logger.error(f"게임 세계 무결성 검증 실패: {e}")
            if admin_session:
                await admin_session.send_error(f"무결성 검증 실패: {str(e)}")
            raise

    async def kick_player(self, target_username: str, admin_session: SessionType, reason: str = "관리자에 의해 추방") -> bool:
        """
        플레이어를 서버에서 추방합니다.

        Args:
            target_username: 추방할 플레이어 이름
            admin_session: 관리자 세션
            reason: 추방 이유

        Returns:
            bool: 추방 성공 여부
        """
        try:
            # 대상 플레이어 세션 찾기
            target_session = None
            for session in self.game_engine.session_manager.get_authenticated_sessions():
                if session.player and session.player.username == target_username:
                    target_session = session
                    break

            if not target_session:
                await admin_session.send_error(f"플레이어 '{target_username}'을(를) 찾을 수 없습니다.")
                return False

            # 추방 알림 전송
            await target_session.send_message({
                "type": "kicked",
                "message": f"관리자에 의해 서버에서 추방되었습니다. 사유: {reason}",
                "reason": reason,
                "admin": admin_session.player.username if admin_session.player else "시스템"
            })

            # 다른 플레이어들에게 알림
            kick_message = {
                "type": "system_message",
                "message": f"🚫 {target_username}님이 관리자에 의해 추방되었습니다.",
                "timestamp": datetime.now().isoformat()
            }
            await self.game_engine.broadcast_to_all(kick_message)

            # 세션 강제 종료
            await self.game_engine.remove_player_session(target_session, f"관리자 추방: {reason}")

            # 관리자에게 성공 알림
            await admin_session.send_success(f"플레이어 '{target_username}'을(를) 추방했습니다.")

            logger.info(f"플레이어 추방: {target_username} (관리자: {admin_session.player.username if admin_session.player else 'Unknown'}, 사유: {reason})")
            return True

        except Exception as e:
            logger.error(f"플레이어 추방 실패 ({target_username}): {e}")
            await admin_session.send_error(f"플레이어 추방 실패: {str(e)}")
            return False

    async def get_admin_stats(self, admin_session: SessionType) -> Dict[str, Any]:
        """
        관리자용 서버 통계 정보를 반환합니다.

        Args:
            admin_session: 관리자 세션

        Returns:
            Dict: 서버 통계 정보
        """
        try:
            # 기본 게임 엔진 통계
            engine_stats = self.game_engine.get_stats()

            # 추가 관리자 통계
            authenticated_sessions = self.game_engine.session_manager.get_authenticated_sessions()

            player_stats = {
                "total_online": len(authenticated_sessions),
                "players": [
                    {
                        "username": session.player.username,
                        "session_id": session.session_id,
                        "current_room": getattr(session, 'current_room_id', None),
                        "ip_address": session.ip_address,
                        "connected_at": session.connected_at.isoformat() if hasattr(session, 'connected_at') else None
                    }
                    for session in authenticated_sessions
                    if session.player
                ]
            }

            # 방 통계
            room_stats = await self._get_room_statistics()

            # 객체 통계
            object_stats = await self._get_object_statistics()

            admin_stats = {
                "engine": engine_stats,
                "players": player_stats,
                "rooms": room_stats,
                "objects": object_stats,
                "timestamp": datetime.now().isoformat()
            }

            return admin_stats

        except Exception as e:
            logger.error(f"관리자 통계 조회 실패: {e}")
            await admin_session.send_error(f"통계 조회 실패: {str(e)}")
            return {}

    async def _get_room_statistics(self) -> Dict[str, Any]:
        """방 통계 정보 조회"""
        try:
            # 모든 방 조회 (간단한 통계만)
            rooms = await self.game_engine.world_manager._room_repo.get_all()

            return {
                "total_rooms": len(rooms),
                "rooms_with_players": len([
                    room for room in rooms
                    if any(
                        getattr(session, 'current_room_id', None) == room.id
                        for session in self.game_engine.session_manager.get_authenticated_sessions()
                    )
                ])
            }
        except Exception as e:
            logger.error(f"방 통계 조회 실패: {e}")
            return {"total_rooms": 0, "rooms_with_players": 0}

    async def _get_object_statistics(self) -> Dict[str, Any]:
        """객체 통계 정보 조회"""
        try:
            # 모든 객체 조회 (간단한 통계만)
            objects = await self.game_engine.world_manager._object_repo.get_all()

            object_types: Dict[str, int] = {}
            for obj in objects:
                obj_type = getattr(obj, 'object_type', 'unknown')
                object_types[obj_type] = object_types.get(obj_type, 0) + 1

            return {
                "total_objects": len(objects),
                "by_type": object_types
            }
        except Exception as e:
            logger.error(f"객체 통계 조회 실패: {e}")
            return {"total_objects": 0, "by_type": {}}