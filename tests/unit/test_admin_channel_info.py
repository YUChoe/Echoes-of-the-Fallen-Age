"""
게임 채널의 어드민 진입 안내 단위 테스트

어드민 권한 계정이 게임 채널에 로그인하면 서버가 어드민 채널 사용 가능
여부를 알린다. 계약: docs/protocol/server-to-client.md
"""

from src.mud_engine.server.telnet_server import TelnetServer


class _StubPlayer:
    """is_admin 만 보는 최소 대역"""

    def __init__(self, is_admin: bool) -> None:
        self.is_admin = is_admin


class _StubAdminServer:
    def __init__(self, running: bool) -> None:
        self.is_running = running


def _server(admin_server: object | None) -> TelnetServer:
    server = TelnetServer()
    server.admin_server = admin_server  # type: ignore[assignment]
    return server


def test_non_admin_gets_no_admin_channel_field():
    """비관리자 응답에는 필드를 담지 않는다"""
    server = _server(_StubAdminServer(True))

    assert server._admin_channel_info(_StubPlayer(False)) is None


def test_admin_gets_available_when_admin_server_running():
    """어드민 서버가 떠 있으면 available 이 참이다"""
    server = _server(_StubAdminServer(True))

    info = server._admin_channel_info(_StubPlayer(True))

    assert info == {
        "available": True,
        "channel": "admin",
        "requires_reauth": True,
    }


def test_admin_gets_unavailable_when_admin_server_stopped():
    """권한이 있어도 어드민 서버가 없으면 available 이 거짓이다"""
    server = _server(_StubAdminServer(False))

    info = server._admin_channel_info(_StubPlayer(True))

    assert info is not None
    assert info["available"] is False


def test_admin_gets_unavailable_when_admin_server_absent():
    """어드민 채널이 없는 배포에서도 응답이 성립한다"""
    server = _server(None)

    info = server._admin_channel_info(_StubPlayer(True))

    assert info is not None
    assert info["available"] is False


def test_reauth_is_always_required():
    """게임 세션 인증은 어드민 채널로 전이되지 않으므로 항상 재인증이다"""
    for running in (True, False):
        server = _server(_StubAdminServer(running))
        info = server._admin_channel_info(_StubPlayer(True))

        assert info is not None
        assert info["requires_reauth"] is True
