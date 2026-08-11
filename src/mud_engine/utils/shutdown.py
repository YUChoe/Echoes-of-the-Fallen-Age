# -*- coding: utf-8 -*-
"""종료 신호 처리

시그널 핸들러에서 예외를 던지지 않는다. `KeyboardInterrupt` 를 올리면 실행 중이던
임의의 지점에서 터져 종료 절차가 중간에 끊기고, 종료 진행 중 재진입도 막지
못한다. 이전 구현은 한 번의 SIGINT 로 핸들러가 세 번 호출되고 `KeyboardInterrupt`
가 처리되지 않은 채 남았다.

대신 종료 이벤트를 세워 대기 중인 메인 코루틴을 깨운다. 두 번째 신호는 무시한다.
"""

import asyncio
import logging
import signal
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ShutdownSignal:
    """종료 신호를 한 번만 처리한다."""

    def __init__(
        self, loop: asyncio.AbstractEventLoop, event: asyncio.Event
    ) -> None:
        """
        Args:
            loop: 이벤트를 세울 이벤트 루프
            event: 메인 코루틴이 기다리는 종료 이벤트
        """
        self._loop = loop
        self._event = event
        self._triggered = False

    @property
    def triggered(self) -> bool:
        """종료 신호를 이미 받았는지"""
        return self._triggered

    def handle(self, signum: int, frame: Optional[Any] = None) -> None:
        """시그널 핸들러 본체.

        `Event.set()` 을 직접 부르지 않고 루프에 넘긴다. 시그널 핸들러가 루프
        스레드 밖에서 실행될 수 있기 때문이다.
        """
        if self._triggered:
            logger.warning(f"Signal {signum} 무시. 이미 종료 중이다")
            return

        self._triggered = True
        logger.info(f"Signal {signum} 수신됨. 서버 종료 절차 시작...")
        print(f"\n🛑 Signal {signum} 수신됨. 서버 종료 중...")

        self._loop.call_soon_threadsafe(self._event.set)

    def install(self) -> tuple[str, ...]:
        """사용 가능한 종료 시그널에 핸들러를 등록한다.

        Windows 와 Unix 모두 지원한다. 없는 시그널은 건너뛴다.

        Returns:
            등록한 시그널 이름
        """
        installed: list[str] = []

        for name in ("SIGTERM", "SIGINT", "SIGBREAK"):
            sig = getattr(signal, name, None)
            if sig is None:
                continue
            signal.signal(sig, self.handle)
            installed.append(name)

        return tuple(installed)
