"""
계정 생성 경로 단위 테스트

입력 검증, 사용자명 중복, 서비스 토큰 미설정 시 경로 비활성화를 확인한다.
계약: docs/protocol/admin.md
"""

import pytest

from src.mud_engine.server.admin.account import (
    EMAIL_MAX_LENGTH,
    PASSWORD_MAX_BYTES,
    PASSWORD_MIN_LENGTH,
    SUPPORTED_LOCALES,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
    AccountHandlers,
    _validate,
    is_enabled,
)
from src.mud_engine.utils.exceptions import AuthenticationError


class _StubPlayer:
    def __init__(self, player_id: str) -> None:
        self.id = player_id


class _StubPlayerManager:
    """생성 요청을 기록하고 중복을 흉내낸다"""

    def __init__(self, taken: tuple[str, ...] = ()) -> None:
        self.taken = set(taken)
        self.calls: list[tuple] = []

    async def create_account(self, username, password, email=None, locale=None):
        self.calls.append((username, password, email, locale))
        if username in self.taken:
            raise AuthenticationError(f"사용자 이름 '{username}'이(가) 이미 존재합니다.")
        return _StubPlayer("a1b2c3d4")


class _StubPrincipal:
    name = "landing"


class _StubSession:
    session_id = "s-1"
    principal = _StubPrincipal()

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_message(self, message: dict) -> bool:
        self.sent.append(message)
        return True


class _StubServer:
    def __init__(self) -> None:
        self.registered: dict[str, object] = {}

    def register(self, message_type: str, handler) -> None:
        self.registered[message_type] = handler


def _valid_payload(**overrides) -> dict:
    payload = {
        "type": "account_create",
        "seq": 2,
        "username": "newplayer",
        "password": "test1234",
        "email": "user@example.com",
        "preferred_locale": "ko",
    }
    payload.update(overrides)
    return payload


# 사용자명 검증 --------------------------------------------------------------


def test_username_must_be_a_string():
    assert _validate(None, "test1234", None, None) == "username must be a string"
    assert _validate(42, "test1234", None, None) == "username must be a string"


def test_username_length_bounds():
    """계약이 규정한 길이 검증"""
    too_short = "a" * (USERNAME_MIN_LENGTH - 1)
    too_long = "a" * (USERNAME_MAX_LENGTH + 1)

    assert "characters" in (_validate(too_short, "test1234", None, None) or "")
    assert "characters" in (_validate(too_long, "test1234", None, None) or "")
    assert _validate("a" * USERNAME_MIN_LENGTH, "test1234", None, None) is None
    assert _validate("a" * USERNAME_MAX_LENGTH, "test1234", None, None) is None


def test_username_charset_is_ascii_only():
    """로그인 식별자이므로 한국어를 허용하지 않는다"""
    assert _validate("player_5426", "test1234", None, None) is None
    assert _validate("나그네", "test1234", None, None) is not None
    assert _validate("has space", "test1234", None, None) is not None
    assert _validate("drop;table", "test1234", None, None) is not None


# 비밀번호 검증 --------------------------------------------------------------


def test_password_minimum_length():
    short = "a" * (PASSWORD_MIN_LENGTH - 1)

    assert "at least" in (_validate("newplayer", short, None, None) or "")
    assert _validate("newplayer", "a" * PASSWORD_MIN_LENGTH, None, None) is None


def test_password_over_bcrypt_limit_is_rejected():
    """bcrypt 가 72바이트를 넘는 입력을 조용히 잘라내므로 거절한다"""
    too_long = "a" * (PASSWORD_MAX_BYTES + 1)

    assert "bytes" in (_validate("newplayer", too_long, None, None) or "")


def test_password_byte_length_counts_multibyte():
    """한국어 한 글자는 3바이트다. 문자 수가 아니라 바이트로 센다"""
    korean = "가" * 25  # 75바이트

    assert len(korean) < PASSWORD_MAX_BYTES
    assert "bytes" in (_validate("newplayer", korean, None, None) or "")


def test_password_must_be_a_string():
    assert _validate("newplayer", None, None, None) == "password must be a string"


# 이메일 검증 ----------------------------------------------------------------


def test_email_is_optional():
    """선택 항목이므로 없어도 통과한다"""
    assert _validate("newplayer", "test1234", None, None) is None


def test_email_format_is_checked():
    assert _validate("newplayer", "test1234", "user@example.com", None) is None
    assert _validate("newplayer", "test1234", "not-an-email", None) is not None
    assert _validate("newplayer", "test1234", "no@domain", None) is not None
    assert _validate("newplayer", "test1234", "two@@at.com", None) is not None


def test_email_length_is_capped():
    long_email = "a" * EMAIL_MAX_LENGTH + "@example.com"

    assert "exceed" in (_validate("newplayer", "test1234", long_email, None) or "")


# 선호 언어 ------------------------------------------------------------------


def test_locale_must_be_supported():
    for locale in SUPPORTED_LOCALES:
        assert _validate("newplayer", "test1234", None, locale) is None

    assert _validate("newplayer", "test1234", None, "jp") is not None
    assert _validate("newplayer", "test1234", None, 1) is not None


def test_locale_is_optional():
    assert _validate("newplayer", "test1234", None, None) is None


# 경로 활성화 ----------------------------------------------------------------


def test_path_is_disabled_without_service_token(monkeypatch):
    """토큰이 없으면 처리기를 등록하지 않는다"""
    monkeypatch.delenv("LANDING_SERVICE_TOKEN", raising=False)
    server = _StubServer()

    AccountHandlers(_StubPlayerManager()).register_all(server)

    assert is_enabled() is False
    assert "account_create" not in server.registered


def test_path_is_enabled_with_service_token(monkeypatch):
    """토큰이 있으면 등록한다"""
    monkeypatch.setenv("LANDING_SERVICE_TOKEN", "s3cr3t")
    server = _StubServer()

    AccountHandlers(_StubPlayerManager()).register_all(server)

    assert is_enabled() is True
    assert "account_create" in server.registered


# 생성 처리 ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_successful_creation_returns_player_id():
    """성공 응답에 player_id 를 담는다"""
    manager = _StubPlayerManager()
    session = _StubSession()

    await AccountHandlers(manager).handle(session, _valid_payload())

    message = session.sent[0]
    assert message["type"] == "account_create_result"
    assert message["seq"] == 2
    assert message["success"] is True
    assert message["player_id"] == "a1b2c3d4"


@pytest.mark.asyncio
async def test_email_and_locale_are_passed_through():
    """선택 항목이 저장 계층까지 전달된다"""
    manager = _StubPlayerManager()

    await AccountHandlers(manager).handle(_StubSession(), _valid_payload())

    assert manager.calls == [
        ("newplayer", "test1234", "user@example.com", "ko")
    ]


@pytest.mark.asyncio
async def test_blank_optional_fields_become_none():
    """빈 문자열은 값이 없는 것으로 다룬다"""
    manager = _StubPlayerManager()

    await AccountHandlers(manager).handle(
        _StubSession(), _valid_payload(email="", preferred_locale="")
    )

    assert manager.calls == [("newplayer", "test1234", None, None)]


@pytest.mark.asyncio
async def test_duplicate_username_is_rejected():
    """중복은 USERNAME_TAKEN 이다"""
    manager = _StubPlayerManager(taken=("newplayer",))
    session = _StubSession()

    await AccountHandlers(manager).handle(session, _valid_payload())

    message = session.sent[0]
    assert message["success"] is False
    assert message["reason_code"] == "USERNAME_TAKEN"
    assert "player_id" not in message


@pytest.mark.asyncio
async def test_validation_failure_does_not_touch_storage():
    """검증에서 걸리면 저장 계층을 호출하지 않는다"""
    manager = _StubPlayerManager()
    session = _StubSession()

    await AccountHandlers(manager).handle(session, _valid_payload(password="short"))

    assert manager.calls == []
    assert session.sent[0]["reason_code"] == "VALIDATION_FAILED"


@pytest.mark.asyncio
async def test_failure_response_omits_player_id():
    """실패 응답에 계정 식별자를 담지 않는다"""
    session = _StubSession()

    await AccountHandlers(_StubPlayerManager()).handle(
        session, _valid_payload(username="나그네")
    )

    assert "player_id" not in session.sent[0]
