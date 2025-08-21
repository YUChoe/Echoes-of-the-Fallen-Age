# -*- coding: utf-8 -*-
"""이벤트 버스 시스템"""

import asyncio
import logging
from typing import Dict, List, Callable, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class EventType(Enum):
    """이벤트 타입 정의"""
    # 플레이어 관련 이벤트
    PLAYER_CONNECTED = "player_connected"
    PLAYER_DISCONNECTED = "player_disconnected"
    PLAYER_LOGIN = "player_login"
    PLAYER_LOGOUT = "player_logout"
    PLAYER_MOVED = "player_moved"
    PLAYER_COMMAND = "player_command"

    # 게임 세계 관련 이벤트
    ROOM_ENTERED = "room_entered"
    ROOM_LEFT = "room_left"
    ROOM_MESSAGE = "room_message"
    ROOM_BROADCAST = "room_broadcast"

    # 객체 관련 이벤트
    OBJECT_CREATED = "object_created"
    OBJECT_DESTROYED = "object_destroyed"
    OBJECT_MOVED = "object_moved"
    OBJECT_INTERACTED = "object_interacted"

    # 시스템 이벤트
    SERVER_STARTED = "server_started"
    SERVER_STOPPING = "server_stopping"
    SERVER_STOPPED = "server_stopped"

    # 커스텀 이벤트
    CUSTOM = "custom"


@dataclass
class Event:
    """이벤트 데이터 클래스"""
    event_type: EventType
    source: str  # 이벤트 발생원 (session_id, player_id 등)
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    target: Optional[str] = None  # 특정 대상 (선택사항)
    room_id: Optional[str] = None  # 방 ID (선택사항)

    def __post_init__(self):
        """이벤트 생성 후 처리"""
        if isinstance(self.event_type, str):
            # 문자열로 전달된 경우 EventType으로 변환 시도
            try:
                self.event_type = EventType(self.event_type)
            except ValueError:
                self.event_type = EventType.CUSTOM
                self.data["original_type"] = self.event_type


class EventBus:
    """이벤트 버스 - 이벤트 발행/구독 시스템"""

    def __init__(self):
        """EventBus 초기화"""
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._event_history: List[Event] = []
        self._max_history: int = 1000  # 최대 이벤트 히스토리 개수
        self._running: bool = False
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processor_task: Optional[asyncio.Task] = None

        logger.info("EventBus 초기화 완료")

    async def start(self) -> None:
        """이벤트 버스 시작"""
        if self._running:
            logger.warning("EventBus가 이미 실행 중입니다")
            return

        self._running = True
        self._processor_task = asyncio.create_task(self._process_events())
        logger.info("EventBus 시작됨")

        # 서버 시작 이벤트 발행
        await self.publish(Event(
            event_type=EventType.SERVER_STARTED,
            source="event_bus",
            data={"timestamp": datetime.now().isoformat()}
        ))

    async def stop(self) -> None:
        """이벤트 버스 중지"""
        if not self._running:
            return

        logger.info("EventBus 중지 중...")

        # 서버 중지 이벤트 발행
        await self.publish(Event(
            event_type=EventType.SERVER_STOPPING,
            source="event_bus",
            data={"timestamp": datetime.now().isoformat()}
        ))

        self._running = False

        if self._processor_task and not self._processor_task.done():
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass

        # 서버 중지 완료 이벤트 발행 (동기적으로)
        stop_event = Event(
            event_type=EventType.SERVER_STOPPED,
            source="event_bus",
            data={"timestamp": datetime.now().isoformat()}
        )
        await self._handle_event(stop_event)

        logger.info("EventBus 중지 완료")

    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """
        이벤트 구독

        Args:
            event_type: 구독할 이벤트 타입
            callback: 이벤트 발생 시 호출될 콜백 함수
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append(callback)
        logger.debug(f"이벤트 구독 등록: {event_type.value} -> {callback.__name__}")

    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> bool:
        """
        이벤트 구독 해제

        Args:
            event_type: 구독 해제할 이벤트 타입
            callback: 제거할 콜백 함수

        Returns:
            bool: 구독 해제 성공 여부
        """
        if event_type in self._subscribers and callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)
            logger.debug(f"이벤트 구독 해제: {event_type.value} -> {callback.__name__}")
            return True
        return False

    async def publish(self, event: Event) -> None:
        """
        이벤트 발행

        Args:
            event: 발행할 이벤트
        """
        if not self._running:
            logger.warning(f"EventBus가 중지된 상태에서 이벤트 발행 시도: {event.event_type.value}")
            return

        await self._event_queue.put(event)
        logger.debug(f"이벤트 발행: {event.event_type.value} (ID: {event.event_id})")

    async def _process_events(self) -> None:
        """이벤트 처리 루프 (백그라운드 작업)"""
        logger.info("이벤트 처리 루프 시작")

        try:
            while self._running:
                try:
                    # 이벤트 대기 (타임아웃 설정)
                    event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                    await self._handle_event(event)
                except asyncio.TimeoutError:
                    # 타임아웃은 정상적인 상황 (루프 유지용)
                    continue
                except Exception as e:
                    logger.error(f"이벤트 처리 중 오류: {e}", exc_info=True)

        except asyncio.CancelledError:
            logger.info("이벤트 처리 루프 취소됨")
        finally:
            logger.info("이벤트 처리 루프 종료")

    async def _handle_event(self, event: Event) -> None:
        """
        개별 이벤트 처리

        Args:
            event: 처리할 이벤트
        """
        try:
            # 이벤트 히스토리에 추가
            self._add_to_history(event)

            # 구독자들에게 이벤트 전달
            subscribers = self._subscribers.get(event.event_type, [])

            if not subscribers:
                logger.debug(f"구독자가 없는 이벤트: {event.event_type.value}")
                return

            # 모든 구독자에게 이벤트 전달
            for callback in subscribers:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"이벤트 콜백 실행 중 오류 ({callback.__name__}): {e}", exc_info=True)

            logger.debug(f"이벤트 처리 완료: {event.event_type.value} -> {len(subscribers)}개 구독자")

        except Exception as e:
            logger.error(f"이벤트 처리 중 오류: {e}", exc_info=True)

    def _add_to_history(self, event: Event) -> None:
        """
        이벤트를 히스토리에 추가

        Args:
            event: 추가할 이벤트
        """
        self._event_history.append(event)

        # 히스토리 크기 제한
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

    def get_subscribers(self, event_type: EventType) -> List[Callable]:
        """
        특정 이벤트 타입의 구독자 목록 반환

        Args:
            event_type: 이벤트 타입

        Returns:
            List[Callable]: 구독자 목록
        """
        return self._subscribers.get(event_type, []).copy()

    def get_event_history(self, event_type: Optional[EventType] = None,
                         limit: int = 100) -> List[Event]:
        """
        이벤트 히스토리 조회

        Args:
            event_type: 특정 이벤트 타입만 조회 (None이면 전체)
            limit: 최대 반환 개수

        Returns:
            List[Event]: 이벤트 히스토리
        """
        history = self._event_history

        if event_type:
            history = [e for e in history if e.event_type == event_type]

        return history[-limit:] if limit > 0 else history

    def get_stats(self) -> Dict[str, Any]:
        """
        이벤트 버스 통계 정보 반환

        Returns:
            Dict: 통계 정보
        """
        subscriber_counts = {
            event_type.value: len(callbacks)
            for event_type, callbacks in self._subscribers.items()
        }

        event_type_counts = {}
        for event in self._event_history:
            event_type = event.event_type.value
            event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1

        return {
            "running": self._running,
            "total_subscribers": sum(len(callbacks) for callbacks in self._subscribers.values()),
            "subscriber_counts": subscriber_counts,
            "event_history_size": len(self._event_history),
            "max_history_size": self._max_history,
            "event_type_counts": event_type_counts,
            "queue_size": self._event_queue.qsize() if self._running else 0
        }

    def clear_history(self) -> int:
        """
        이벤트 히스토리 초기화

        Returns:
            int: 삭제된 이벤트 개수
        """
        count = len(self._event_history)
        self._event_history.clear()
        logger.info(f"이벤트 히스토리 초기화: {count}개 이벤트 삭제")
        return count


# 전역 이벤트 버스 인스턴스
_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """
    전역 이벤트 버스 인스턴스 반환

    Returns:
        EventBus: 전역 이벤트 버스 인스턴스
    """
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


async def initialize_event_bus() -> EventBus:
    """
    전역 이벤트 버스 초기화 및 시작

    Returns:
        EventBus: 초기화된 이벤트 버스
    """
    event_bus = get_event_bus()
    if not event_bus._running:
        await event_bus.start()
    return event_bus


async def shutdown_event_bus() -> None:
    """전역 이벤트 버스 종료"""
    global _global_event_bus
    if _global_event_bus and _global_event_bus._running:
        await _global_event_bus.stop()
        _global_event_bus = None