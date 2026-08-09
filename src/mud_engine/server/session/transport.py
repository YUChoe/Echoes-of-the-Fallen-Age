# -*- coding: utf-8 -*-
"""Telnet 전송(Transport) 구성요소.

바이트 단위 입출력(reader/writer), 텍스트 전송, 한 줄 읽기, 에코 제어, 연결 종료를
담당한다. Telnet IAC 협상/필터링은 protocol 구성요소가 담당한다.
"""

import asyncio
import logging
from typing import Callable, Optional

from .util import short_session_id

logger = logging.getLogger(__name__)


class TelnetTransport:
    """Telnet 연결의 바이트 단위 입출력을 담당한다."""

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        session_id: str,
        on_activity: Optional[Callable[[], None]] = None,
    ) -> None:
        self.reader = reader
        self.writer = writer
        self.session_id = session_id
        self._on_activity = on_activity or (lambda: None)

    def is_closing(self) -> bool:
        return self.writer.is_closing()

    async def send_line(self, payload: bytes) -> bool:
        """개행으로 종결된 JSON 라인을 그대로 전송한다.

        페이로드를 가공하지 않는다. 개행 치환이나 프롬프트 개념은 라인 프로토콜에서
        라인 경계를 깨뜨리므로 존재하지 않는다.

        Args:
            payload: `serialization.encode_line()` 이 만든 바이트열

        Returns:
            전송 성공 여부
        """
        try:
            if self.writer.is_closing():
                logger.warning(
                    f"Telnet 세션 {short_session_id(self.session_id)}: 연결이 이미 닫혀있음"
                )
                return False

            self.writer.write(payload)
            await self.writer.drain()
            self._on_activity()
            return True
        except Exception as e:
            logger.error(f"Telnet 세션 {self.session_id} 라인 전송 실패: {e}")
            return False

    async def read_line(self, timeout: Optional[float] = None) -> Optional[str]:
        """클라이언트로부터 한 줄 읽기 (백스페이스/IAC 처리 포함)."""
        BACKSPACE = 0x08
        DELETE = 0x7F
        CR = 0x0D
        LF = 0x0A
        IAC = 0xFF

        buffer = bytearray()
        start_time = asyncio.get_event_loop().time() if timeout else None

        try:
            while True:
                if timeout and start_time:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed >= timeout:
                        logger.debug(f"Telnet 세션 {self.session_id} 읽기 타임아웃")
                        return None
                    remaining = timeout - elapsed
                else:
                    remaining = None

                try:
                    if remaining:
                        byte_data = await asyncio.wait_for(
                            self.reader.read(1), timeout=remaining
                        )
                    else:
                        byte_data = await self.reader.read(1)
                except asyncio.TimeoutError:
                    logger.debug(f"Telnet 세션 {self.session_id} 읽기 타임아웃")
                    return None

                if not byte_data:
                    logger.debug(f"Telnet 세션 {self.session_id}: 연결 종료 감지")
                    return None

                byte_val = byte_data[0]

                # Telnet IAC 명령어 처리
                if byte_val == IAC:
                    try:
                        cmd_byte = await asyncio.wait_for(
                            self.reader.read(1), timeout=0.1
                        )
                        if cmd_byte:
                            cmd = cmd_byte[0]
                            if cmd in (251, 252, 253, 254):
                                await asyncio.wait_for(self.reader.read(1), timeout=0.1)
                    except asyncio.TimeoutError:
                        pass
                    continue

                if byte_val in (BACKSPACE, DELETE):
                    if len(buffer) > 0:
                        buffer.pop()
                    continue

                if byte_val in (CR, LF):
                    if byte_val == CR:
                        try:
                            next_byte = await asyncio.wait_for(
                                self.reader.read(1), timeout=0.05
                            )
                            if next_byte and next_byte[0] != LF:
                                pass
                        except asyncio.TimeoutError:
                            pass
                    break

                if 32 <= byte_val <= 126 or byte_val >= 128:
                    buffer.append(byte_val)

            try:
                decoded_line = buffer.decode("utf-8", errors="ignore").strip()
                self._on_activity()
                return decoded_line
            except Exception as e:
                logger.warning(f"Telnet 세션 {self.session_id} 디코딩 오류: {e}")
                return ""
        except Exception as e:
            logger.error(f"Telnet 세션 {self.session_id} 읽기 오류: {e}")
            return None

    async def close(self, message: str = "Connection closed") -> None:
        """Telnet 연결 종료.

        종료 사유를 소켓에 쓰지 않는다. 자유 텍스트는 라인 프로토콜의 계약을
        위반하므로, 사유를 알려야 하는 경우 호출자가 먼저 구조화 메시지를 보낸다.
        """
        try:
            if not self.writer.is_closing():
                self.writer.close()
                await self.writer.wait_closed()
                logger.info(
                    f"Telnet 세션 {short_session_id(self.session_id)} 연결 종료: {message}"
                )
        except Exception as e:
            logger.error(
                f"Telnet 세션 {short_session_id(self.session_id)} 종료 중 오류: {e}"
            )
