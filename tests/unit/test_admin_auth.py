"""
어드민 채널 인증 단위 테스트

주체 권한, 세션 만료, 서비스 토큰 검증과 어드민 메시지 봉투를 확인한다.
계약: docs/protocol/admin.md
"""

from datetime import datetime, timedelta

import pytest

from src.mud_engine.server import serialization as ser
from src.mud_engine.server.admin.auth import (
    SESSION_LIFETIME,
    AdminAuthenticator,
    AdminPrincipal,
)
from src.mud_engine.server.channels import (
    ADMIN_ONLY_TYPES,
    CHANNEL_ADMIN,
    CHANNEL_GAME,
    GAME_ONLY_TYPES,
    SHARED_TYPES,
    wrong_channel_detail,
)
from src.mud_engine.utils.exceptions import AuthenticationError


def _principal(kind: str, **overrides) -> AdminPrincipal:
    kwargs = {
        "kind": kind,
        "name": "player5426" if kind == "admin" else "landing",
        "expires_at": datetime.now() + SESSION_LIFETIME,
    }
    kwargs.update(overrides)
    return AdminPrincipal(**kwargs)


class _StubPlayer:
    """PlayerManager.authenticate 가 돌려주는 Player 의 최소 대역"""

    def __init__(self, username: str, is_admin: bool) -> None:
        self.id = "cf65f7f3-0000-0000-0000-000000000000"
        self.username = username
        self.is_admin = is_admin

    def get_display_name(self) -> str:
        return "SUPERADMIN"


class _StubPlayerManager:
    def __init__(self, player: _StubPlayer | None) -> None:
        self._player = player

    async def authenticate(self, username: str, password: str):
        if self._player is None or password != "test1234":
            raise AuthenticationError("사용자 이름 또는 비밀번호가 잘못되었습니다.")
        return self._player


# 주체 권한 ------------------------------------------------------------------


def test_admin_principal_has_no_type_restriction():
    """관리자 주체는 메시지 타입 제한이 없다

    토큰으로 붙는 서비스 주체는 없앴다. 계정 생성이 게임 채널의 `register` 로
    옮겨가 그 주체가 필요 없어졌다.
    """
    principal = _principal("admin")

    assert principal.may_send("account_create") is True
    assert principal.may_send("admin_list") is True
    assert principal.may_send("admin_action") is True


def test_admin_principal_has_no_type_restriction():
    """관리자 주체는 메시지 타입 제한이 없다"""
    principal = _principal("admin")

    assert principal.may_send("account_create") is True
    assert principal.may_send("admin_action") is True


def test_expiry_is_evaluated_against_now():
    """만료 시각이 지나면 만료로 판정한다"""
    expired = _principal("admin", expires_at=datetime.now() - timedelta(seconds=1))
    live = _principal("admin")

    assert expired.is_expired() is True
    assert live.is_expired() is False


def test_session_lifetime_is_two_hours():
    """계약이 규정한 세션 유효 기간은 2시간이다"""
    assert SESSION_LIFETIME == timedelta(hours=2)


# 관리자 인증 ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_login_succeeds_for_admin_account():
    """is_admin 계정은 인증에 성공한다"""
    auth = AdminAuthenticator(_StubPlayerManager(_StubPlayer("player5426", True)))

    principal = await auth.authenticate_admin("player5426", "test1234")

    assert principal.kind == "admin"
    assert principal.name == "player5426"
    assert principal.display_name == "SUPERADMIN"
    assert principal.is_expired() is False


@pytest.mark.asyncio
async def test_admin_login_rejects_non_admin_account():
    """자격이 맞아도 is_admin 이 거짓이면 거절한다"""
    auth = AdminAuthenticator(_StubPlayerManager(_StubPlayer("player0001", False)))

    with pytest.raises(PermissionError):
        await auth.authenticate_admin("player0001", "test1234")


@pytest.mark.asyncio
async def test_admin_login_rejects_wrong_password():
    """비밀번호가 틀리면 AuthenticationError 가 그대로 올라온다"""
    auth = AdminAuthenticator(_StubPlayerManager(_StubPlayer("player5426", True)))

    with pytest.raises(AuthenticationError):
        await auth.authenticate_admin("player5426", "wrong")


# 메시지 봉투 ----------------------------------------------------------------


def test_admin_login_result_success_shape():
    """성공 응답에 admin 과 expires_at 이 담긴다"""
    message = ser.admin_login_result(
        1,
        True,
        admin={"id": "cf65f7f3", "username": "player5426", "display_name": "SUPERADMIN"},
        expires_at="2026-08-10T18:45:00",
    )

    assert message["type"] == "admin_login_result"
    assert message["seq"] == 1
    assert message["success"] is True
    assert message["admin"]["username"] == "player5426"
    assert message["expires_at"] == "2026-08-10T18:45:00"
    assert "reason_code" not in message


def test_admin_login_result_failure_omits_admin():
    """실패 응답에는 admin 을 담지 않는다"""
    message = ser.admin_login_result(2, False, reason_code="PERMISSION_DENIED")

    assert message["success"] is False
    assert message["reason_code"] == "PERMISSION_DENIED"
    assert "admin" not in message
    assert "expires_at" not in message


def test_channel_type_sets_do_not_overlap():
    """한 메시지 타입이 두 채널 전용으로 동시에 분류되지 않는다"""
    assert GAME_ONLY_TYPES & ADMIN_ONLY_TYPES == frozenset()
    assert GAME_ONLY_TYPES & SHARED_TYPES == frozenset()
    assert ADMIN_ONLY_TYPES & SHARED_TYPES == frozenset()


def test_ping_is_shared_between_channels():
    """ping 은 두 채널 모두에서 허용된다"""
    assert "ping" in SHARED_TYPES
    assert "ping" not in GAME_ONLY_TYPES
    assert "ping" not in ADMIN_ONLY_TYPES


def test_wrong_channel_detail_names_both_channels():
    """detail 이 기대 채널과 현재 채널을 모두 밝힌다"""
    detail = wrong_channel_detail("login", CHANNEL_ADMIN)

    assert "login" in detail
    assert "game channel" in detail
    assert "admin channel" in detail


def test_wrong_channel_detail_is_direction_aware():
    """반대 방향에서는 기대 채널이 뒤바뀐다"""
    detail = wrong_channel_detail("admin_login", CHANNEL_GAME)

    assert "admin_login belongs to the admin channel" in detail
    assert "this connection is the game channel" in detail


def test_admin_rejected_uses_detail_not_translation_key():
    """어드민 거절은 번역 키 대신 영문 detail 을 쓴다"""
    message = ser.admin_rejected(
        30, "spawn_monster", "NOT_FOUND", "template_id not found: template_unknown"
    )

    assert message["type"] == "admin_rejected"
    assert message["action"] == "spawn_monster"
    assert message["reason_code"] == "NOT_FOUND"
    assert message["detail"] == "template_id not found: template_unknown"
    assert "message" not in message
