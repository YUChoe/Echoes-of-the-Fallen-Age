# -*- coding: utf-8 -*-
"""
MUD 엔진에서 사용될 커스텀 예외 클래스를 정의합니다.
"""

class MudEngineError(Exception):
    """MUD 엔진의 기본이 되는 예외 클래스입니다."""
    pass

class AuthenticationError(MudEngineError):
    """인증 과정에서 발생하는 예외입니다."""
    pass

class CommandError(MudEngineError):
    """명령어 처리 중 발생하는 예외입니다."""
    pass

class WorldError(MudEngineError):
    """게임 세계 데이터 관련 예외입니다."""
    pass

class DatabaseError(MudEngineError):
    """데이터베이스 연산 중 발생하는 예외입니다."""
    pass


class AdminOperationError(MudEngineError):
    """어드민 작업이 수행되지 못한 경우의 예외입니다.

    사유 코드를 담아 어드민 채널이 `admin_rejected` 로 그대로 옮길 수 있게 한다.
    매니저가 완성된 문장을 만들어 세션으로 보내던 방식을 대체한다.

    Attributes:
        reason_code: docs/protocol/entities.md 와 admin.md 의 사유 코드
        detail: 개발자용 영문 설명. 사용자에게 표시하지 않는다
    """

    def __init__(self, reason_code: str, detail: str) -> None:
        super().__init__(detail)
        self.reason_code = reason_code
        self.detail = detail
