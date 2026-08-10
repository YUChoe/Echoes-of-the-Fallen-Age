# -*- coding: utf-8 -*-
"""어드민 채널 메시지 봉투

어드민 채널은 사람이 직접 읽는 UI 가 아니라 도구를 경유하므로 번역 키를 쓰지
않는다. 거절 사유는 `detail` 에 영문으로 담고 Godot 어드민 패널이 코드별 안내
문구를 자체 보유한다.

프로토콜 계약: docs/protocol/admin.md
"""

from typing import Any, Optional

from .envelope import build


def admin_login_result(
    seq: Optional[int],
    success: bool,
    admin: Optional[dict[str, Any]] = None,
    expires_at: Optional[str] = None,
    reason_code: Optional[str] = None,
) -> dict[str, Any]:
    """관리자 인증 결과를 만든다.

    Args:
        seq: 요청 번호
        success: 인증 성공 여부
        admin: 성공 시 관리자 정보 (id, username, display_name)
        expires_at: 성공 시 세션 만료 시각 ISO 문자열
        reason_code: 실패 시 사유 코드
    """
    payload: dict[str, Any] = {"success": success}

    if admin is not None:
        payload["admin"] = admin
    if expires_at is not None:
        payload["expires_at"] = expires_at
    if reason_code is not None:
        payload["reason_code"] = reason_code

    return build("admin_login_result", seq=seq, **payload)


def service_login_result(
    seq: Optional[int],
    success: bool,
    service: Optional[str] = None,
    expires_at: Optional[str] = None,
    reason_code: Optional[str] = None,
) -> dict[str, Any]:
    """서비스 인증 결과를 만든다.

    랜딩 백엔드가 계정 생성을 위해 쓴다. 성공해도 `account_create` 외의
    어드민 메시지는 `PERMISSION_DENIED` 로 거절된다.
    """
    payload: dict[str, Any] = {"success": success}

    if service is not None:
        payload["service"] = service
    if expires_at is not None:
        payload["expires_at"] = expires_at
    if reason_code is not None:
        payload["reason_code"] = reason_code

    return build("service_login_result", seq=seq, **payload)


def admin_rejected(
    seq: Optional[int],
    action: str,
    reason_code: str,
    detail: str = "",
) -> dict[str, Any]:
    """어드민 요청 거절 메시지를 만든다.

    Args:
        seq: 거절 대상 요청의 번호
        action: 거절된 메시지 타입 또는 `admin_action` 의 action 이름
        reason_code: 사유 코드
        detail: 개발자용 영문 설명
    """
    return build(
        "admin_rejected",
        seq=seq,
        action=action,
        reason_code=reason_code,
        detail=detail,
    )
