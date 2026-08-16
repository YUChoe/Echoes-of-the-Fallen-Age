# -*- coding: utf-8 -*-
"""플레이어 활동 로그 검증

기록 대상은 액션과 채팅이다. 대상은 번호가 아니라 uuid 로 남아야 한다. 번호
기반 대상 지정은 폐기됐고, 사후에 로그를 읽을 때 번호로는 무엇을 가리켰는지
되찾을 수 없다.
"""

import logging

import pytest

from src.mud_engine.server import player_session_logger as psl


PLAYER_ID = "8757e357-fcb4-499b-961a-8110648bb04d"
TARGET_ID = "7d9cc821-1660-4d92-9b3a-cc8202193b19"


class _Collector(logging.Handler):
    """기록된 줄을 모은다."""

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())


@pytest.fixture
def collector():
    """플레이어 로거에 수집 핸들러를 붙였다 뗀다."""
    player_logger = logging.getLogger(f"player.{PLAYER_ID}")
    handler = _Collector()
    player_logger.addHandler(handler)
    player_logger.setLevel(logging.INFO)
    player_logger.propagate = False

    yield handler

    player_logger.removeHandler(handler)


def test_핸들러가_없으면_버린다() -> None:
    # 인증 전이거나 세션이 끝난 뒤다. 그대로 기록하면 통합 로그로 샌다
    unknown = logging.getLogger("player.no-such-player")
    assert not unknown.handlers

    psl.write("no-such-player", "샐 수 없다")

    assert not unknown.handlers


def test_빈_player_id_는_버린다(collector) -> None:
    psl.write("", "대상 없음")
    assert collector.lines == []


def test_대상이_uuid_로_남는다(collector) -> None:
    psl.log_action(PLAYER_ID, "attack", TARGET_ID, None, "success")

    assert collector.lines == [f"액션: attack target={TARGET_ID} -> success"]


def test_대상이_없는_액션은_target_을_적지_않는다(collector) -> None:
    psl.log_action(PLAYER_ID, "look", None, None, "success")

    assert collector.lines == ["액션: look -> success"]


def test_거절도_사유_코드와_함께_남는다(collector) -> None:
    psl.log_action(PLAYER_ID, "attack", TARGET_ID, None, "rejected(NOT_FOUND)")

    assert "rejected(NOT_FOUND)" in collector.lines[0]


def test_params_를_남긴다(collector) -> None:
    psl.log_action(
        PLAYER_ID, "dialogue_choice", None, {"choice_index": 1}, "success")

    assert "params={'choice_index': 1}" in collector.lines[0]


def test_빈_params_는_적지_않는다(collector) -> None:
    psl.log_action(PLAYER_ID, "look", None, {}, "success")

    assert collector.lines == ["액션: look -> success"]


def test_긴_params_는_자른다(collector) -> None:
    psl.log_action(
        PLAYER_ID, "say", None, {"text": "가" * 500}, "success")

    line = collector.lines[0]
    assert "… -> success" in line
    assert len(line) < 400


def test_방_채팅을_남긴다(collector) -> None:
    psl.log_chat(PLAYER_ID, "room", "안녕하세요")

    assert collector.lines == ["채팅[room] 안녕하세요"]


def test_귓속말은_대상을_함께_남긴다(collector) -> None:
    psl.log_chat(PLAYER_ID, "whisper", "둘만의 이야기", target=TARGET_ID)

    assert collector.lines == [f"채팅[whisper] target={TARGET_ID} 둘만의 이야기"]


def test_로그_파일명에_날짜가_들어간다(tmp_path, monkeypatch) -> None:
    # 로그 줄은 시각만 담는다. 한 파일에 여러 날이 쌓이면 어제와 오늘이
    # 구별되지 않는다
    monkeypatch.setattr(psl, "PLAYER_LOG_DIR", str(tmp_path))

    manager = psl.PlayerSessionLogger()
    manager.setup_player_logger(PLAYER_ID, "player5426", "sid", "127.0.0.1")

    try:
        names = [path.name for path in tmp_path.iterdir()]
    finally:
        manager.cleanup_player_logger(PLAYER_ID)

    assert len(names) == 1
    assert names[0].startswith(f"{PLAYER_ID}-")
    assert names[0].endswith(".log")

    stamp = names[0][len(PLAYER_ID) + 1: -len(".log")]
    assert len(stamp) == 8 and stamp.isdigit()
