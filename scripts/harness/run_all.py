#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""하니스 전체 실행

실행:
    PYTHONPATH=. .venv/Scripts/python.exe -m scripts.harness.run_all
    PYTHONPATH=. .venv/Scripts/python.exe -m scripts.harness.run_all --port 4000
    PYTHONPATH=. .venv/Scripts/python.exe -m scripts.harness.run_all --unit-only

단위 검증은 서버 없이 수행된다. 서버가 필요한 시나리오는 접속에 실패하면
건너뜀으로 기록하고 종료 코드에 영향을 주지 않는다. 서버를 대상으로 검증하려면
먼저 서버를 기동해야 한다.

서버 기동은 control_bash_process를 사용한다. nohup으로 띄우면 콘솔이 분리되어
kill -2가 전달되지 않고 graceful 종료가 불가능해진다.
"""

import argparse
import socket
import sys

from . import scenario_framing
from .client import DEFAULT_PORT
from .result import RunSummary, ScenarioResult


def _is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """포트가 열려 있는지 확인한다."""
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except OSError:
        return False


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="JSON 라인 프로토콜 하니스")
    parser.add_argument(
        "--host", default="127.0.0.1", help="서버 호스트 (기본 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help=f"서버 포트 (기본 {DEFAULT_PORT})"
    )
    parser.add_argument(
        "--unit-only",
        action="store_true",
        help="서버가 필요한 시나리오를 건너뛰고 단위 검증만 실행",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = RunSummary()

    print("=" * 60)
    print("JSON 라인 프로토콜 하니스")
    print("=" * 60)

    # 1. 단위 검증 - 서버 불필요
    print()
    print("[프레이밍 단위 검증]")
    framing_unit = ScenarioResult("framing (unit)")
    scenario_framing.run_unit(framing_unit)
    summary.add(framing_unit)

    # 2. 서버 대상 검증
    server_up = False
    if not args.unit_only:
        server_up = _is_port_open(args.host, args.port)

    print()
    print("[서버 왕복 검증]")
    framing_net = ScenarioResult("framing (server)")
    if args.unit_only:
        framing_net.skip("서버 왕복 수신", "--unit-only 지정")
    elif not server_up:
        framing_net.skip(
            "서버 왕복 수신",
            f"{args.host}:{args.port} 에 접속할 수 없다. 서버를 먼저 기동하십시오",
        )
    else:
        scenario_framing.run_roundtrip(framing_net, port=args.port)
    summary.add(framing_net)

    # 3. 프로토콜 전환 후 추가될 시나리오
    #    auth, room, action 시나리오는 server-json-protocol Task 9.3에서 작성한다.

    summary.report()
    return summary.exit_code


if __name__ == "__main__":
    sys.exit(main())
