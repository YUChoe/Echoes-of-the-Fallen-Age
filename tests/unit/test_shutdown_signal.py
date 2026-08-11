"""
종료 신호 처리 단위 테스트

핸들러가 예외를 던지지 않고, 재진입을 막고, 이벤트를 루프에 넘기는지 확인한다.
이전 구현은 `raise KeyboardInterrupt()` 뒤에 도달 불가 코드를 두어 한 번의
SIGINT 로 세 번 호출되고 종료 절차가 중간에 끊겼다.
"""

import asyncio
import signal

import pytest

from src.mud_engine.utils.shutdown import ShutdownSignal


class _StubLoop:
    """call_soon_threadsafe 호출을 기록한다"""

    def __init__(self) -> None:
        self.scheduled: list = []

    def call_soon_threadsafe(self, callback, *args) -> None:
        self.scheduled.append(callback)


def _signal() -> tuple[ShutdownSignal, _StubLoop, asyncio.Event]:
    loop = _StubLoop()
    event = asyncio.Event()
    return ShutdownSignal(loop, event), loop, event  # type: ignore[arg-type]


# 예외를 던지지 않는다 --------------------------------------------------------


def test_handler_does_not_raise():
    """시그널 핸들러가 예외를 올리면 종료 절차가 임의의 지점에서 끊긴다"""
    shutdown, _, _ = _signal()

    shutdown.handle(signal.SIGINT, None)  # 예외가 나면 테스트가 실패한다


def test_handler_schedules_event_on_the_loop():
    """Event.set() 을 직접 부르지 않고 루프에 넘긴다"""
    shutdown, loop, event = _signal()

    shutdown.handle(signal.SIGINT, None)

    assert len(loop.scheduled) == 1
    assert loop.scheduled[0] == event.set
    # 아직 실행되지 않았으므로 이벤트는 세워지지 않았다
    assert event.is_set() is False


def test_scheduled_callback_sets_the_event():
    """루프가 콜백을 실행하면 이벤트가 세워진다"""
    shutdown, loop, event = _signal()

    shutdown.handle(signal.SIGTERM, None)
    loop.scheduled[0]()

    assert event.is_set() is True


# 재진입 방지 ----------------------------------------------------------------


def test_second_signal_is_ignored():
    """종료 중 재진입을 막는다"""
    shutdown, loop, _ = _signal()

    shutdown.handle(signal.SIGINT, None)
    shutdown.handle(signal.SIGINT, None)
    shutdown.handle(signal.SIGTERM, None)

    assert len(loop.scheduled) == 1


def test_triggered_reflects_state():
    """종료 신호 수신 여부를 알 수 있다"""
    shutdown, _, _ = _signal()

    assert shutdown.triggered is False

    shutdown.handle(signal.SIGINT, None)

    assert shutdown.triggered is True


def test_frame_argument_is_optional():
    """시그널 핸들러 규약의 frame 인자가 없어도 동작한다"""
    shutdown, loop, _ = _signal()

    shutdown.handle(signal.SIGINT)

    assert len(loop.scheduled) == 1


# 등록 ------------------------------------------------------------------------


def test_install_registers_available_signals():
    """플랫폼에 있는 종료 시그널만 등록한다"""
    shutdown, _, _ = _signal()
    previous = {
        name: signal.getsignal(getattr(signal, name))
        for name in ("SIGTERM", "SIGINT", "SIGBREAK")
        if hasattr(signal, name)
    }

    try:
        installed = shutdown.install()

        assert "SIGINT" in installed
        assert "SIGTERM" in installed
        for name in installed:
            assert signal.getsignal(getattr(signal, name)) == shutdown.handle
    finally:
        for name, handler in previous.items():
            signal.signal(getattr(signal, name), handler)


@pytest.mark.skipif(
    not hasattr(signal, "SIGBREAK"), reason="SIGBREAK 은 Windows 전용"
)
def test_install_covers_sigbreak_on_windows():
    """Windows 의 Ctrl+Break 도 종료 신호로 다룬다"""
    shutdown, _, _ = _signal()
    previous = signal.getsignal(signal.SIGBREAK)

    try:
        assert "SIGBREAK" in shutdown.install()
    finally:
        signal.signal(signal.SIGBREAK, previous)
