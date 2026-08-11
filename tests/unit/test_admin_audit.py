"""
어드민 감사 로그 단위 테스트

기록 형식, 비밀 값 차단, 값 절단, 전용 파일 핸들러를 확인한다.
DB 테이블에 저장하지 않고 파일 로그로 남기기로 결정했다.
계약: docs/protocol/admin.md
"""

import json
import logging
import logging.handlers

import pytest

from src.mud_engine.server.admin import audit
from src.mud_engine.server.admin.audit import (
    AUDIT_LOGGER_NAME,
    MAX_VALUE_CHARS,
    REDACTED,
    SECRET_KEYS,
    record,
    redact_values,
    setup_audit_log,
)


@pytest.fixture
def captured():
    """감사 로거가 남긴 JSON 기록을 모은다"""
    logger = logging.getLogger(AUDIT_LOGGER_NAME)
    entries: list[dict] = []

    class _Capture(logging.Handler):
        def emit(self, record_obj: logging.LogRecord) -> None:
            entries.append(json.loads(record_obj.getMessage()))

    handler = _Capture()
    previous_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    yield entries

    logger.removeHandler(handler)
    logger.setLevel(previous_level)


# 기록 형식 ------------------------------------------------------------------


def test_record_carries_actor_operation_and_time(captured):
    """계약이 요구하는 실행 주체, 대상, 변경 내용, 시각을 남긴다"""
    record(
        actor="player5426",
        operation="update",
        resource="rooms",
        target={"id": "r1"},
        changes={"description_ko": "광장"},
    )

    entry = captured[0]

    assert entry["actor"] == "player5426"
    assert entry["operation"] == "update"
    assert entry["resource"] == "rooms"
    assert entry["target"] == {"id": "r1"}
    assert entry["changes"] == {"description_ko": "광장"}
    assert entry["result"] == "ok"
    assert "T" in entry["ts"]


def test_record_is_one_json_line(captured):
    """한 건이 한 줄이어야 grep 과 jq 로 다룰 수 있다"""
    logger = logging.getLogger(AUDIT_LOGGER_NAME)

    emitted: list[str] = []

    class _Raw(logging.Handler):
        def emit(self, record_obj: logging.LogRecord) -> None:
            emitted.append(record_obj.getMessage())

    handler = _Raw()
    logger.addHandler(handler)
    try:
        record(actor="a", operation="delete", changes={"note": "줄바꿈\n포함"})
    finally:
        logger.removeHandler(handler)

    assert len(emitted) == 1
    assert "\n" not in emitted[0]


def test_rejection_records_reason_code(captured):
    """거절된 시도도 남긴다. 무엇을 시도했는지가 감사 대상이다"""
    record(
        actor="player5426",
        operation="delete",
        resource="factions",
        target={"id": "ash_knights"},
        result="rejected",
        reason_code="REFERENCED",
        detail="factions is referenced by 46 row(s)",
    )

    entry = captured[0]

    assert entry["result"] == "rejected"
    assert entry["reason_code"] == "REFERENCED"
    assert entry["detail"].startswith("factions is referenced")


def test_empty_fields_are_omitted(captured):
    """값이 없는 항목은 담지 않는다"""
    record(actor="landing", operation="account_create")

    entry = captured[0]

    assert entry["actor"] == "landing"
    for field in ("resource", "target", "changes", "reason_code", "detail"):
        assert field not in entry


# 비밀 값 차단 ---------------------------------------------------------------


def test_secret_keys_are_redacted():
    """비밀번호와 토큰은 감사 파일에 남기지 않는다"""
    values = {"username": "newplayer", "password": "test1234", "token": "s3cr3t"}

    assert redact_values(values) == {
        "username": "newplayer",
        "password": REDACTED,
        "token": REDACTED,
    }


def test_password_hash_is_in_secret_keys():
    """리소스 정책과 별개로 감사 계층도 해시를 막는다"""
    assert "password_hash" in SECRET_KEYS
    assert redact_values({"password_hash": "$2b$12$..."})["password_hash"] == REDACTED


def test_redaction_is_case_insensitive():
    """대소문자가 달라도 비밀 값으로 본다"""
    assert redact_values({"Password": "x"})["Password"] == REDACTED


def test_hidden_columns_are_redacted_too():
    """리소스가 노출을 막은 컬럼도 함께 가린다"""
    result = redact_values({"email": "a@b.c"}, hidden=frozenset({"email"}))

    assert result["email"] == REDACTED


# 값 다듬기 ------------------------------------------------------------------


def test_long_values_are_clipped():
    """방 설명은 최대 645자였다. 감사 파일이 부풀지 않게 자른다"""
    long_text = "가" * 700

    clipped = redact_values({"description_ko": long_text})["description_ko"]

    assert clipped.startswith("가" * MAX_VALUE_CHARS)
    assert "700자" in clipped
    assert len(clipped) < len(long_text)


def test_short_values_are_untouched():
    """상한 이하의 값은 그대로 남긴다"""
    assert redact_values({"room_type": "gate"})["room_type"] == "gate"


def test_nested_structures_are_summarised():
    """중첩 구조는 무엇이 바뀌었는지만 남기고 내용은 생략한다"""
    result = redact_values({"blocked_exits": ["north", "west"], "stats": {"hp": 10}})

    assert result["blocked_exits"] == "<list len=2>"
    assert result["stats"] == "<dict len=1>"


def test_scalars_survive():
    """숫자, 참거짓, None 은 그대로 남긴다"""
    result = redact_values({"x": 0, "is_alive": True, "faction_id": None})

    assert result == {"x": 0, "is_alive": True, "faction_id": None}


# 전용 파일 ------------------------------------------------------------------


def test_setup_attaches_rotating_file_handler(tmp_path):
    """전용 파일에 날짜 단위로 로테이션한다"""
    logger = logging.getLogger(AUDIT_LOGGER_NAME)
    original = list(logger.handlers)

    for handler in original:
        logger.removeHandler(handler)

    try:
        setup_audit_log(str(tmp_path))
        handlers = [
            h for h in logger.handlers
            if isinstance(h, logging.handlers.TimedRotatingFileHandler)
        ]

        assert len(handlers) == 1
        assert handlers[0].suffix == "%Y%m%d"
        assert (tmp_path / "admin_audit.log").exists()
    finally:
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)
        for handler in original:
            logger.addHandler(handler)


def test_setup_is_idempotent(tmp_path):
    """두 번 호출해도 핸들러가 중복되지 않는다"""
    logger = logging.getLogger(AUDIT_LOGGER_NAME)
    original = list(logger.handlers)

    for handler in original:
        logger.removeHandler(handler)

    try:
        setup_audit_log(str(tmp_path))
        setup_audit_log(str(tmp_path))

        handlers = [
            h for h in logger.handlers
            if isinstance(h, logging.handlers.TimedRotatingFileHandler)
        ]

        assert len(handlers) == 1
    finally:
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)
        for handler in original:
            logger.addHandler(handler)


def test_records_reach_the_file(tmp_path):
    """설정 후 기록이 실제로 파일에 쓰인다"""
    logger = logging.getLogger(AUDIT_LOGGER_NAME)
    original = list(logger.handlers)

    for handler in original:
        logger.removeHandler(handler)

    try:
        setup_audit_log(str(tmp_path))
        record(actor="player5426", operation="create", resource="rooms")

        for handler in logger.handlers:
            handler.flush()

        content = (tmp_path / "admin_audit.log").read_text(encoding="utf-8")
        entry = json.loads(content.strip().splitlines()[-1])

        assert entry["actor"] == "player5426"
        assert entry["operation"] == "create"
    finally:
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)
        for handler in original:
            logger.addHandler(handler)


def test_audit_logger_propagates():
    """설정을 거치지 않는 실행 경로에서도 기록이 사라지지 않는다"""
    assert logging.getLogger(AUDIT_LOGGER_NAME).propagate is True


def test_audit_logger_name_is_separate_from_server_log():
    """일반 서버 로그와 이름이 구분된다"""
    assert AUDIT_LOGGER_NAME == "mud_engine.admin.audit"
    assert audit.AUDIT_LOGGER_NAME.endswith(".audit")
