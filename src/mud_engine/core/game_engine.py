# -*- coding: utf-8 -*-
"""리팩토링된 게임 엔진 코어 클래스"""

import logging
from typing import Dict, Optional, Any, TYPE_CHECKING
from datetime import datetime

from .event_bus import EventBus, Event, EventType, get_event_bus
from .managers import CommandManager, EventHandler, PlayerMovementManager, AdminManager, GlobalTickManager
from .managers.time_manager import TimeManager
from .managers.scheduler_manager import SchedulerManager
from .types import SessionType
from ..game.managers import PlayerManager, WorldManager
from ..game.repositories import RoomRepository, GameObjectRepository
from ..database.connection import DatabaseManager

if TYPE_CHECKING:
    from ..server.session_manager import SessionManager
    from ..game.models import Player

logger = logging.getLogger(__name__)


class GameEngine:
    """MUD 게임의 핵심 엔진 클래스 - 리팩토링된 버전"""

    def __init__(self,
                 session_manager: 'SessionManager',
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

        # ModelManager 초기화
        from ..game.repositories import ModelManager
        self.model_manager = ModelManager(db_manager)

        # WorldManager 초기화
        room_repo = RoomRepository(db_manager)
        object_repo = GameObjectRepository(db_manager)
        from ..game.repositories import MonsterRepository
        monster_repo = MonsterRepository(db_manager)
        self.world_manager = WorldManager(room_repo, object_repo, monster_repo)

        # WorldManager에 GameEngine 참조 설정 (순환 참조 방지)
        self.world_manager.set_game_engine(self)

        # CombatManager 및 CombatHandler 초기화
        from ..game.combat import CombatManager
        from ..game.combat_handler import CombatHandler
        self.combat_manager = CombatManager(self.session_manager)
        self.combat_handler = CombatHandler(self.combat_manager, self.world_manager, self, self.session_manager)

        self._running = False
        self._start_time: Optional[datetime] = None

        # 매니저들 초기화
        try:
            self.command_manager = CommandManager(self)
            self.event_handler = EventHandler(self)
            self.movement_manager = PlayerMovementManager(self)
            self.admin_manager = AdminManager(self)
            self.time_manager = TimeManager(self)
            self.scheduler_manager = SchedulerManager(self)
            self.global_tick_manager = GlobalTickManager(self)

            # 튜토리얼 안내 시스템 초기화
            from ..game.tutorial_announcer import get_tutorial_announcer
            self.tutorial_announcer = get_tutorial_announcer(self)

            logger.info("모든 매니저 초기화 완료")
        except Exception as e:
            logger.error(f"매니저 초기화 실패: {e}", exc_info=True)
            raise

        # 이벤트 구독 설정
        try:
            self.event_handler.setup_event_subscriptions()
            logger.info("이벤트 구독 설정 완료")
        except Exception as e:
            logger.error(f"이벤트 구독 설정 실패: {e}", exc_info=True)
            raise

        logger.info("GameEngine 초기화 완료 (리팩토링된 버전)")

    # === 핵심 엔진 메서드들 ===

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

        # 몬스터 템플릿 및 스폰 시스템 시작
        try:
            # 템플릿 로드
            await self.world_manager.initialize_templates()
            logger.info("몬스터 템플릿 로드 완료")

            # 글로벌 스폰 제한 설정
            self.world_manager.set_global_spawn_limit('template_small_rat', 20)
            self.world_manager.set_global_spawn_limit('template_forest_goblin', 10)
            self.world_manager.set_global_spawn_limit('template_town_guard', 4)
            logger.info("글로벌 스폰 제한 설정 완료")

            # 초과 몬스터 정리
            await self.world_manager.cleanup_all_excess_monsters()

            await self.world_manager.setup_default_spawn_points()
            await self.world_manager.start_spawn_scheduler()
            logger.info("몬스터 스폰 시스템 시작 완료")
        except Exception as e:
            logger.error(f"몬스터 스폰 시스템 시작 실패: {e}")

        # 시간 시스템 시작
        try:
            await self.time_manager.start()
            logger.info("시간 시스템 시작 완료")
        except Exception as e:
            logger.error(f"시간 시스템 시작 실패: {e}")

        # 글로벌 스케줄러 시작
        try:
            # 전투 tick 이벤트 등록 (15초마다 실행)
            from .managers.scheduler_manager import ScheduleInterval
            self.scheduler_manager.register_event(
                "combat_tick",
                self._process_combat_tick,
                [ScheduleInterval.SECOND_00, ScheduleInterval.SECOND_15,
                 ScheduleInterval.SECOND_30, ScheduleInterval.SECOND_45]
            )
            await self.scheduler_manager.start()
            logger.info("글로벌 스케줄러 시작 완료")
        except Exception as e:
            logger.error(f"글로벌 스케줄러 시작 실패: {e}")

        # 글로벌 3초 Tick 시작
        try:
            await self.global_tick_manager.start()
            logger.info("글로벌 Tick 매니저 시작 완료")
        except Exception as e:
            logger.error(f"글로벌 Tick 매니저 시작 실패: {e}")

        # 튜토리얼 안내 시스템 시작
        try:
            await self.tutorial_announcer.start()
            logger.info("튜토리얼 안내 시스템 시작 완료")
        except Exception as e:
            logger.error(f"튜토리얼 안내 시스템 시작 실패: {e}")

        logger.info("GameEngine 시작 완료")

    async def stop(self) -> None:
        """게임 엔진 중지"""
        if not self._running:
            return

        logger.info("GameEngine 중지 중...")

        self._running = False

        # 튜토리얼 안내 시스템 중지
        try:
            await self.tutorial_announcer.stop()
            logger.info("튜토리얼 안내 시스템 중지 완료")
        except Exception as e:
            logger.error(f"튜토리얼 안내 시스템 중지 실패: {e}")

        # 글로벌 스케줄러 중지
        try:
            await self.scheduler_manager.stop()
            logger.info("글로벌 스케줄러 중지 완료")
        except Exception as e:
            logger.error(f"글로벌 스케줄러 중지 실패: {e}")

        # 글로벌 Tick 중지
        try:
            await self.global_tick_manager.stop()
            logger.info("글로벌 Tick 매니저 중지 완료")
        except Exception as e:
            logger.error(f"글로벌 Tick 매니저 중지 실패: {e}")

        # 시간 시스템 중지
        try:
            await self.time_manager.stop()
            logger.info("시간 시스템 중지 완료")
        except Exception as e:
            logger.error(f"시간 시스템 중지 실패: {e}")

        # 몬스터 스폰 시스템 중지
        try:
            await self.world_manager.stop_spawn_scheduler()
            logger.info("몬스터 스폰 시스템 중지 완료")
        except Exception as e:
            logger.error(f"몬스터 스폰 시스템 중지 실패: {e}")

        # 모든 활성 세션에 종료 알림
        await self._notify_all_players_shutdown()

        logger.info("GameEngine 중지 완료")

    def is_running(self) -> bool:
        """게임 엔진 실행 상태 반환"""
        return self._running

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

    # === 플레이어 세션 관리 ===

    async def add_player_session(self, session: SessionType, player: 'Player') -> None:
        """
        플레이어 세션 추가

        Args:
            session: 세션 객체 (Session 또는 TelnetSession)
            player: 플레이어 객체
        """
        # SessionManager에 세션 추가
        self.session_manager.add_session(session)
        await self.session_manager.authenticate_session(session.session_id, player)
        short_session_id = session.session_id.split('-')[-1] if '-' in session.session_id else session.session_id
        logger.info(f"SessionManager에 세션 추가: {short_session_id}, 플레이어: {player.username}")

        # 세션에 게임 엔진 참조 설정
        session.game_engine = self
        session.locale = player.preferred_locale

        # 플레이어를 마지막 위치(좌표 기반) 또는 기본 방으로 이동
        target_room = await self.world_manager.get_room_at_coordinates(
            player.last_room_x, player.last_room_y
        )
        if not target_room:
            logger.warning(f"저장된 좌표 ({player.last_room_x}, {player.last_room_y})에 방이 없음. 기본 방으로 이동")
            target_room = await self.world_manager.get_room_at_coordinates(0, 0)

        target_room_id = target_room.id if target_room else "town_square"

        await self.movement_manager.move_player_to_room(session, target_room_id)

        # 방 정보를 가져와서 좌표로 로그 표시
        logger.info(f"플레이어 {player.username} 로그인: 위치 ({player.last_room_x}, {player.last_room_y})로 복원")

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

        # 플레이어를 기본 채널에 자동 참여 (chat_manager가 있는 경우)
        if hasattr(self, 'chat_manager') and self.chat_manager:
            self.chat_manager.subscribe_to_channel(player.id, "ooc")

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

    async def remove_player_session(self, session: SessionType, reason: str = "연결 종료") -> None:
        """
        플레이어 세션 제거

        Args:
            session: 세션 객체 (Session 또는 TelnetSession)
            reason: 제거 이유
        """
        # 따라가기 관련 정리 작업 수행
        await self.movement_manager.handle_player_disconnect_cleanup(session)

        if session.player:
            # 현재 위치 저장 (좌표 기반)
            current_room_id = getattr(session, 'current_room_id', None)
            if current_room_id:
                try:
                    # 방 좌표 가져오기
                    room = await self.world_manager.get_room(current_room_id)
                    if room:
                        session.player.last_room_x = room.x
                        session.player.last_room_y = room.y
                        await self.player_manager.save_player(session.player)
                        logger.info(f"플레이어 {session.player.username} 로그아웃: 위치 ({room.x}, {room.y}) 저장")
                    else:
                        logger.warning(f"플레이어 {session.player.username} 로그아웃: 방 정보를 찾을 수 없음")
                except Exception as e:
                    logger.error(f"플레이어 위치 저장 실패: {e}")
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

    # === 메시지 브로드캐스트 ===

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

        # 실제 브로드캐스트 수행 - 해당 방에 있는 플레이어들만 대상
        count = 0
        for session in self.session_manager.iter_authenticated_sessions():
            if (session.player and
                session.session_id != exclude_session and
                getattr(session, 'current_room_id', None) == room_id):
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

    # === 명령어 처리 ===

    async def handle_player_command(self, session: SessionType, command: str):
        """
        플레이어 명령어 처리

        Args:
            session: 세션 객체 (Session 또는 TelnetSession)
            command: 명령어

        Returns:
            명령어 실행 결과
        """
        return await self.command_manager.handle_player_command(session, command)

    # === 월드 관리 위임 메서드들 ===

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
            logger.debug(f"방 정보 조회 시작: room_id={room_id}, locale={locale}")
            location_summary = await self.world_manager.get_location_summary(room_id, locale)
            logger.debug(f"방 정보 조회 완료: room_id={room_id}")
            return location_summary
        except Exception as e:
            logger.error(f"방 정보 조회 실패 ({room_id}): {e}", exc_info=True)
            return None

    # === 관리자 기능 위임 메서드들 ===

    async def create_room_realtime(self, room_data: Dict[str, Any], admin_session: SessionType) -> bool:
        """실시간으로 새로운 방을 생성합니다."""
        return await self.admin_manager.create_room_realtime(room_data, admin_session)

    async def update_room_realtime(self, room_id: str, updates: Dict[str, Any], admin_session: SessionType) -> bool:
        """실시간으로 방 정보를 수정합니다."""
        return await self.admin_manager.update_room_realtime(room_id, updates, admin_session)

    async def create_object_realtime(self, object_data: Dict[str, Any], admin_session: SessionType) -> bool:
        """실시간으로 새로운 게임 객체를 생성합니다."""
        return await self.admin_manager.create_object_realtime(object_data, admin_session)

    async def validate_and_repair_world(self, admin_session: Optional[SessionType] = None) -> Dict[str, Any]:
        """게임 세계의 무결성을 검증하고 자동으로 수정합니다."""
        return await self.admin_manager.validate_and_repair_world(admin_session)

    # === 이동 관리 위임 메서드들 ===

    async def move_player_to_room(self, session: SessionType, room_id: str, skip_followers: bool = False) -> bool:
        """플레이어를 특정 방으로 이동시킵니다."""
        return await self.movement_manager.move_player_to_room(session, room_id, skip_followers)

    async def update_room_player_list(self, room_id: str) -> None:
        """방의 플레이어 목록을 실시간으로 업데이트합니다."""
        await self.movement_manager.update_room_player_list(room_id)

    async def handle_player_disconnect_cleanup(self, session: SessionType) -> None:
        """플레이어 연결 해제 시 따라가기 관련 정리 작업"""
        await self.movement_manager.handle_player_disconnect_cleanup(session)

    # === 유틸리티 메서드들 ===

    async def _notify_all_players_shutdown(self) -> None:
        """모든 플레이어에게 서버 종료 알림"""
        shutdown_message = {
            "type": "system_message",
            "message": "🛑 서버가 곧 종료됩니다. 연결이 끊어집니다.",
            "timestamp": datetime.now().isoformat()
        }

        count = await self.broadcast_to_all(shutdown_message)
        logger.info(f"서버 종료 알림 전송: {count}명의 플레이어")

    def _find_session_by_player_id(self, player_id: str) -> Optional[SessionType]:
        """플레이어 ID로 세션 찾기"""
        for session in self.session_manager.sessions.values():
            if session.player and session.player.id == player_id:
                return session
        return None

    # === 전투 시스템 관련 메서드들 ===

    async def _process_combat_tick(self) -> None:
        """
        전투 tick 처리 (스케줄러에서 15초마다 호출)
        연결된 플레이어가 없는 전투의 타임아웃을 관리합니다.
        """
        try:
            result = await self.combat_manager.process_combat_tick()

            if result["timed_out_combats"]:
                for combat_id in result["timed_out_combats"]:
                    logger.info(f"전투 {combat_id} 타임아웃으로 종료됨")

            # 활성 전투가 있으면 로그
            if result["active_combats"] > 0:
                logger.debug(f"전투 tick 처리 완료: 활성 전투 {result['active_combats']}개")

        except Exception as e:
            logger.error(f"전투 tick 처리 오류: {e}", exc_info=True)

    async def try_rejoin_combat(self, session: SessionType) -> bool:
        """
        플레이어 재접속 시 기존 전투에 복귀 시도

        Args:
            session: 재접속한 플레이어의 세션

        Returns:
            bool: 전투 복귀 성공 여부
        """
        if not session.player:
            return False

        player_id = session.player.id
        combat = self.combat_manager.try_rejoin_combat(player_id, session.player)

        if combat:
            # 세션 전투 상태 복구
            session.in_combat = True
            session.combat_id = combat.id
            session.current_room_id = f"combat_{combat.id}"
            session.original_room_id = combat.room_id

            # 전투 복귀 메시지 전송
            await session.send_message({
                "type": "combat_rejoin",
                "message": "⚔️ 진행 중인 전투에 복귀했습니다!",
                "combat_id": combat.id,
                "combat_status": combat.to_dict()
            })

            logger.info(f"플레이어 {session.player.username} 전투 {combat.id}에 복귀")
            return True

        return False