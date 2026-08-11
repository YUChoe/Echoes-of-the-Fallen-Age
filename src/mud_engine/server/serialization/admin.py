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


def admin_list_result(
    seq: Optional[int],
    resource: str,
    page: int,
    page_size: int,
    total: int,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """리소스 목록 응답을 만든다.

    `rows` 의 각 항목은 DB 컬럼을 그대로 담는다. 게임 채널의 엔티티 스키마와
    달리 언어별 dict 로 묶지 않는다. 어드민은 데이터를 편집하는 도구이므로
    원본 구조가 그대로 보여야 한다.
    """
    return build(
        "admin_list_result",
        seq=seq,
        resource=resource,
        page=page,
        page_size=page_size,
        total=total,
        rows=rows,
    )


def admin_get_result(
    seq: Optional[int],
    resource: str,
    key: dict[str, Any],
    row: dict[str, Any],
) -> dict[str, Any]:
    """리소스 상세 응답을 만든다.

    Args:
        key: 기본키 컬럼과 값. 복합키면 항목이 둘 이상이다
        row: DB 컬럼을 그대로 담은 행
    """
    return build("admin_get_result", seq=seq, resource=resource, key=key, row=row)


def admin_mutate_result(
    seq: Optional[int],
    resource: str,
    key: dict[str, Any],
    success: bool,
    row: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """생성·수정·삭제 응답을 만든다.

    Args:
        key: 대상 행의 기본키
        row: 생성·수정 결과 행. 삭제에는 담지 않는다
    """
    payload: dict[str, Any] = {"resource": resource, "key": key, "success": success}

    if row is not None:
        payload["row"] = row

    return build("admin_mutate_result", seq=seq, **payload)


def admin_stats_result(
    seq: Optional[int], stats: dict[str, Any]
) -> dict[str, Any]:
    """서버 통계 응답을 만든다.

    `AdminManager` 의 반환값을 그대로 전달한다. 어드민은 데이터를 보는 도구이므로
    가공하지 않는다.
    """
    return build("admin_stats_result", seq=seq, **stats)


def admin_map_result(
    seq: Optional[int], bounds: dict[str, int], rooms: list[dict[str, Any]]
) -> dict[str, Any]:
    """맵 데이터 응답을 만든다.

    좌표와 종족 분포를 노출하므로 어드민 채널 전용이다.
    """
    return build("admin_map_result", seq=seq, bounds=bounds, rooms=rooms)


def admin_action_result(
    seq: Optional[int],
    action: str,
    success: bool,
    data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """실시간 액션 결과를 만든다.

    Args:
        action: 수행한 액션 이름
        success: 수행 성공 여부
        data: 액션별 결과 데이터
    """
    return build(
        "admin_action_result",
        seq=seq,
        action=action,
        success=success,
        data=data or {},
    )


def admin_rejected(
    seq: Optional[int],
    action: str,
    reason_code: str,
    detail: str = "",
    references: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """어드민 요청 거절 메시지를 만든다.

    Args:
        seq: 거절 대상 요청의 번호
        action: 거절된 메시지 타입 또는 `admin_action` 의 action 이름
        reason_code: 사유 코드
        detail: 개발자용 영문 설명
        references: `REFERENCED` 거절에서 삭제를 막은 참조 목록
    """
    payload: dict[str, Any] = {
        "action": action,
        "reason_code": reason_code,
        "detail": detail,
    }

    if references is not None:
        payload["references"] = references

    return build("admin_rejected", seq=seq, **payload)
