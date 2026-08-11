# -*- coding: utf-8 -*-
"""게임 시간 관리 시스템"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..game_engine import GameEngine

logger = logging.getLogger(__name__)


class TimeOfDay(Enum):
    """시간대 열거형"""
    DAY = "day"
    NIGHT = "night"


class TimeManager:
    """게임 내 시간 관리 및 낮/밤 주기 시스템"""

    def __init__(self, game_engine: 'GameEngine'):
        """
        TimeManager 초기화

        Args:
            game_engine: 게임 엔진 인스턴스
        """
        self.game_engine = game_engine
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._map_export_counter: int = 0  # 맵 생성 카운터 (15초 * 40 = 10분)
        
        # 현재 시간에 맞게 초기 시간대 설정
        now = datetime.now()
        current_minute = now.minute
        day_minutes = [5, 15, 25, 35, 45, 55]
        night_minutes = [0, 10, 20, 30, 40, 50]
        
        # 가장 최근의 변경 시점 찾기
        all_minutes = sorted(day_minutes + night_minutes)
        last_change = 0
        for minute in reversed(all_minutes):
            if minute <= current_minute:
                last_change = minute
                break
        else:
            # 현재 분이 모든 변경 시점보다 작으면 이전 시간의 마지막 변경 시점
            last_change = all_minutes[-1]
        
        if last_change in day_minutes:
            self.current_time = TimeOfDay.DAY
        else:
            self.current_time = TimeOfDay.NIGHT
        
        logger.info(f"TimeManager 초기화 완료 (현재 시간대: {self.current_time.value})")

    def get_current_time(self) -> TimeOfDay:
        """현재 시간대 반환"""
        return self.current_time

    def is_day(self) -> bool:
        """낮인지 확인"""
        return self.current_time == TimeOfDay.DAY

    def is_night(self) -> bool:
        """밤인지 확인"""
        return self.current_time == TimeOfDay.NIGHT

    async def start(self) -> None:
        """시간 시스템 시작"""
        if self._running:
            logger.warning("TimeManager가 이미 실행 중입니다")
            return

        self._running = True
        self._task = asyncio.create_task(self._time_cycle_loop())

        # 맵 HTML 자동 생성 스케줄은 제거했다. 맵은 어드민 채널의 admin_map 으로
        # 요청 시점에 만들며 파일로 남기지 않는다
        logger.info("시간 시스템 시작 완료")

    async def stop(self) -> None:
        """시간 시스템 중지"""
        if not self._running:
            return

        self._running = False
        
        # 시간 주기 태스크 중지
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # 스케줄러에서 맵 생성 이벤트 제거
        self.game_engine.scheduler_manager.unregister_event("map_export")

        logger.info("시간 시스템 중지 완료")

    async def _time_cycle_loop(self) -> None:
        """시간 주기 루프"""
        try:
            while self._running:
                # 현재 시간의 분 확인
                now = datetime.now()
                current_minute = now.minute

                # 다음 변경 시간 계산
                next_change_minute = self._calculate_next_change_minute(current_minute)
                wait_seconds = self._calculate_wait_seconds(current_minute, next_change_minute)

                logger.info(f"현재 시간: {now.strftime('%H:%M')}, "
                          f"다음 변경: {next_change_minute}분, "
                          f"대기 시간: {wait_seconds}초")

                # 대기
                await asyncio.sleep(wait_seconds)

                if not self._running:
                    break

                # 시간대 변경
                await self._change_time_of_day()

        except asyncio.CancelledError:
            logger.info("시간 주기 루프 취소됨")
        except Exception as e:
            logger.error(f"시간 주기 루프 오류: {e}", exc_info=True)

    def _calculate_next_change_minute(self, current_minute: int) -> int:
        """
        다음 시간 변경 시점 계산

        Args:
            current_minute: 현재 분

        Returns:
            int: 다음 변경 시점의 분 (0-59)
        """
        # 낮으로 변경: 5, 15, 25, 35, 45, 55
        # 밤으로 변경: 0, 10, 20, 30, 40, 50
        change_minutes = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]

        for minute in change_minutes:
            if minute > current_minute:
                return minute

        # 다음 시간의 0분
        return 0

    def _calculate_wait_seconds(self, current_minute: int, next_change_minute: int) -> float:
        """
        다음 변경까지 대기 시간 계산

        Args:
            current_minute: 현재 분
            next_change_minute: 다음 변경 분

        Returns:
            float: 대기 시간 (초)
        """
        now = datetime.now()
        current_second = now.second

        if next_change_minute > current_minute:
            # 같은 시간 내
            minutes_diff = next_change_minute - current_minute
            wait_seconds = (minutes_diff * 60) - current_second
        else:
            # 다음 시간
            minutes_diff = (60 - current_minute) + next_change_minute
            wait_seconds = (minutes_diff * 60) - current_second

        return max(1, wait_seconds)  # 최소 1초

    async def _change_time_of_day(self) -> None:
        """시간대 변경 및 알림"""
        now = datetime.now()
        current_minute = now.minute
        
        logger.info(f"_change_time_of_day 호출됨: 현재 분={current_minute}")

        # 낮/밤 결정
        # 낮: 5, 15, 25, 35, 45, 55
        # 밤: 0, 10, 20, 30, 40, 50
        day_minutes = [5, 15, 25, 35, 45, 55]
        night_minutes = [0, 10, 20, 30, 40, 50]

        old_time = self.current_time

        if current_minute in day_minutes:
            self.current_time = TimeOfDay.DAY
        elif current_minute in night_minutes:
            self.current_time = TimeOfDay.NIGHT
        else:
            # 예상치 못한 시간 (오차 허용)
            logger.warning(f"예상치 못한 시간 변경 시점: {current_minute}분")
            return

        # 시간이 실제로 변경된 경우에만 알림
        logger.info(f"시간 비교: old={old_time.value}, new={self.current_time.value}")
        if old_time != self.current_time:
            logger.info(f"시간대 변경: {old_time.value} -> {self.current_time.value}")
            await self._notify_time_change()
        else:
            logger.info(f"시간대 변경 없음 (이미 {self.current_time.value})")

    async def _notify_time_change(self) -> None:
        """모든 접속 유저에게 시간 변경 알림

        색상은 클라이언트가 결정한다. 서버는 번역 키만 보낸다.
        """
        from ...server.serialization import build_event

        # 모든 활성 세션에 알림
        from typing import Any, List
        all_sessions: List[Any] = []
        
        # SessionManager를 통해 모든 세션 가져오기
        all_sessions.extend(self.game_engine.session_manager.iter_all_sessions())
        
        logger.info(f"전체 세션 수: {len(all_sessions)}")
        
        sent_count = 0
        for session in all_sessions:
            if hasattr(session, 'is_authenticated') and session.is_authenticated:
                try:
                    key = (
                        "time.dawn"
                        if self.current_time == TimeOfDay.DAY
                        else "time.dusk"
                    )
                    await session.send_message(build_event(key, category="system"))
                    sent_count += 1
                except Exception as e:
                    session_id = getattr(session, 'session_id', 'unknown')
                    logger.error(f"시간 변경 알림 전송 실패 (세션 {session_id}): {e}")

        logger.info(f"시간 변경 알림 전송 완료 (전송: {sent_count}/{len(all_sessions)})")

