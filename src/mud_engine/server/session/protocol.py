# -*- coding: utf-8 -*-
"""Telnet 프로토콜(IAC) 구성요소.

Telnet 옵션 협상(IAC negotiation)과 명령어 시퀀스 필터링을 담당한다.
바이트 입출력 자체는 Transport가 담당한다.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)

# Telnet 제어 바이트
IAC = 255   # Interpret As Command
WILL = 251
WONT = 252
DO = 253
DONT = 254
ECHO = 1
SUPPRESS_GO_AHEAD = 3
LINEMODE = 34


class TelnetProtocol:
    """Telnet 옵션 협상 및 IAC 시퀀스 필터링을 담당한다."""

    def __init__(self, writer: asyncio.StreamWriter) -> None:
        self.writer = writer

    async def initialize(self) -> None:
        """Telnet 프로토콜 초기화 및 옵션 협상.

        WILL SUPPRESS_GO_AHEAD, WONT ECHO(클라이언트 에코), DONT LINEMODE 전송.
        """
        try:
            self.writer.write(bytes([IAC, WILL, SUPPRESS_GO_AHEAD]))
            self.writer.write(bytes([IAC, WONT, ECHO]))
            self.writer.write(bytes([IAC, DONT, LINEMODE]))
            await self.writer.drain()
        except Exception as e:
            logger.debug(f"Telnet 프로토콜 협상 오류 (무시됨): {e}")

    @staticmethod
    def filter_commands(data: bytes) -> bytes:
        """Telnet IAC 명령어 시퀀스를 필터링하여 순수 데이터만 반환한다."""
        result = bytearray()
        i = 0
        while i < len(data):
            if data[i] == IAC:
                if i + 1 < len(data):
                    cmd = data[i + 1]
                    if cmd in (DO, DONT, WILL, WONT):
                        if i + 2 < len(data):
                            i += 3
                            continue
                    elif cmd == IAC:
                        # IAC IAC는 실제 0xFF 바이트를 의미
                        result.append(IAC)
                        i += 2
                        continue
                    else:
                        i += 2
                        continue
                i += 1
            else:
                result.append(data[i])
                i += 1
        return bytes(result)
