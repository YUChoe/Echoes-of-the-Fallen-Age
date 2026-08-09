# -*- coding: utf-8 -*-
"""액션 핸들러

verb 카테고리별로 파일을 나눈다. 각 모듈이 `handlers()` 를 제공하고
`build_handlers()` 가 이를 모아 디스패처에 등록할 목록을 만든다.

재export를 두지 않는다. 핸들러가 게임 엔진을 참조하므로 즉시 임포트하면
순환이 발생한다.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..base import ActionHandler


def build_handlers() -> list["ActionHandler"]:
    """등록할 핸들러 전체 목록을 만든다.

    카테고리 모듈을 여기서 임포트한다. 모듈 최상단에서 임포트하면
    `commands.actions` 를 참조하는 다른 모듈과 순환이 생긴다.

    Returns:
        핸들러 인스턴스 목록
    """
    from . import combat, containers, dialogue, inspection, items, movement, state

    handlers: list["ActionHandler"] = []
    handlers.extend(movement.handlers())
    handlers.extend(inspection.handlers())
    handlers.extend(items.handlers())
    handlers.extend(containers.handlers())
    handlers.extend(combat.handlers())
    handlers.extend(dialogue.handlers())
    handlers.extend(state.handlers())

    return handlers
