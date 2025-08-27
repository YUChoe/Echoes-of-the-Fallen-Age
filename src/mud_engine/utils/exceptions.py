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
