# -*- coding: utf-8 -*-
"""공통 타입 정의"""

from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    from ..server.session import Session
    from ..server.telnet_session import TelnetSession

# 세션 타입 별칭 - WebSocket 세션과 Telnet 세션을 모두 지원
SessionType = Union['Session', 'TelnetSession']
