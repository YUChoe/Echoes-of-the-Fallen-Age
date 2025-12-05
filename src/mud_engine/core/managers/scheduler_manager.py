# -*- coding: utf-8 -*-
"""글로벌 스케줄러 시스템"""

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Callable, Awaitable, Dict, List
from dataclasses import dataclass
from enum import Enum

if TYPE_CHECKING:
    from ..game_engine import GameEngine

logger = logging.getLogger(__name__)


class ScheduleInterval(Enum):
    """스케줄 간격 열거형"""
    SECOND_00 = 0
    SECOND_15 = 15
    SECOND_30 = 30
    SECOND_45 = 45


@dataclass
class ScheduledEvent:
    """스케줄된 이벤트"""
    name: str
    callback: Callable[[], Awaitable[None]]
    intervals: List[ScheduleInterval]
    enabled: bool = True
    last_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0


class SchedulerManager:
    """글로벌 스케줄러 매니저 - 0, 15, 30, 45초에 이벤트 실행"""

    def __init__(self, game_engine: 'GameEngine'):
        """
        SchedulerManager 초기화

        Args:
            game_engine: 게임 엔진 인스턴스
        """
        self.game_engine = game_engine
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._events: Dict[str, ScheduledEvent] = {}
        
        logger.info("SchedulerManager 초기화 완료")

    def register_event(
        self,
        name: str,
        callback: Callable[[], Awaitable[None]],
        intervals: List[ScheduleInterval]
    ) -> None:
        """
        스케줄 이벤트 등록

        Args:
            name: 이벤트 이름 (고유 식별자)
            callback: 실행할 비동기 함수
            intervals: 실행할 초 간격 리스트

        Example:
            scheduler.register_event(
                "monster_spawn",
                self._spawn_monsters,
                [ScheduleInterval.SECOND_00, ScheduleInterval.SECOND_30]
            )
        """
        if name in self._events:
            logger.warning(f"이벤트 '{name}'이 이미 등록되어 있습니다. 덮어씁니다.")
        
        event = ScheduledEvent(
            name=name,
            callback=callback,
            intervals=intervals
        )
        self._events[name] = event
        logger.info(f"스케줄 이벤트 등록: {name} (간격: {[i.value for i in intervals]}초)")

    def unregister_event(self, name: str) -> bool:
        """
        스케줄 이벤트 등록 해제

        Args:
            name: 이벤트 이름

        Returns:
            bool: 성공 여부
        """
        if name in self._events:
            del self._events[name]
            logger.info(f"스케줄 이벤트 등록 해제: {name}")
            return True
        
        logger.warning(f"등록되지 않은 이벤트: {name}")
        return False

    def enable_event(self, name: str) -> bool:
        """
        이벤트 활성화

        Args:
            name: 이벤트 이름

        Returns:
            bool: 성공 여부
        """
        if name in self._events:
            self._events[name].enabled = True
            logger.info(f"스케줄 이벤트 활성화: {name}")
            return True
        
        logger.warning(f"등록되지 않은 이벤트: {name}")
        return False

    def disable_event(self, name: str) -> bool:
        """
        이벤트 비활성화

        Args:
            name: 이벤트 이름

        Returns:
            bool: 성공 여부
        """
        if name in self._events:
            self._events[name].enabled = False
            logger.info(f"스케줄 이벤트 비활성화: {name}")
            return True
        
        logger.warning(f"등록되지 않은 이벤트: {name}")
        return False

    def get_event_info(self, name: str) -> Optional[Dict]:
        """
        이벤트 정보 조회

        Args:
            name: 이벤트 이름

        Returns:
            Dict: 이벤트 정보 또는 None
        """
        if name not in self._events:
            return None
        
        event = self._events[name]
        return {
            "name": event.name,
            "enabled": event.enabled,
            "intervals": [i.value for i in event.intervals],
            "last_run": event.last_run.isoformat() if event.last_run else None,
            "run_count": event.run_count,
            "error_count": event.error_count
        }

    def list_events(self) -> List[Dict]:
        """
        등록된 모든 이벤트 목록 조회

        Returns:
            List[Dict]: 이벤트 정보 리스트
        """
        return [self.get_event_info(name) for name in self._events.keys()]

    async def start(self) -> None:
        """스케줄러 시작"""
        if self._running:
            logger.warning("SchedulerManager가 이미 실행 중입니다")
            return

        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        
        event_count = len(self._events)
        enabled_count = sum(1 for e in self._events.values() if e.enabled)
        logger.info(f"글로벌 스케줄러 시작 완료 (등록된 이벤트: {event_count}개, 활성: {enabled_count}개)")

    async def stop(self) -> None:
        """스케줄러 중지"""
        if not self._running:
            return

        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("글로벌 스케줄러 중지 완료")

    async def _scheduler_loop(self) -> None:
        """스케줄러 메인 루프"""
        try:
            loop_count = 0
            while self._running:
                now = datetime.now()
                current_second = now.second

                # 다음 실행 시점 계산
                next_trigger = self._calculate_next_trigger(current_second)
                wait_seconds = self._calculate_wait_seconds(current_second, next_trigger)

                logger.debug(f"현재 시간: {now.strftime('%H:%M:%S')}, "
                           f"다음 트리거: {next_trigger}초, "
                           f"대기 시간: {wait_seconds:.2f}초")

                # 대기
                await asyncio.sleep(wait_seconds)

                if not self._running:
                    break

                # 이벤트 실행
                await self._execute_scheduled_events(next_trigger)
                
                # 1분마다 상태 로그 (0초 트리거 시)
                loop_count += 1
                if next_trigger == 0 and loop_count % 1 == 0:
                    event_count = len(self._events)
                    enabled_count = sum(1 for e in self._events.values() if e.enabled)
                    total_runs = sum(e.run_count for e in self._events.values())
                    total_errors = sum(e.error_count for e in self._events.values())
                    logger.info(f"스케줄러 상태: 이벤트 {event_count}개 (활성 {enabled_count}개), "
                              f"총 실행 {total_runs}회, 오류 {total_errors}회")

        except asyncio.CancelledError:
            logger.info("스케줄러 루프 취소됨")
        except Exception as e:
            logger.error(f"스케줄러 루프 오류: {e}", exc_info=True)

    def _calculate_next_trigger(self, current_second: int) -> int:
        """
        다음 트리거 시점 계산

        Args:
            current_second: 현재 초 (0-59)

        Returns:
            int: 다음 트리거 초 (0, 15, 30, 45)
        """
        trigger_seconds = [0, 15, 30, 45]
        
        for trigger in trigger_seconds:
            if trigger > current_second:
                return trigger
        
        # 다음 분의 0초
        return 0

    def _calculate_wait_seconds(self, current_second: int, next_trigger: int) -> float:
        """
        다음 트리거까지 대기 시간 계산

        Args:
            current_second: 현재 초
            next_trigger: 다음 트리거 초

        Returns:
            float: 대기 시간 (초)
        """
        now = datetime.now()
        current_microsecond = now.microsecond

        if next_trigger > current_second:
            # 같은 분 내
            seconds_diff = next_trigger - current_second
            wait_seconds = seconds_diff - (current_microsecond / 1_000_000)
        else:
            # 다음 분
            seconds_diff = (60 - current_second) + next_trigger
            wait_seconds = seconds_diff - (current_microsecond / 1_000_000)

        return max(0.1, wait_seconds)  # 최소 0.1초

    async def _execute_scheduled_events(self, trigger_second: int) -> None:
        """
        스케줄된 이벤트 실행

        Args:
            trigger_second: 트리거 초 (0, 15, 30, 45)
        """
        trigger_interval = ScheduleInterval(trigger_second)
        executed_count = 0
        
        logger.debug(f"스케줄 이벤트 실행 시작: {trigger_second}초")

        for event in self._events.values():
            if not event.enabled:
                continue
            
            if trigger_interval not in event.intervals:
                continue

            try:
                logger.debug(f"이벤트 실행: {event.name}")
                await event.callback()
                
                event.last_run = datetime.now()
                event.run_count += 1
                executed_count += 1
                
                logger.debug(f"이벤트 실행 완료: {event.name} (총 {event.run_count}회)")
            
            except Exception as e:
                event.error_count += 1
                logger.error(f"이벤트 실행 오류 ({event.name}): {e}", exc_info=True)

        if executed_count > 0:
            logger.info(f"스케줄 이벤트 실행 완료: {executed_count}개 이벤트 ({trigger_second}초)")
