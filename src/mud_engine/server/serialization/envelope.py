# -*- coding: utf-8 -*-
"""메시지 봉투와 JSON 라인 인코딩

모든 서버 송신 메시지는 `type` 필드를 갖는 JSON 오브젝트이며 개행으로 종결된다.
메시지 내부에는 개행이 들어가지 않는다.

프로토콜 계약: docs/protocol/README.md
"""

import json
from typing import Any, Optional

# 라인 하나의 최대 길이. 계약과 하니스가 같은 값을 쓴다.
MAX_LINE_BYTES = 256 * 1024

# 프로토콜 계약 버전. welcome 메시지로 클라이언트에 알린다.
PROTOCOL_VERSION = 1


def build(message_type: str, seq: Optional[int] = None, **fields: Any) -> dict[str, Any]:
    """봉투를 만든다.

    Args:
        message_type: 메시지 종류
        seq: 요청에 대한 응답이면 그 요청의 번호. 자발적 알림이면 None
        **fields: 메시지별 필드

    Returns:
        봉투가 적용된 딕셔너리
    """
    envelope: dict[str, Any] = {"type": message_type}
    if seq is not None:
        envelope["seq"] = seq
    envelope.update(fields)
    return envelope


def encode(message: dict[str, Any]) -> str:
    """메시지를 JSON 라인 문자열로 인코딩한다.

    한국어를 그대로 보내기 위해 ensure_ascii를 끈다. 개행은 붙이지 않으며
    전송 계층이 라인을 종결한다.

    Raises:
        ValueError: 직렬화 결과에 개행이 포함된 경우
    """
    line = json.dumps(message, ensure_ascii=False, separators=(",", ":"))

    if "\n" in line or "\r" in line:
        # json.dumps 는 문자열 값의 개행을 \n 으로 이스케이프하므로 정상 경로에서는
        # 발생하지 않는다. 발생했다면 인코딩 설정이 어긋난 것이다.
        raise ValueError("직렬화 결과에 개행이 포함되었습니다")

    return line


def encode_line(message: dict[str, Any]) -> bytes:
    """메시지를 개행으로 종결된 UTF-8 바이트로 인코딩한다."""
    return (encode(message) + "\n").encode("utf-8")


def error(reason_code: str, detail: str = "", seq: Optional[int] = None) -> dict[str, Any]:
    """프로토콜 수준 오류 메시지를 만든다.

    게임 로직의 거절은 `action_rejected` 를 쓴다. 이 함수는 JSON 파싱 실패,
    필수 필드 누락처럼 계약 위반에만 사용한다.

    Args:
        reason_code: 사유 코드
        detail: 개발자용 영문 설명. 사용자에게 표시하지 않는다
        seq: 대응되는 요청 번호가 있으면 지정
    """
    return build("error", seq=seq, reason_code=reason_code, detail=detail)


def action_rejected(
    seq: Optional[int],
    verb: str,
    reason_code: str,
    message_key: Optional[str] = None,
    params: Optional[dict[str, Any]] = None,
    target: Optional[str] = None,
) -> dict[str, Any]:
    """액션 거절 메시지를 만든다.

    클라이언트는 엔티티 속성으로 버튼을 추론하므로 적용 불가한 verb 를 보낼 수 있다.
    이는 정상 동작 범위이며 오류가 아니다.

    Args:
        seq: 거절 대상 요청의 번호
        verb: 거절된 액션
        reason_code: 사유 코드
        message_key: 사용자에게 표시할 번역 키
        params: 번역 치환 파라미터
        target: 대상 엔티티 uuid
    """
    payload: dict[str, Any] = {"verb": verb, "reason_code": reason_code}

    if target is not None:
        payload["target"] = target
    if message_key is not None:
        payload["message"] = {"key": message_key, "params": params or {}}

    return build("action_rejected", seq=seq, **payload)


def message_payload(key: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """번역 키 페이로드를 만든다.

    서버는 완성된 문장을 만들지 않는다. 클라이언트가 키와 파라미터로 번역한다.
    params 값이 언어별 dict 이면 클라이언트가 현재 locale 값을 골라 치환한다.
    """
    return {"key": key, "params": params or {}}
