# -*- coding: utf-8 -*-
"""어드민 감사 로그

모든 어드민 변경 작업에 실행 주체, 대상, 변경 내용, 시각을 남긴다. DB 테이블에
저장하지 않고 파일 로그로 남기기로 결정했다.

한 건이 한 줄의 JSON 이다. 사람이 읽을 수 있고 `grep` 과 `jq` 로 걸러낼 수 있으며
포맷이 고정되어 나중에 다른 저장소로 옮기기도 쉽다.

전용 파일 `logs/admin_audit-YYYYMMDD.log` 에 쓰면서 상위 로거로도 전파한다.
전파를 남겨 두는 이유는 설정을 거치지 않는 실행 경로(테스트, 스크립트)에서도
기록이 사라지지 않게 하기 위해서다.

프로토콜 계약: docs/protocol/admin.md
"""

import json
import logging
import logging.handlers
import os
from datetime import datetime
from typing import Any, Optional

# 감사 로그 전용 로거. 일반 서버 로그와 파일을 분리한다
AUDIT_LOGGER_NAME = "mud_engine.admin.audit"

# 값에 담긴 비밀을 파일에 남기지 않는다. 컬럼명과 파라미터명을 함께 다룬다
SECRET_KEYS = frozenset(
    {"password", "password_hash", "new_password", "token", "service_token"}
)

# 값 하나가 감사 파일을 부풀리지 않도록 자른다. 방 설명은 최대 645자였다
MAX_VALUE_CHARS = 200

REDACTED = "<redacted>"

_logger = logging.getLogger(AUDIT_LOGGER_NAME)


class _JsonLineFormatter(logging.Formatter):
    """메시지를 그대로 한 줄로 쓴다. 메시지가 이미 JSON 이다."""

    def format(self, record: logging.LogRecord) -> str:
        return record.getMessage()


def setup_audit_log(directory: str = "logs", backup_days: int = 90) -> None:
    """감사 로그 전용 파일 핸들러를 붙인다.

    두 번 호출해도 핸들러가 중복되지 않는다.

    Args:
        directory: 로그 디렉터리
        backup_days: 보관 일수. 감사 기록은 일반 로그보다 오래 남긴다
    """
    if any(isinstance(handler, logging.handlers.TimedRotatingFileHandler)
           for handler in _logger.handlers):
        return

    os.makedirs(directory, exist_ok=True)

    handler = logging.handlers.TimedRotatingFileHandler(
        filename=os.path.join(directory, "admin_audit.log"),
        when="midnight",
        backupCount=backup_days,
        encoding="utf-8",
    )
    handler.suffix = "%Y%m%d"
    handler.setFormatter(_JsonLineFormatter())

    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)


def record(
    actor: str,
    operation: str,
    resource: Optional[str] = None,
    target: Optional[dict[str, Any]] = None,
    changes: Optional[dict[str, Any]] = None,
    result: str = "ok",
    reason_code: Optional[str] = None,
    detail: Optional[str] = None,
) -> None:
    """감사 기록 한 건을 남긴다.

    Args:
        actor: 실행 주체. 관리자 사용자명 또는 서비스 이름
        operation: `create`, `update`, `delete` 또는 액션 이름
        resource: 리소스 이름. 액션에는 없을 수 있다
        target: 대상 식별자. 보통 기본키
        changes: 변경 내용 또는 액션 파라미터
        result: `ok` 또는 `rejected`
        reason_code: 거절된 경우의 사유 코드
        detail: 거절된 경우의 영문 설명
    """
    entry: dict[str, Any] = {
        "ts": datetime.now().isoformat(),
        "actor": actor,
        "operation": operation,
        "result": result,
    }

    if resource is not None:
        entry["resource"] = resource
    if target:
        entry["target"] = target
    if changes:
        entry["changes"] = redact_values(changes)
    if reason_code is not None:
        entry["reason_code"] = reason_code
    if detail is not None:
        entry["detail"] = detail

    _logger.info(json.dumps(entry, ensure_ascii=False, separators=(",", ":")))


def redact_values(
    values: dict[str, Any], hidden: Optional[frozenset[str]] = None
) -> dict[str, Any]:
    """감사 파일에 남길 수 있는 형태로 값을 다듬는다.

    비밀 값은 가리고, 긴 값은 자르고, 구조는 유지한다.

    Args:
        values: 원본 값
        hidden: 리소스가 노출을 막은 컬럼. 비밀 목록에 더해 함께 가린다
    """
    blocked = SECRET_KEYS | (hidden or frozenset())

    return {key: _clip(key, value, blocked) for key, value in values.items()}


def _clip(key: str, value: Any, blocked: frozenset[str]) -> Any:
    """값 하나를 다듬는다."""
    if key.lower() in blocked:
        return REDACTED

    if isinstance(value, str) and len(value) > MAX_VALUE_CHARS:
        return value[:MAX_VALUE_CHARS] + f"...({len(value)}자)"

    if isinstance(value, (dict, list)):
        # 중첩 구조는 길이만 남긴다. 감사 목적에는 무엇이 바뀌었는지가 중요하다
        return f"<{type(value).__name__} len={len(value)}>"

    return value
