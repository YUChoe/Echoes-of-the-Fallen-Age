#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""서버를 띄우고 정상 종료까지 관리하는 런처

MSYS 의 `kill` 은 네이티브 Windows 프로세스에 시그널을 전달하지 못한다.
`taskkill` 도 창 없는 콘솔 앱에는 WM_CLOSE 를 전달할 수 없어 `/F` 강제 종료만
가능하다. 강제 종료는 종료 절차를 건너뛰므로 WAL 정리와 세션 종료 알림이
빠진다.

이 런처는 서버를 새 프로세스 그룹으로 띄우고 `CTRL_BREAK_EVENT` 를 보내
정상 종료를 유도한다. 서버는 이를 SIGBREAK 로 받는다.

실행:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/run_server.py
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/run_server.py --seconds 30

`--seconds` 를 주면 그 시간 뒤에 정상 종료를 요청한다. 검증 절차에서
서버를 띄웠다 내리는 데 쓴다. 생략하면 Ctrl+Break 를 기다린다.
"""

import argparse
import os
import signal
import subprocess
import sys
import time

# 정상 종료를 기다리는 시간. 넘으면 강제 종료한다
GRACEFUL_TIMEOUT = 20.0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MUD 서버 런처")
    parser.add_argument(
        "--seconds",
        type=float,
        default=None,
        help="이 시간 뒤에 정상 종료를 요청한다. 생략하면 Ctrl+Break 를 기다린다",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    if sys.platform != "win32":
        print("이 런처는 Windows 전용이다. 다른 플랫폼에서는 kill -2 가 동작한다")
        return 2

    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env["PYTHONPATH"] = "."

    print("서버 기동 중...")
    process = subprocess.Popen(
        [sys.executable, "-m", "src.mud_engine.main"],
        env=env,
        # 새 프로세스 그룹이어야 CTRL_BREAK_EVENT 를 보낼 수 있다
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )

    try:
        if args.seconds is None:
            print(f"PID {process.pid}. Ctrl+Break 로 정상 종료한다")
            process.wait()
            return process.returncode

        print(f"PID {process.pid}. {args.seconds}초 뒤 정상 종료를 요청한다")
        try:
            return process.wait(timeout=args.seconds)
        except subprocess.TimeoutExpired:
            pass
    except KeyboardInterrupt:
        print("\n런처가 Ctrl+C 를 받았다. 서버에 정상 종료를 요청한다")

    return _shutdown(process)


def _shutdown(process: subprocess.Popen) -> int:
    """서버에 정상 종료를 요청하고 기다린다."""
    print("CTRL_BREAK_EVENT 전송")
    process.send_signal(signal.CTRL_BREAK_EVENT)

    started = time.monotonic()

    try:
        code = process.wait(timeout=GRACEFUL_TIMEOUT)
    except subprocess.TimeoutExpired:
        print(f"{GRACEFUL_TIMEOUT}초 안에 종료되지 않아 강제 종료한다")
        process.kill()
        process.wait()
        return 1

    print(f"정상 종료 완료 ({time.monotonic() - started:.1f}초, 종료 코드 {code})")
    return code


if __name__ == "__main__":
    sys.exit(main())
