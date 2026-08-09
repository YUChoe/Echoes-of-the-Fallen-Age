#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JSON 라인 프레이밍 계층

TCP는 스트림이므로 하나의 읽기 단위가 라인 경계와 일치하지 않는다.
개행이 나타날 때까지 바이트를 누적하고 완성된 라인만 UTF-8로 디코딩해야
멀티바이트 문자가 청크 경계에서 쪼개져 손상되는 것을 막을 수 있다.

Telnet IAC 협상 바이트도 청크 경계에 걸칠 수 있으므로 필터를 상태 기반으로 만든다.

게이트웨이(Node)의 LineFramer와 같은 규약을 구현한다.
프로토콜 계약: docs/protocol/README.md
"""

from enum import Enum, auto

# Telnet 제어 바이트
IAC = 0xFF   # Interpret As Command
SE = 0xF0    # Subnegotiation End
SB = 0xFA    # Subnegotiation Begin
WILL = 0xFB
WONT = 0xFC
DO = 0xFD
DONT = 0xFE

_OPTION_COMMANDS = frozenset((WILL, WONT, DO, DONT))

LF = 0x0A
CR = 0x0D

# 라인 하나의 최대 길이. 초과 시 프로토콜 위반으로 간주한다.
DEFAULT_MAX_LINE_BYTES = 256 * 1024


class LineTooLongError(Exception):
    """라인 길이 상한을 초과했을 때 발생한다."""

    def __init__(self, size: int, limit: int) -> None:
        super().__init__(f"line exceeds limit: {size} > {limit}")
        self.size = size
        self.limit = limit


class _FilterState(Enum):
    """IAC 필터의 상태"""

    NORMAL = auto()          # 일반 데이터
    IAC_SEEN = auto()        # IAC를 봤고 다음 바이트를 기다린다
    OPTION_WAIT = auto()     # WILL/WONT/DO/DONT를 봤고 옵션 바이트를 기다린다
    SUBNEG = auto()          # SB 이후, IAC SE를 기다린다
    SUBNEG_IAC = auto()      # 서브협상 중 IAC를 봤다


class TelnetFilter:
    """Telnet IAC 시퀀스를 제거한다.

    협상은 연결 초기에만 발생하지만, 시퀀스가 청크 경계에 걸칠 수 있으므로
    상태를 유지한다. 협상이 끝난 뒤에는 사실상 통과 경로가 된다.
    """

    def __init__(self) -> None:
        self._state = _FilterState.NORMAL

    def filter(self, chunk: bytes) -> bytes:
        """IAC 시퀀스를 제거한 바이트를 반환한다."""
        out = bytearray()

        for byte in chunk:
            if self._state is _FilterState.NORMAL:
                if byte == IAC:
                    self._state = _FilterState.IAC_SEEN
                else:
                    out.append(byte)

            elif self._state is _FilterState.IAC_SEEN:
                if byte == IAC:
                    # IAC IAC 는 리터럴 0xFF 를 의미한다
                    out.append(IAC)
                    self._state = _FilterState.NORMAL
                elif byte in _OPTION_COMMANDS:
                    self._state = _FilterState.OPTION_WAIT
                elif byte == SB:
                    self._state = _FilterState.SUBNEG
                else:
                    # 2바이트 명령. 버린다
                    self._state = _FilterState.NORMAL

            elif self._state is _FilterState.OPTION_WAIT:
                # 옵션 바이트를 버리고 일반 상태로 복귀
                self._state = _FilterState.NORMAL

            elif self._state is _FilterState.SUBNEG:
                if byte == IAC:
                    self._state = _FilterState.SUBNEG_IAC

            elif self._state is _FilterState.SUBNEG_IAC:
                if byte == SE:
                    self._state = _FilterState.NORMAL
                elif byte == IAC:
                    # 서브협상 데이터 안의 리터럴 0xFF. 서브협상 자체를 버리므로 무시
                    self._state = _FilterState.SUBNEG
                else:
                    self._state = _FilterState.SUBNEG

        return bytes(out)

    @property
    def in_negotiation(self) -> bool:
        """협상 시퀀스 중간에 있는지"""
        return self._state is not _FilterState.NORMAL


class LineReader:
    """바이트를 누적하고 개행 경계에서 라인을 분리한다.

    완성된 라인만 UTF-8로 디코딩한다. 불완전한 잔여 바이트는 다음 청크와 결합한다.
    """

    def __init__(
        self,
        max_line_bytes: int = DEFAULT_MAX_LINE_BYTES,
        keep_empty: bool = False,
    ) -> None:
        self._buffer = bytearray()
        self._max_line_bytes = max_line_bytes
        self._keep_empty = keep_empty

    def feed(self, chunk: bytes) -> list[str]:
        """청크를 넣고 완성된 라인 목록을 반환한다.

        Raises:
            LineTooLongError: 잔여 버퍼가 상한을 초과한 경우
        """
        self._buffer.extend(chunk)
        lines: list[str] = []

        while True:
            index = self._buffer.find(LF)
            if index == -1:
                break

            raw = bytes(self._buffer[:index])
            del self._buffer[: index + 1]

            # 개행 직전의 CR 제거 (\r\n 방어)
            if raw.endswith(b"\r"):
                raw = raw[:-1]

            if raw or self._keep_empty:
                lines.append(raw.decode("utf-8", "replace"))

        if len(self._buffer) > self._max_line_bytes:
            raise LineTooLongError(len(self._buffer), self._max_line_bytes)

        return lines

    def pending(self) -> bytes:
        """아직 개행을 만나지 못한 잔여 바이트"""
        return bytes(self._buffer)

    def flush(self) -> str:
        """잔여 바이트를 라인으로 간주해 반환하고 버퍼를 비운다.

        연결이 종료됐는데 마지막 라인에 개행이 없는 경우에 사용한다.
        """
        raw = bytes(self._buffer)
        self._buffer.clear()
        if raw.endswith(b"\r"):
            raw = raw[:-1]
        return raw.decode("utf-8", "replace")
