#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JSON 라인 하니스 클라이언트

Godot 클라이언트 없이 서버를 검증하기 위한 도구다. 게이트웨이를 거치지 않고
서버의 TCP 포트에 직접 붙어 개행 구분 JSON 라인을 주고받는다.

프로토콜 전환 구간(server-json-protocol Task 3~4)에서는 이 하니스가 유일한
검증 수단이다. 전환 전에도 텍스트 라인을 그대로 수신할 수 있어 기준선 확보에 쓴다.

프로토콜 계약: docs/protocol/
"""

import json
import re
import socket
import sys
import time
from typing import Any

from . import coverage
from .framing import LineReader, TelnetFilter

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4000
DEFAULT_ADMIN_PORT = 4001

# 응답 대기 기본값. 로컬 접속 기준
DEFAULT_WAIT_MS = 500
DEFAULT_CONNECT_TIMEOUT = 5.0

_ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def strip_ansi(text: str) -> str:
    """ANSI 이스케이프 시퀀스를 제거한다.

    전환 완료 후 서버는 ANSI를 보내지 않는다. 전환 전 기준선 확보에만 필요하다.
    """
    return _ANSI_PATTERN.sub("", text)


class HarnessError(Exception):
    """하니스 동작 실패"""


class HarnessClient:
    """라인 단위로 서버와 통신하는 검증 클라이언트

    사용 예:
        with HarnessClient() as client:
            client.connect()
            client.send_json({"type": "login", "username": "u", "password": "p"})
            result = client.wait_for("login_result")
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        verbose: bool = True,
        filter_telnet: bool = True,
    ) -> None:
        self._host = host
        self._port = port
        self._verbose = verbose
        self._sock: socket.socket | None = None
        self._filter = TelnetFilter() if filter_telnet else None
        self._reader = LineReader()
        self._seq = 0
        # 아직 소비되지 않은 수신 라인
        self._inbox: list[str] = []

    # 연결 관리 --------------------------------------------------------------

    def connect(self, timeout: float = DEFAULT_CONNECT_TIMEOUT) -> None:
        """서버에 접속한다."""
        self._log(f"연결 시도: {self._host}:{self._port}")
        try:
            self._sock = socket.create_connection((self._host, self._port), timeout)
        except OSError as exc:
            raise HarnessError(f"접속 실패 {self._host}:{self._port} - {exc}") from exc
        self._sock.settimeout(0.2)
        self._log("연결 성공")

    def close(self) -> None:
        """연결을 종료한다."""
        if self._sock is None:
            return
        try:
            self._sock.close()
        except OSError:
            pass
        finally:
            self._sock = None
            self._log("연결 종료")

    def __enter__(self) -> "HarnessClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # 송신 ------------------------------------------------------------------

    def next_seq(self) -> int:
        """다음 요청 번호를 발급한다."""
        self._seq += 1
        return self._seq

    def send_line(self, text: str) -> None:
        """원시 라인을 전송한다. 개행을 붙인다."""
        if self._sock is None:
            raise HarnessError("연결되지 않음")
        payload = (text + "\n").encode("utf-8")
        self._log(f">>> {text}")
        self._sock.sendall(payload)

    def send_raw(self, data: bytes) -> None:
        """바이트를 그대로 전송한다. 프레이밍 시험에 사용한다."""
        if self._sock is None:
            raise HarnessError("연결되지 않음")
        self._log(f">>> (raw {len(data)} bytes)")
        self._sock.sendall(data)

    def send_json(self, message: dict[str, Any], with_seq: bool = True) -> int | None:
        """JSON 메시지를 한 줄로 전송한다.

        Returns:
            부여된 seq. with_seq가 False면 None
        """
        payload = dict(message)
        seq: int | None = None
        if with_seq and "seq" not in payload:
            seq = self.next_seq()
            payload["seq"] = seq
        elif "seq" in payload:
            seq = payload["seq"]

        recorder = coverage.active()
        if recorder is not None:
            recorder.record_sent(payload)

        # ensure_ascii=False 로 한국어를 그대로 보내 왕복을 검증한다
        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        self.send_line(line)
        return seq

    # 수신 ------------------------------------------------------------------

    def _pump(self) -> None:
        """소켓에서 읽어 라인 버퍼를 채운다. 블로킹하지 않는다."""
        if self._sock is None:
            raise HarnessError("연결되지 않음")
        try:
            chunk = self._sock.recv(8192)
        except socket.timeout:
            return
        except OSError as exc:
            raise HarnessError(f"수신 실패: {exc}") from exc

        if not chunk:
            return

        if self._filter is not None:
            chunk = self._filter.filter(chunk)
        if chunk:
            self._inbox.extend(self._reader.feed(chunk))

    def read_lines(self, wait_ms: int = DEFAULT_WAIT_MS) -> list[str]:
        """주어진 시간 동안 수신한 라인을 모아 반환한다."""
        deadline = time.monotonic() + wait_ms / 1000.0
        while time.monotonic() < deadline:
            self._pump()
        lines = self._inbox
        self._inbox = []
        for line in lines:
            self._log(f"<<< {_preview(line)}")
        return lines

    def read_json(self, wait_ms: int = DEFAULT_WAIT_MS) -> list[dict[str, Any]]:
        """수신 라인을 JSON으로 파싱해 반환한다.

        파싱할 수 없는 라인은 건너뛴다. 전환 전 텍스트 프로토콜에서는
        대부분의 라인이 파싱되지 않는다.
        """
        messages: list[dict[str, Any]] = []
        for line in self.read_lines(wait_ms):
            parsed = _try_parse(line)
            if parsed is not None:
                messages.append(parsed)
        return messages

    def wait_for(
        self,
        message_type: str,
        seq: int | None = None,
        timeout_ms: int = 3000,
    ) -> dict[str, Any]:
        """특정 타입의 메시지를 기다린다.

        Args:
            message_type: 기다릴 `type` 값
            seq: 지정하면 해당 요청 번호와 일치하는 응답만 받아들인다
            timeout_ms: 제한 시간

        Raises:
            HarnessError: 제한 시간 내에 수신하지 못한 경우
        """
        deadline = time.monotonic() + timeout_ms / 1000.0
        seen: list[str] = []

        while time.monotonic() < deadline:
            self._pump()
            remaining = self._inbox
            self._inbox = []
            for line in remaining:
                parsed = _try_parse(line)
                if parsed is None:
                    seen.append(f"(non-json) {_preview(line)}")
                    continue
                got_type = parsed.get("type")
                seen.append(str(got_type))
                if got_type != message_type:
                    continue
                if seq is not None and parsed.get("seq") != seq:
                    continue
                self._log(f"<<< {message_type} 수신")
                return parsed

        raise HarnessError(
            f"'{message_type}' 대기 시간 초과 ({timeout_ms}ms). 수신한 타입: {seen}"
        )

    # 내부 ------------------------------------------------------------------

    def _log(self, text: str) -> None:
        if self._verbose:
            print(text, flush=True)


def _try_parse(line: str) -> dict[str, Any] | None:
    """라인을 JSON 오브젝트로 파싱한다. 실패하면 None.

    파싱에 성공한 메시지는 커버리지에 기록한다. 수신 경로가 이 함수 하나로
    모이므로 여기서 한 번만 기록하면 된다.
    """
    stripped = line.strip()
    if not stripped or stripped[0] != "{":
        return None
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None

    recorder = coverage.active()
    if recorder is not None:
        recorder.record_received(parsed)

    return parsed


def _preview(text: str, limit: int = 120) -> str:
    """로그 출력용으로 라인을 줄인다."""
    clean = strip_ansi(text).replace("\r", "")
    if len(clean) <= limit:
        return clean
    return clean[:limit] + f"... ({len(clean)}자)"


def main() -> int:
    """단독 실행 시 접속과 초기 수신만 확인한다."""
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    try:
        with HarnessClient(port=port) as client:
            client.connect()
            lines = client.read_lines(800)
            if not lines:
                print("판정: 실패 - 수신 없음")
                return 1
            print(f"판정: 성공 - {len(lines)}줄 수신")
            return 0
    except HarnessError as exc:
        print(f"판정: 실패 - {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
