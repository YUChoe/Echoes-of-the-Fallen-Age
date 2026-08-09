#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JSON 라인 프로토콜 검증 하니스

Godot 클라이언트 없이 서버를 검증한다. 프로토콜 전환 구간에서 유일한 검증 수단이다.

실행:
    PYTHONPATH=. .venv/Scripts/python.exe -m scripts.harness.run_all

프로토콜 계약: docs/protocol/
"""

from .client import HarnessClient, HarnessError, strip_ansi
from .framing import LineReader, LineTooLongError, TelnetFilter

__all__ = [
    "HarnessClient",
    "HarnessError",
    "LineReader",
    "LineTooLongError",
    "TelnetFilter",
    "strip_ansi",
]
