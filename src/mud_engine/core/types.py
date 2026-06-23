# -*- coding: utf-8 -*-
"""공통 타입 정의"""

from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from ..server.telnet_session import TelnetSession

# 세션 타입 별칭 - 현재 런타임은 Telnet 세션만 사용한다.
# (과거 WebSocket 세션은 제거되었으며, 깨진 ..server.session 임포트도 정리함)
SessionType: TypeAlias = "TelnetSession"
