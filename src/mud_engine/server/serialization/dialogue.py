# -*- coding: utf-8 -*-
"""대화 페이로드 직렬화

선택지 번호는 대화 인스턴스 안에서만 유효한 로컬 번호다. uuid 규약의 예외이며,
선택지는 엔티티가 아니라 대화 트리의 분기이므로 uuid 를 갖지 않는다.

`lines[]` 와 `choices[].text` 는 번역 키와 치환 파라미터를 담는다. 서버는 문장을
만들지 않는다. 대사 원본은 클라이언트 저장소의 번역 파일에 있고 Lua 스크립트는
키만 돌려준다.

프로토콜 계약: docs/protocol/server-to-client.md
"""

from typing import Any, Optional

from ...game.dialogue import FAREWELL_KEY


def ensure_farewell_choice(choice_entity: dict[int, Any]) -> dict[int, Any]:
    """대화 종료 선택지가 없으면 마지막 번호로 추가한다.

    페이로드를 만들기 전에 호출해야 클라이언트가 받은 번호와 서버가 해석하는
    번호가 일치한다. 기존 구현은 표시 단계에서 추가해 두 번호가 어긋날 수 있었다.

    Args:
        choice_entity: 대화 인스턴스의 선택지 맵. 제자리에서 수정된다

    Returns:
        같은 맵
    """
    for value in choice_entity.values():
        if _is_farewell(value):
            return choice_entity

    next_index = max(choice_entity, default=0) + 1
    choice_entity[next_index] = {"key": FAREWELL_KEY, "params": {}}

    return choice_entity


def _is_farewell(value: Any) -> bool:
    """대화 종료 선택지인지 판별한다.

    판정 기준은 `DialogueInstance.get_dialogueby_choice` 와 같아야 한다. 같은
    상수를 쓰므로 한쪽만 바뀌지 않는다.
    """
    return isinstance(value, dict) and value.get("key") == FAREWELL_KEY


def _text_payload(value: Any) -> dict[str, Any]:
    """대사 한 줄을 `{key, params}` 로 만든다.

    Lua 스크립트가 이미 이 형태를 돌려주므로 형만 확정한다. 키가 없으면 빈 키를
    담는다. 클라이언트가 없는 키를 받으면 키 문자열을 그대로 보여 주므로 화면이
    비지 않고 누락이 드러난다.
    """
    if isinstance(value, dict):
        params = value.get("params")
        return {
            "key": str(value.get("key", "")),
            "params": params if isinstance(params, dict) else {},
        }

    return {"key": str(value) if value is not None else "", "params": {}}


def serialize_choices(choice_entity: dict[int, Any]) -> list[dict[str, Any]]:
    """선택지 맵을 번호 순서대로 배열로 만든다.

    `text` 는 `{key, params}` 다. 선택지 번호는 대화 인스턴스 로컬 번호이며
    클라이언트가 `dialogue_choice` 의 params 로 되돌려 보낸다.
    """
    return [
        {"index": int(index), "text": _text_payload(choice_entity[index])}
        for index in sorted(choice_entity)
    ]


def build_dialogue(
    dialogue_id: str,
    speaker: Any,
    lines: Any,
    choice_entity: dict[int, Any],
    is_active: bool = True,
    seq: Optional[int] = None,
) -> dict[str, Any]:
    """dialogue 메시지를 만든다.

    Args:
        dialogue_id: 대화 인스턴스 id
        speaker: 대화 상대 몬스터. 이름만 사용한다
        lines: 대사 목록. `{key, params}` 형태
        choice_entity: 선택지 맵. 번호를 키로 갖는다
        is_active: 거짓이면 클라이언트가 대화 창을 닫는다
        seq: 클라이언트 요청에 대한 응답이면 그 번호
    """
    from .entity import localized_dict
    from .envelope import build

    return build(
        "dialogue",
        seq=seq,
        dialogue_id=str(dialogue_id),
        speaker={
            "id": str(getattr(speaker, "id", "")),
            "name": localized_dict(getattr(speaker, "name", None)),
        },
        lines=[_text_payload(line) for line in (lines or [])],
        choices=serialize_choices(choice_entity),
        is_active=bool(is_active),
    )
