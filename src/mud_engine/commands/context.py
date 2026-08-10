# -*- coding: utf-8 -*-
"""액션 컨텍스트와 결과

디스패처와 핸들러가 주고받는 자료구조를 정의한다. 완성된 문장을 담지 않는다.
번역 키와 치환 파라미터만 전달하며 문장 조립은 클라이언트가 수행한다.

프로토콜 계약: docs/protocol/client-to-server.md, docs/protocol/entities.md
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

from ..core.types import SessionType

if TYPE_CHECKING:
    from ..core.game_engine import GameEngine


class ActionResultType(Enum):
    """액션 처리 결과의 종류"""

    # 액션이 수행되었다
    SUCCESS = "success"
    # 서버 내부 오류로 수행하지 못했다
    ERROR = "error"
    # 규칙에 따라 거절했다. 오류가 아니다
    REJECTED = "rejected"


class BroadcastScope(Enum):
    """브로드캐스트 범위"""

    # 현재 방
    ROOM = "room"
    # 접속한 모든 플레이어
    ALL = "all"


@dataclass
class BroadcastSpec:
    """주변에 알릴 내용

    발신자 언어로 만든 문장을 뿌리지 않는다. 키를 전달하면 수신 클라이언트가
    각자의 언어로 번역하므로 언어 오염이 구조적으로 사라진다.
    """

    message_key: str
    params: dict[str, Any] = field(default_factory=dict)
    scope: BroadcastScope = BroadcastScope.ROOM
    # 로그 채널 분류 (combat/movement/item/social/system/dialogue)
    category: str = "system"
    # 발신자에게는 보내지 않는다
    exclude_actor: bool = True


@dataclass
class ActionContext:
    """액션 한 건의 처리에 필요한 입력

    Attributes:
        session: 액션을 보낸 세션
        game_engine: 게임 엔진
        verb: 액션 종류
        target: 대상 엔티티 uuid. 대상이 없는 verb 는 None
        params: verb 별 부가 인자
        seq: 요청 번호. 응답에 그대로 실어 클라이언트가 대응시킨다
        entity: 디스패처가 target 을 해석한 결과. 해석 대상이 없으면 None
    """

    session: SessionType
    game_engine: "GameEngine"
    verb: str
    target: Optional[str] = None
    params: dict[str, Any] = field(default_factory=dict)
    seq: Optional[int] = None
    entity: Optional[Any] = None

    @property
    def player_id(self) -> Optional[str]:
        """액션을 보낸 플레이어 id"""
        return self.session.player.id if self.session.player else None

    @property
    def room_id(self) -> Optional[str]:
        """액션이 발생한 방 id"""
        return getattr(self.session, "current_room_id", None)


@dataclass
class ActionResult:
    """액션 처리 결과

    Attributes:
        result_type: 처리 결과 종류
        message_key: 사용자에게 표시할 번역 키
        params: 번역 치환 파라미터. 값이 언어별 dict 이면 클라이언트가 고른다
        rejection_code: REJECTED 인 경우의 사유 코드
        broadcast: 주변에 알릴 내용
        data: 응답에 실을 부가 데이터
        message: 개발자용 영문 사유. 사용자에게 표시하지 않는다.
            REJECTED 는 서버 로그에만 남고, ERROR 는 `error.detail` 로 나간다.
            SUCCESS 에 쓰이는 경우는 Lua 스크립트가 만든 대사뿐이며
            그 전환은 Task 10 에서 다룬다
    """

    result_type: ActionResultType
    message_key: Optional[str] = None
    params: dict[str, Any] = field(default_factory=dict)
    rejection_code: Optional[str] = None
    broadcast: Optional[BroadcastSpec] = None
    data: dict[str, Any] = field(default_factory=dict)
    message: Optional[str] = None

    @property
    def succeeded(self) -> bool:
        """액션이 수행되었는지"""
        return self.result_type is ActionResultType.SUCCESS


def success(
    message_key: Optional[str] = None,
    params: Optional[dict[str, Any]] = None,
    broadcast: Optional[BroadcastSpec] = None,
    data: Optional[dict[str, Any]] = None,
    message: Optional[str] = None,
) -> ActionResult:
    """성공 결과를 만든다."""
    return ActionResult(
        result_type=ActionResultType.SUCCESS,
        message_key=message_key,
        params=params or {},
        broadcast=broadcast,
        data=data or {},
        message=message,
    )


def rejected(
    rejection_code: str,
    message_key: Optional[str] = None,
    params: Optional[dict[str, Any]] = None,
    message: Optional[str] = None,
) -> ActionResult:
    """거절 결과를 만든다.

    Args:
        rejection_code: entities.md 에 정의된 사유 코드
        message_key: 사용자에게 표시할 번역 키
        params: 번역 치환 파라미터
        message: 개발자용 영문 사유. 서버 로그에만 남는다
    """
    return ActionResult(
        result_type=ActionResultType.REJECTED,
        message_key=message_key,
        params=params or {},
        rejection_code=rejection_code,
        message=message,
    )


def error(
    message_key: Optional[str] = None,
    message: Optional[str] = None,
) -> ActionResult:
    """서버 내부 오류 결과를 만든다."""
    return ActionResult(
        result_type=ActionResultType.ERROR,
        message_key=message_key,
        message=message,
    )
