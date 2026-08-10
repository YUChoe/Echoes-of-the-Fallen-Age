# -*- coding: utf-8 -*-
"""액션 핸들러 기본 클래스"""

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .context import ActionContext, ActionResult

logger = logging.getLogger(__name__)


class ActionHandler(ABC):
    """액션 핸들러 기본 클래스

    구조화 액션 하나를 처리한다. 문자열 파싱과 별칭이 없으므로 이름, 별칭,
    사용법, 도움말을 갖지 않는다. 클라이언트가 엔티티 속성으로 버튼을 추론하고
    서버는 적용 불가한 요청을 거절한다.
    """

    # 이 핸들러가 처리하는 verb
    verb: str = ""

    # 대상 uuid 가 필요한 verb 인지. 디스패처가 검사한다
    requires_target: bool = False

    # 전투 중에만 허용되는 verb 인지
    combat_only: bool = False

    # 전투 중에 금지되는 verb 인지
    forbidden_in_combat: bool = False

    # 관리자 전용 verb 인지
    admin_only: bool = False

    @abstractmethod
    async def handle(self, ctx: "ActionContext") -> "ActionResult":
        """액션을 처리한다.

        Args:
            ctx: 액션 컨텍스트. 대상 해석은 디스패처가 이미 수행했다

        Returns:
            처리 결과
        """
        raise NotImplementedError
