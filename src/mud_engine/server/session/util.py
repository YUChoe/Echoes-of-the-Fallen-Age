# -*- coding: utf-8 -*-
"""세션 계층 공용 유틸리티."""


def short_session_id(session_id: str) -> str:
    """세션 ID의 짧은 표기(마지막 하이픈 세그먼트)를 반환한다.

    로그 가독성을 위해 UUID의 마지막 부분만 표시한다.
    """
    return session_id.split("-")[-1] if "-" in session_id else session_id
