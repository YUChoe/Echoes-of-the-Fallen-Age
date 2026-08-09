# -*- coding: utf-8 -*-
"""대화 페이로드 직렬화

선택지 번호는 대화 인스턴스 안에서만 유효한 로컬 번호다. uuid 규약의 예외이며,
선택지는 엔티티가 아니라 대화 트리의 분기이므로 uuid 를 갖지 않는다.

과도기 사항: 계약은 `lines[]` 와 `choices[].text` 가 번역 키를 담도록 규정하지만,
대사 원본이 `configs/dialogues/*.lua` 의 언어별 완성 문장이라 현재는 키가 존재하지
않는다. 그래서 언어별 dict 를 그대로 싣는다. 번역 키 전환은 별도 태스크에서
Lua 스크립트의 대사를 키로 바꾸고 클라이언트 번역 파일로 옮길 때 수행한다.

프로토콜 계약: docs/protocol/server-to-client.md
"""

from typing import Any, Optional

# 자동으로 붙는 대화 종료 선택지. Lua 스크립트가 제공하지 않아도 나갈 길을 준다.
FAREWELL_CHOICE: dict[str, str] = {"en": "Bye.", "ko": "안녕히."}


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
    choice_entity[next_index] = dict(FAREWELL_CHOICE)

    return choice_entity


def _is_farewell(value: Any) -> bool:
    """대화 종료 선택지인지 판별한다.

    판정 기준은 `DialogueInstance.get_dialogueby_choice` 와 같아야 한다.
    """
    if isinstance(value, dict):
        return value.get("en") == FAREWELL_CHOICE["en"]
    return value == FAREWELL_CHOICE["en"]


def _text_payload(value: Any) -> dict[str, str]:
    """대사 한 줄을 언어별 dict 로 만든다."""
    from .entity import localized_dict

    if isinstance(value, dict):
        return localized_dict(value)

    text = str(value) if value is not None else ""
    return {"en": text, "ko": text}


def serialize_choices(choice_entity: dict[int, Any]) -> list[dict[str, Any]]:
    """선택지 맵을 번호 순서대로 배열로 만든다."""
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
        lines: 대사 목록. 언어별 dict 또는 문자열
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
