#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""세션/명령어 리팩토링용 회귀 기준선 캡처 스크립트 (socket 기반, Python 3.13+).

대표 시나리오(login/look/stats/inventory/help/이동/알 수 없는 명령어)를 실행하고
ANSI 코드를 제거한 출력을 telnet/baseline_session_refactor.txt 에 저장한다.
telnetlib는 Python 3.13에서 제거되어 raw socket을 사용한다.
"""

import re
import socket
import sys
import time

HOST = "127.0.0.1"
PORT = 4000
USER = "player5426"
PASSWORD = "test1234"
OUT_PATH = "telnet/baseline_session_refactor.txt"

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def filter_iac(data: bytes) -> bytes:
    """Telnet IAC(0xFF) 명령 시퀀스를 제거한다."""
    out = bytearray()
    i = 0
    while i < len(data):
        b = data[i]
        if b == 0xFF:  # IAC
            cmd = data[i + 1] if i + 1 < len(data) else 0
            if cmd in (251, 252, 253, 254):  # WILL/WONT/DO/DONT + option
                i += 3
                continue
            i += 2
            continue
        out.append(b)
        i += 1
    return bytes(out)


def clean(text: str) -> str:
    return ANSI_RE.sub("", text)


def read_all(sock: socket.socket, wait_ms: int) -> str:
    """waitMs 동안 도착하는 데이터를 모두 읽는다."""
    sock.settimeout(wait_ms / 1000.0)
    chunks = bytearray()
    deadline = time.time() + (wait_ms / 1000.0)
    while time.time() < deadline:
        try:
            data = sock.recv(4096)
            if not data:
                break
            chunks.extend(data)
        except socket.timeout:
            break
    return clean(filter_iac(bytes(chunks)).decode("utf-8", errors="ignore"))


def send(sock: socket.socket, cmd: str) -> None:
    sock.sendall((cmd + "\n").encode("utf-8"))


def main() -> int:
    lines: list[str] = []

    def record(label: str, data: str) -> None:
        lines.append(f"===== {label} =====")
        lines.append(data.strip())
        lines.append("")
        print(f">>> {label}: {len(data.strip())} chars")

    try:
        sock = socket.create_connection((HOST, PORT), timeout=5)
    except OSError as e:
        print(f"연결 실패: {e}")
        return 1

    try:
        record("welcome", read_all(sock, 800))
        send(sock, "1")
        record("login_menu", read_all(sock, 500))
        send(sock, USER)
        record("username_prompt", read_all(sock, 500))
        send(sock, PASSWORD)
        record("login_result", read_all(sock, 800))

        for cmd, wait in [
            ("look", 600),
            ("stats", 600),
            ("inventory", 600),
            ("help", 600),
            ("xyzzy", 500),
            ("east", 600),
            ("look", 600),
            ("west", 600),
        ]:
            send(sock, cmd)
            record(f"cmd:{cmd}", read_all(sock, wait))

        send(sock, "quit")
        record("quit", read_all(sock, 500))
    finally:
        sock.close()

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n기준선 저장 완료: {OUT_PATH} ({len(lines)} 줄)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
