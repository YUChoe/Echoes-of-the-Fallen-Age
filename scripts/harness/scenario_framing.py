#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""프레이밍 검증 시나리오

두 층으로 검증한다.

1. 단위 검증 - 서버 없이 LineReader와 TelnetFilter의 동작을 확인한다.
   분할 수신, 병합 수신, 멀티바이트 경계 분할이 대상이다.
2. 왕복 검증 - 서버에 붙어 한국어를 포함한 페이로드가 손상 없이 오는지 확인한다.
   프로토콜 전환 전에는 텍스트 라인을 수신해 기준선을 확보한다.

라인 프레이밍의 핵심은 개행을 찾은 뒤에야 UTF-8 디코딩을 수행하는 것이다.
청크 단위로 디코딩하면 멀티바이트 문자가 경계에서 쪼개져 한국어가 손상된다.
"""

import json

from .client import DEFAULT_PORT, HarnessClient, HarnessError
from .framing import LineReader, LineTooLongError, TelnetFilter
from .result import ScenarioResult

# 한국어와 이모지를 포함해 멀티바이트 경계 분할을 유발하는 표본
_SAMPLE_KO = "성문 앞 넓은 광장에 사람들의 발길이 끊이지 않는다."
_SAMPLE_MIXED = "재의 약탈자 ⚔ Ash Raider 🐾 카르나스"


def _check_split_at_every_offset(result: ScenarioResult) -> None:
    """모든 분할 지점에서 라인 복원이 원본과 일치하는지 확인한다.

    멀티바이트 문자 중간에서 쪼개도 결과가 같아야 한다. 이것이 청크 단위
    디코딩과 라인 단위 디코딩의 차이를 드러내는 검증이다.
    """
    original = _SAMPLE_KO
    payload = (original + "\n").encode("utf-8")

    failures: list[int] = []
    for offset in range(1, len(payload)):
        reader = LineReader()
        lines = reader.feed(payload[:offset])
        lines.extend(reader.feed(payload[offset:]))
        if lines != [original]:
            failures.append(offset)

    if failures:
        result.fail(
            "분할 지점별 라인 복원",
            f"{len(failures)}개 지점에서 불일치 (예: offset={failures[:5]})",
        )
    else:
        result.ok("분할 지점별 라인 복원", f"{len(payload) - 1}개 지점 모두 일치")


def _check_merged_lines(result: ScenarioResult) -> None:
    """한 청크에 여러 라인이 들어온 경우 각각 분리되는지 확인한다."""
    lines = ["첫째 줄", "second line", _SAMPLE_MIXED]
    payload = "".join(line + "\n" for line in lines).encode("utf-8")

    reader = LineReader()
    got = reader.feed(payload)

    if got == lines:
        result.ok("병합 수신 분리", f"{len(lines)}줄 분리")
    else:
        result.fail("병합 수신 분리", f"기대 {lines}, 실제 {got}")


def _check_partial_line_held(result: ScenarioResult) -> None:
    """개행이 없는 잔여 바이트를 라인으로 내보내지 않는지 확인한다."""
    reader = LineReader()
    got = reader.feed("개행 없는 조각".encode())

    if got:
        result.fail("불완전 라인 보류", f"라인을 반환했다: {got}")
        return

    pending = reader.pending()
    if not pending:
        result.fail("불완전 라인 보류", "잔여 버퍼가 비어 있다")
        return

    remainder = reader.feed(b"\n")
    if remainder == ["개행 없는 조각"]:
        result.ok("불완전 라인 보류", "개행 수신 후 복원")
    else:
        result.fail("불완전 라인 보류", f"복원 실패: {remainder}")


def _check_crlf_and_empty(result: ScenarioResult) -> None:
    """CRLF 종결과 빈 라인 처리를 확인한다."""
    reader = LineReader()
    got = reader.feed(b"with cr\r\n\n\nafter blanks\n")

    if got == ["with cr", "after blanks"]:
        result.ok("CRLF와 빈 라인", "CR 제거 및 빈 라인 폐기")
    else:
        result.fail("CRLF와 빈 라인", f"실제 {got}")


def _check_line_limit(result: ScenarioResult) -> None:
    """라인 길이 상한 초과 시 예외가 발생하는지 확인한다."""
    reader = LineReader(max_line_bytes=64)
    try:
        reader.feed(b"x" * 128)
    except LineTooLongError:
        result.ok("라인 길이 상한", "초과 시 예외 발생")
        return
    result.fail("라인 길이 상한", "예외가 발생하지 않았다")


def _check_iac_filter(result: ScenarioResult) -> None:
    """IAC 협상 시퀀스가 제거되는지 확인한다."""
    # IAC WILL ECHO(0x01) + 본문 + IAC SB ... IAC SE + 본문
    chunk = (
        bytes((0xFF, 0xFB, 0x01))
        + b"hello"
        + bytes((0xFF, 0xFA, 0x18, 0x00, 0x41, 0xFF, 0xF0))
        + b"world"
    )
    got = TelnetFilter().filter(chunk)

    if got == b"helloworld":
        result.ok("IAC 시퀀스 제거", "협상과 서브협상 모두 제거")
    else:
        result.fail("IAC 시퀀스 제거", f"실제 {got!r}")


def _check_iac_across_chunks(result: ScenarioResult) -> None:
    """IAC 시퀀스가 청크 경계에 걸쳐도 제거되는지 확인한다."""
    telnet_filter = TelnetFilter()
    first = telnet_filter.filter(bytes((0xFF,)))
    second = telnet_filter.filter(bytes((0xFB, 0x01)) + b"data")

    if first + second == b"data":
        result.ok("청크 경계 IAC", "상태 유지로 제거 성공")
    else:
        result.fail("청크 경계 IAC", f"실제 {(first + second)!r}")


def _check_iac_literal(result: ScenarioResult) -> None:
    """IAC IAC가 리터럴 0xFF로 복원되는지 확인한다."""
    got = TelnetFilter().filter(bytes((0xFF, 0xFF)))

    if got == bytes((0xFF,)):
        result.ok("IAC 리터럴", "IAC IAC를 0xFF로 복원")
    else:
        result.fail("IAC 리터럴", f"실제 {got!r}")


def _check_json_roundtrip(result: ScenarioResult) -> None:
    """한국어를 포함한 JSON이 직렬화와 파싱을 거쳐 보존되는지 확인한다."""
    original = {
        "type": "event",
        "message": {
            "key": "combat.damage_dealt",
            "params": {"target": {"en": "Ash Raider", "ko": "재의 약탈자"}, "damage": 12},
        },
    }
    line = json.dumps(original, ensure_ascii=False, separators=(",", ":"))

    if "\n" in line:
        result.fail("JSON 라인 무개행", "직렬화 결과에 개행이 포함됐다")
        return

    reader = LineReader()
    got = reader.feed((line + "\n").encode("utf-8"))
    if len(got) != 1 or json.loads(got[0]) != original:
        result.fail("JSON 왕복", f"복원 실패: {got}")
        return

    result.ok("JSON 왕복", "한국어 포함 페이로드 보존")


def run_unit(result: ScenarioResult) -> None:
    """서버 없이 실행할 수 있는 단위 검증"""
    _check_split_at_every_offset(result)
    _check_merged_lines(result)
    _check_partial_line_held(result)
    _check_crlf_and_empty(result)
    _check_line_limit(result)
    _check_iac_filter(result)
    _check_iac_across_chunks(result)
    _check_iac_literal(result)
    _check_json_roundtrip(result)


def run_roundtrip(result: ScenarioResult, port: int = DEFAULT_PORT) -> None:
    """서버에 붙어 수신 경로를 확인한다.

    프로토콜 전환 전에는 텍스트 라인을 받는다. 전환 후에는 welcome 메시지가
    JSON으로 온다. 어느 쪽이든 라인 복원이 성립하는지가 검증 대상이다.
    """
    try:
        with HarnessClient(port=port, verbose=False) as client:
            client.connect()
            lines = client.read_lines(800)
    except HarnessError as exc:
        result.skip("서버 왕복 수신", str(exc))
        return

    if not lines:
        result.fail("서버 왕복 수신", "수신한 라인이 없다")
        return

    joined = "\n".join(lines)
    replacement_count = joined.count("\ufffd")

    if replacement_count:
        result.fail(
            "서버 왕복 수신",
            f"{len(lines)}줄 수신했으나 대체 문자 {replacement_count}개 발견 "
            "(멀티바이트 손상 가능성)",
        )
        return

    result.ok("서버 왕복 수신", f"{len(lines)}줄 수신, 문자 손상 없음")
