# -*- coding: utf-8 -*-
"""어드민 채널 세션

프레이밍 규약(개행 구분 JSON 라인, UTF-8)은 게임 채널과 같지만 Telnet IAC 협상은
하지 않는다. 어드민 채널에 사람이 터미널로 붙는 경우를 지원하지 않으므로 협상이
불필요하다.

프로토콜 계약: docs/protocol/admin.md
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from ..serialization import MAX_LINE_BYTES, admin_rejected, encode_line, error
from ..session.util import short_session_id
from .auth import AdminPrincipal

logger = logging.getLogger(__name__)


class AdminSession:
    """어드민 채널 연결 하나를 관리한다."""

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        session_id: Optional[str] = None,
    ) -> None:
        self.session_id: str = session_id or str(uuid.uuid4())
        self.reader = reader
        self.writer = writer
        self.principal: Optional[AdminPrincipal] = None
        self.created_at = datetime.now()
        self.last_activity = datetime.now()

        peer = writer.get_extra_info("peername")
        self.ip_address: str = peer[0] if peer else "unknown"

    @property
    def short_id(self) -> str:
        """로그용 짧은 세션 id"""
        return short_session_id(self.session_id)

    @property
    def is_authenticated(self) -> bool:
        """인증됐고 만료되지 않았는지"""
        return self.principal is not None and not self.principal.is_expired()

    async def send_message(self, message: dict[str, Any]) -> bool:
        """구조화 메시지를 JSON 라인으로 전송한다.

        Args:
            message: `type` 을 가진 메시지 딕셔너리

        Returns:
            전송 성공 여부
        """
        try:
            if self.writer.is_closing():
                logger.warning(f"어드민 세션 {self.short_id}: 연결이 이미 닫혀있음")
                return False

            self.writer.write(encode_line(message))
            await self.writer.drain()
            self.last_activity = datetime.now()
            return True
        except ValueError as e:
            logger.error(f"어드민 세션 {self.short_id} 인코딩 실패: {e}")
            return False
        except Exception as e:
            logger.error(f"어드민 세션 {self.short_id} 메시지 전송 실패: {e}")
            return False

    async def send_error(
        self, reason_code: str, detail: str = "", seq: Optional[int] = None
    ) -> bool:
        """프로토콜 수준 오류를 알린다.

        JSON 파싱 실패, 필수 필드 누락처럼 계약 위반에 쓴다. 어드민 요청의
        거절에는 `send_rejected` 를 쓴다.
        """
        return await self.send_message(error(reason_code, detail, seq))

    async def send_rejected(
        self,
        action: str,
        reason_code: str,
        detail: str = "",
        seq: Optional[int] = None,
        references: Optional[list[dict[str, Any]]] = None,
    ) -> bool:
        """어드민 요청 거절을 알린다.

        Args:
            references: `REFERENCED` 거절에서 삭제를 막은 참조 목록
        """
        return await self.send_message(
            admin_rejected(seq, action, reason_code, detail, references)
        )

    async def read_message(
        self, timeout: Optional[float] = None
    ) -> Optional[dict[str, Any]]:
        """유효한 JSON 메시지 한 건을 읽는다.

        라인 → UTF-8 디코딩 → json.loads → 봉투 검증 순서로 처리한다. 계약을
        위반한 라인은 `error` 를 보내고 다음 라인을 계속 읽으므로, None 은 연결
        종료 또는 타임아웃만을 뜻한다.

        Args:
            timeout: 라인 하나를 기다리는 시간 (초)

        Returns:
            검증을 통과한 메시지. 연결이 끝났거나 타임아웃이면 None
        """
        while True:
            line = await self._read_line(timeout)

            if line is None:
                return None

            if not line.strip():
                continue

            try:
                message = json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning(f"어드민 세션 {self.short_id} JSON 파싱 실패: {e}")
                await self.send_error("MALFORMED_MESSAGE", "line is not valid JSON")
                continue

            if not isinstance(message, dict):
                await self.send_error(
                    "MALFORMED_MESSAGE", "message must be a JSON object"
                )
                continue

            if not isinstance(message.get("type"), str):
                await self.send_error("MALFORMED_MESSAGE", "missing type field")
                continue

            return message

    async def _read_line(self, timeout: Optional[float]) -> Optional[str]:
        """개행까지 한 줄을 읽어 UTF-8 로 디코딩한다.

        게임 채널과 달리 바이트 단위 IAC 처리와 백스페이스 편집이 없다.
        """
        try:
            if timeout is not None:
                raw = await asyncio.wait_for(
                    self.reader.readuntil(b"\n"), timeout=timeout
                )
            else:
                raw = await self.reader.readuntil(b"\n")
        except asyncio.TimeoutError:
            logger.debug(f"어드민 세션 {self.short_id} 읽기 타임아웃")
            return None
        except asyncio.IncompleteReadError:
            logger.debug(f"어드민 세션 {self.short_id}: 연결 종료 감지")
            return None
        except asyncio.LimitOverrunError:
            logger.warning(f"어드민 세션 {self.short_id}: 라인 길이 초과")
            await self.send_error(
                "MALFORMED_MESSAGE", f"line exceeds {MAX_LINE_BYTES} bytes"
            )
            return None
        except Exception as e:
            logger.error(f"어드민 세션 {self.short_id} 읽기 오류: {e}")
            return None

        self.last_activity = datetime.now()
        return raw.decode("utf-8", errors="replace")

    async def close(self, reason: str = "connection closed") -> None:
        """연결을 종료한다.

        종료 사유를 소켓에 쓰지 않는다. 사유를 알려야 하면 호출자가 먼저
        구조화 메시지를 보낸다.
        """
        try:
            if not self.writer.is_closing():
                self.writer.close()
                await self.writer.wait_closed()
        except Exception as e:
            logger.error(f"어드민 세션 {self.short_id} 종료 중 오류: {e}")
        finally:
            logger.info(f"어드민 세션 {self.short_id} 연결 종료: {reason}")
