# -*- coding: utf-8 -*-
"""게임 엔진 코어 클래스"""

import asyncio
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime

from .event_bus import EventBus, Event, EventType, get_event_bus
from ..server.session import SessionManager, Session
from ..game.managers import PlayerManager, WorldManager
from ..game.models import Player
from ..game.repositories import RoomRepository, GameObjectRepository
from ..database.connection import DatabaseManager
from ..commands import CommandProcessor, SayCommand, TellCommand, WhoCommand, LookCommand, HelpCommand, QuitCommand

logger = logging.getLogger(__name__)


class GameEngine:
    """MUD 게임의 핵심 엔진 클래스"""

    def __init__(self,
                 session_manager: SessionManager,
                 player_manager: PlayerManager,
                 db_manager: DatabaseManager,
                 event_bus: Optional[EventBus] = None):
        """
        GameEngine 초기화

        Args:
            session_manager: 세션 관리자
            player_manager: 플레이어 관리자
            db_manager: 데이터베이스 관리자
            event_bus: 이벤트 버스 (None이면 전역 인스턴스 사용)
        """
        self.session_manager = session_manager
        self.player_manager = player_manager
        self.db_manager = db_manager
        self.event_bus = event_bus or get_event_bus()

        # WorldManager 초기화
        room_repo = RoomRepository(db_manager)
        object_repo = GameObjectRepository(db_manager)
        self.world_manager = WorldManager(room_repo, object_repo)

        self._running = False
        self._start_time: Optional[datetime] = None

        # 명령어 처리기 초기화
        self.command_processor = CommandProcessor(self.event_bus)
        self._setup_commands()

        # 이벤트 구독 설정
        self._setup_event_subscriptions()

        logger.info("GameEngine 초기화 완료 (WorldManager 포함)")

    def _setup_commands(self) -> None:
        """기본 명령어들 설정"""
        # 기본 명령어들 등록
        self.command_processor.register_command(SayCommand())
        self.command_processor.register_command(TellCommand())
        self.command_processor.register_command(WhoCommand(self.session_manager))
        self.command_processor.register_command(LookCommand())
        self.command_processor.register_command(QuitCommand())

        # HelpCommand는 command_processor 참조가 필요
        help_command = HelpCommand(self.command_processor)
        self.command_processor.register_command(help_command)

        logger.info("기본 명령어 등록 완료")

    def _setup_event_subscriptions(self) -> None:
        """이벤트 구독 설정"""
        # 플레이어 관련 이벤트 구독
        self.event_bus.subscribe(EventType.PLAYER_CONNECTED, self._on_player_connected)
        self.event_bus.subscribe(EventType.PLAYER_DISCONNECTED, self._on_player_disconnected)
        self.event_bus.subscribe(EventType.PLAYER_LOGIN, self._on_player_login)
        self.event_bus.subscribe(EventType.PLAYER_LOGOUT, self._on_player_logout)
        self.event_bus.subscribe(EventType.PLAYER_COMMAND, self._on_player_command)

        # 방 관련 이벤트 구독
        self.event_bus.subscribe(EventType.ROOM_ENTERED, self._on_room_entered)
        self.event_bus.subscribe(EventType.ROOM_LEFT, self._on_room_left)
        self.event_bus.subscribe(EventType.ROOM_MESSAGE, self._on_room_message)

        # 시스템 이벤트 구독
        self.event_bus.subscribe(EventType.SERVER_STARTED, self._on_server_started)
        self.event_bus.subscribe(EventType.SERVER_STOPPING, self._on_server_stopping)

        logger.info("이벤트 구독 설정 완료")

    async def start(self) -> None:
        """게임 엔진 시작"""
        if self._running:
            logger.warning("GameEngine이 이미 실행 중입니다")
            return

        logger.info("GameEngine 시작 중...")

        # 이벤트 버스 시작
        if not self.event_bus._running:
            await self.event_bus.start()

        self._running = True
        self._start_time = datetime.now()

        logger.info("GameEngine 시작 완료")

    async def stop(self) -> None:
        """게임 엔진 중지"""
        if not self._running:
            return

        logger.info("GameEngine 중지 중...")

        self._running = False

        # 모든 활성 세션에 종료 알림
        await self._notify_all_players_shutdown()

        logger.info("GameEngine 중지 완료")

    async def add_player_session(self, session: Session, player: Player) -> None:
        """
        플레이어 세션 추가

        Args:
            session: 세션 객체
            player: 플레이어 객체
        """
        # 플레이어 연결 이벤트 발행
        await self.event_bus.publish(Event(
            event_type=EventType.PLAYER_CONNECTED,
            source=session.session_id,
            data={
                "player_id": player.id,
                "username": player.username,
                "session_id": session.session_id,
                "ip_address": session.ip_address
            }
        ))

        # 플레이어 로그인 이벤트 발행
        await self.event_bus.publish(Event(
            event_type=EventType.PLAYER_LOGIN,
            source=session.session_id,
            data={
                "player_id": player.id,
                "username": player.username,
                "session_id": session.session_id
            }
        ))

    async def remove_player_session(self, session: Session, reason: str = "연결 종료") -> None:
        """
        플레이어 세션 제거

        Args:
            session: 세션 객체
            reason: 제거 이유
        """
        if session.player:
            # 플레이어 로그아웃 이벤트 발행
            await self.event_bus.publish(Event(
                event_type=EventType.PLAYER_LOGOUT,
                source=session.session_id,
                data={
                    "player_id": session.player.id,
                    "username": session.player.username,
                    "session_id": session.session_id,
                    "reason": reason
                }
            ))

        # 플레이어 연결 해제 이벤트 발행
        await self.event_bus.publish(Event(
            event_type=EventType.PLAYER_DISCONNECTED,
            source=session.session_id,
            data={
                "session_id": session.session_id,
                "reason": reason,
                "player_id": session.player.id if session.player else None,
                "username": session.player.username if session.player else None
            }
        ))

    async def broadcast_to_room(self, room_id: str, message: Dict[str, Any],
                               exclude_session: Optional[str] = None) -> int:
        """
        특정 방의 모든 플레이어에게 메시지 브로드캐스트

        Args:
            room_id: 방 ID
            message: 브로드캐스트할 메시지
            exclude_session: 제외할 세션 ID (선택사항)

        Returns:
            int: 메시지를 받은 플레이어 수
        """
        # 방 브로드캐스트 이벤트 발행
        await self.event_bus.publish(Event(
            event_type=EventType.ROOM_BROADCAST,
            source="game_engine",
            room_id=room_id,
            data={
                "message": message,
                "exclude_session": exclude_session,
                "room_id": room_id
            }
        ))

        # 실제 브로드캐스트 수행
        count = 0
        for session in self.session_manager.get_authenticated_sessions().values():
            if session.player and session.session_id != exclude_session:
                # TODO: 플레이어가 해당 방에 있는지 확인하는 로직 필요
                # 현재는 모든 인증된 세션에 전송
                if await session.send_message(message):
                    count += 1

        return count

    async def broadcast_to_all(self, message: Dict[str, Any],
                              authenticated_only: bool = True) -> int:
        """
        모든 플레이어에게 메시지 브로드캐스트

        Args:
            message: 브로드캐스트할 메시지
            authenticated_only: 인증된 세션에만 전송할지 여부

        Returns:
            int: 메시지를 받은 플레이어 수
        """
        return await self.session_manager.broadcast_to_all(message, authenticated_only)

    async def handle_player_command(self, session: Session, command: str) -> None:
        """
        플레이어 명령어 처리

        Args:
            session: 세션 객체
            command: 명령어
        """
        if not session.is_authenticated or not session.player:
            await session.send_error("인증되지 않은 사용자입니다.")
            return

        # 명령어 처리기를 통해 명령어 실행
        result = await self.command_processor.process_command(session, command)

        # 결과를 세션에 전송
        await self._send_command_result(session, result)

    async def _send_command_result(self, session: Session, result) -> None:
        """
        명령어 실행 결과를 세션에 전송

        Args:
            session: 세션 객체
            result: 명령어 실행 결과
        """
        from ..commands.base import CommandResultType

        # 기본 메시지 전송
        if result.result_type == CommandResultType.SUCCESS:
            await session.send_success(result.message, result.data)
        elif result.result_type == CommandResultType.ERROR:
            await session.send_error(result.message)
        else:
            await session.send_message({
                "response": result.message,
                "type": result.result_type.value,
                **result.data
            })

        # 브로드캐스트 처리
        if result.broadcast and result.broadcast_message:
            if result.room_only:
                # 같은 방에만 브로드캐스트 (현재는 전체 브로드캐스트로 구현)
                await self.broadcast_to_all({
                    "type": "room_message",
                    "message": result.broadcast_message,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                # 전체 브로드캐스트
                await self.broadcast_to_all({
                    "type": "broadcast_message",
                    "message": result.broadcast_message,
                    "timestamp": datetime.now().isoformat()
                })

        # 특별한 액션 처리
        if result.data.get("disconnect"):
            # quit 명령어 등으로 연결 종료 요청
            await self.remove_player_session(session, "플레이어 요청으로 종료")

    # 이벤트 핸들러들
    async def _on_player_connected(self, event: Event) -> None:
        """플레이어 연결 이벤트 핸들러"""
        data = event.data
        logger.info(f"플레이어 연결: {data.get('username')} (세션: {data.get('session_id')})")

    async def _on_player_disconnected(self, event: Event) -> None:
        """플레이어 연결 해제 이벤트 핸들러"""
        data = event.data
        username = data.get('username', '알 수 없음')
        reason = data.get('reason', '알 수 없는 이유')
        logger.info(f"플레이어 연결 해제: {username} (이유: {reason})")

    async def _on_player_login(self, event: Event) -> None:
        """플레이어 로그인 이벤트 핸들러"""
        data = event.data
        username = data.get('username')

        # 다른 플레이어들에게 로그인 알림
        login_message = {
            "type": "system_message",
            "message": f"🎮 {username}님이 게임에 참여했습니다.",
            "timestamp": event.timestamp.isoformat()
        }

        await self.broadcast_to_all(login_message)
        logger.info(f"플레이어 로그인 알림 브로드캐스트: {username}")

    async def _on_player_logout(self, event: Event) -> None:
        """플레이어 로그아웃 이벤트 핸들러"""
        data = event.data
        username = data.get('username')

        # 다른 플레이어들에게 로그아웃 알림
        logout_message = {
            "type": "system_message",
            "message": f"👋 {username}님이 게임을 떠났습니다.",
            "timestamp": event.timestamp.isoformat()
        }

        await self.broadcast_to_all(logout_message)
        logger.info(f"플레이어 로그아웃 알림 브로드캐스트: {username}")

    async def _on_player_command(self, event: Event) -> None:
        """플레이어 명령어 이벤트 핸들러"""
        data = event.data
        username = data.get('username')
        command = data.get('command')
        logger.debug(f"플레이어 명령어: {username} -> {command}")

    async def _on_room_entered(self, event: Event) -> None:
        """방 입장 이벤트 핸들러"""
        data = event.data
        username = data.get('username')
        room_id = event.room_id
        logger.info(f"방 입장: {username} -> 방 {room_id}")

    async def _on_room_left(self, event: Event) -> None:
        """방 퇴장 이벤트 핸들러"""
        data = event.data
        username = data.get('username')
        room_id = event.room_id
        logger.info(f"방 퇴장: {username} <- 방 {room_id}")

    async def _on_room_message(self, event: Event) -> None:
        """방 메시지 이벤트 핸들러"""
        data = event.data
        username = data.get('username')
        message = data.get('message')
        room_id = event.room_id
        logger.debug(f"방 메시지: {username} (방 {room_id}) -> {message}")

    async def _on_server_started(self, event: Event) -> None:
        """서버 시작 이벤트 핸들러"""
        logger.info("서버 시작 이벤트 수신")

    async def _on_server_stopping(self, event: Event) -> None:
        """서버 중지 이벤트 핸들러"""
        logger.info("서버 중지 이벤트 수신")

    async def _notify_all_players_shutdown(self) -> None:
        """모든 플레이어에게 서버 종료 알림"""
        shutdown_message = {
            "type": "system_message",
            "message": "🛑 서버가 곧 종료됩니다. 연결이 끊어집니다.",
            "timestamp": datetime.now().isoformat()
        }

        count = await self.broadcast_to_all(shutdown_message)
        logger.info(f"서버 종료 알림 전송: {count}명의 플레이어")

    def get_stats(self) -> Dict[str, Any]:
        """
        게임 엔진 통계 정보 반환

        Returns:
            Dict: 통계 정보
        """
        uptime = None
        if self._start_time:
            uptime = (datetime.now() - self._start_time).total_seconds()

        return {
            "running": self._running,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "uptime_seconds": uptime,
            "session_stats": self.session_manager.get_stats(),
            "event_bus_stats": self.event_bus.get_stats()
        }

    def is_running(self) -> bool:
        """게임 엔진 실행 상태 반환"""
        return self._running

    # === WorldManager 통합 메서드들 ===

    async def get_room_info(self, room_id: str, locale: str = 'en') -> Optional[Dict[str, Any]]:
        """
        방 정보를 조회합니다.

        Args:
            room_id: 방 ID
            locale: 언어 설정

        Returns:
            Dict: 방 정보 (방, 객체, 출구 포함)
        """
        try:
            location_summary = await self.world_manager.get_location_summary(room_id, locale)
            return location_summary
        except Exception as e:
            logger.error(f"방 정보 조회 실패 ({room_id}): {e}")
            return None

    async def move_player_to_room(self, session: Session, room_id: str) -> bool:
        """
        플레이어를 특정 방으로 이동시킵니다.

        Args:
            session: 플레이어 세션
            room_id: 목적지 방 ID

        Returns:
            bool: 이동 성공 여부
        """
        if not session.is_authenticated or not session.player:
            return False

        try:
            # 방이 존재하는지 확인
            room = await self.world_manager.get_room(room_id)
            if not room:
                await session.send_error("존재하지 않는 방입니다.")
                return False

            # 이전 방 ID 저장
            old_room_id = getattr(session, 'current_room_id', None)

            # 세션의 현재 방 업데이트
            session.current_room_id = room_id

            # 방 퇴장 이벤트 발행 (이전 방이 있는 경우)
            if old_room_id:
                await self.event_bus.publish(Event(
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
            await self.event_bus.publish(Event(
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

            # 방 정보를 플레이어에게 전송
            room_info = await self.get_room_info(room_id, session.locale)
            if room_info:
                await session.send_message({
                    "type": "room_info",
                    "room": {
                        "id": room_info['room'].id,
                        "name": room_info['room'].get_localized_name(session.locale),
                        "description": room_info['room'].get_localized_description(session.locale),
                        "exits": room_info['exits'],
                        "objects": [
                            {
                                "id": obj.id,
                                "name": obj.get_localized_name(session.locale),
                                "type": obj.object_type
                            }
                            for obj in room_info['objects']
                        ]
                    }
                })

            logger.info(f"플레이어 {session.player.username}이 방 {room_id}로 이동")
            return True

        except Exception as e:
            logger.error(f"플레이어 방 이동 실패 ({session.player.username} -> {room_id}): {e}")
            await session.send_error("방 이동 중 오류가 발생했습니다.")
            return False

    async def create_room_realtime(self, room_data: Dict[str, Any], admin_session: Session) -> bool:
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
            new_room = await self.world_manager.create_room(room_data)

            # 관리자에게 성공 알림
            await admin_session.send_success(
                f"새 방이 생성되었습니다: {new_room.get_localized_name('ko')} (ID: {new_room.id})"
            )

            # 세계 변경 이벤트 발행
            await self.event_bus.publish(Event(
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

    async def update_room_realtime(self, room_id: str, updates: Dict[str, Any], admin_session: Session) -> bool:
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
            updated_room = await self.world_manager.update_room(room_id, updates)
            if not updated_room:
                await admin_session.send_error("존재하지 않는 방입니다.")
                return False

            # 관리자에게 성공 알림
            await admin_session.send_success(
                f"방이 수정되었습니다: {updated_room.get_localized_name('ko')} (ID: {room_id})"
            )

            # 해당 방에 있는 모든 플레이어에게 변경사항 알림
            await self.broadcast_to_room(room_id, {
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
            await self.event_bus.publish(Event(
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

    async def create_object_realtime(self, object_data: Dict[str, Any], admin_session: Session) -> bool:
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
            new_object = await self.world_manager.create_game_object(object_data)

            # 관리자에게 성공 알림
            await admin_session.send_success(
                f"새 객체가 생성되었습니다: {new_object.get_localized_name('ko')} (ID: {new_object.id})"
            )

            # 객체가 방에 배치된 경우 해당 방의 플레이어들에게 알림
            if new_object.location_type == 'room' and new_object.location_id:
                await self.broadcast_to_room(new_object.location_id, {
                    "type": "object_appeared",
                    "message": f"새로운 객체가 나타났습니다: {new_object.get_localized_name('ko')}",
                    "object": {
                        "id": new_object.id,
                        "name": new_object.name,
                        "type": new_object.object_type
                    }
                })

            # 세계 변경 이벤트 발행
            await self.event_bus.publish(Event(
                event_type=EventType.WORLD_UPDATED,
                source=admin_session.session_id,
                data={
                    "action": "object_created",
                    "object_id": new_object.id,
                    "admin_id": admin_session.player.id if admin_session.player else None
                }
            ))

            logger.info(f"실시간 객체 생성: {new_object.id} (관리자: {admin_session.player.username if admin_session.player else 'Unknown'})")
            return True

        except Exception as e:
            logger.error(f"실시간 객체 생성 실패: {e}")
            await admin_session.send_error(f"객체 생성 실패: {str(e)}")
            return False

    async def validate_and_repair_world(self, admin_session: Optional[Session] = None) -> Dict[str, Any]:
        """
        게임 세계의 무결성을 검증하고 자동으로 수정합니다.

        Args:
            admin_session: 관리자 세션 (결과 알림용, 선택사항)

        Returns:
            Dict: 검증 및 수정 결과
        """
        try:
            # 무결성 검증
            issues = await self.world_manager.validate_world_integrity()

            # 문제가 있는 경우 자동 수정
            repair_result = {}
            if any(issues.values()):
                repair_result = await self.world_manager.repair_world_integrity()

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