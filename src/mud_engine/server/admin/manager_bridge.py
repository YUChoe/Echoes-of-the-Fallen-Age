# -*- coding: utf-8 -*-
"""AdminManager 와 어드민 채널 사이의 과도기 어댑터

`AdminManager` 는 게임 채널의 `TelnetSession` 을 받아 완성된 한국어 문장을
보내도록 만들어져 있다. 어드민 채널은 `admin_action_result` 로 구조화 응답을
보내므로 두 규약이 맞지 않는다.

`AdminManager` 를 어드민 채널에 맞게 고치는 것은 Task 7.6 이다. 그때까지
이 어댑터가 세션 인터페이스를 흉내내고, 매니저가 보내려던 문장을 모아
액션 결과의 `notices` 로 전달한다. Task 7.6 에서 함께 사라진다.
"""

import logging
from typing import Any, Optional

from .admin_session import AdminSession

logger = logging.getLogger(__name__)


class AdminManagerSession:
    """`AdminManager` 가 기대하는 세션 인터페이스를 어드민 세션 위에 흉내낸다.

    매니저가 쓰는 것은 `session_id`, `player`, `send_admin_notice` 셋뿐이다.
    """

    def __init__(self, session: AdminSession) -> None:
        self._session = session
        self.notices: list[dict[str, str]] = []

    @property
    def session_id(self) -> str:
        """어드민 세션 id. 매니저가 이벤트 출처로 쓴다."""
        return self._session.session_id

    @property
    def player(self) -> Optional[Any]:
        """게임 플레이어가 아니므로 항상 None.

        `AdminManager` 는 모든 사용처에서 None 을 처리한다. 실행 주체는
        `queries.py` 와 같은 방식으로 감사 로그에 남긴다.
        """
        return None

    async def send_admin_notice(self, text: str, severity: str = "info") -> bool:
        """매니저가 보내려던 문장을 모은다. 소켓으로 내보내지 않는다."""
        self.notices.append({"severity": severity, "text": text})
        return True

    @property
    def failed(self) -> bool:
        """매니저가 오류 문장을 남겼는지"""
        return any(notice["severity"] == "error" for notice in self.notices)
