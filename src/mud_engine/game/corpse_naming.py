# -*- coding: utf-8 -*-
"""시체 이름과 설명 생성

서버에 남는 유일한 텍스트 생성이다. 시체는 `game_objects` 테이블의 이중언어
컬럼에 저장되는 콘텐츠이므로, 프로토콜 메시지처럼 번역 키로 미룰 수 없다.

문구는 `data/translations/combat.json` 의 `combat.corpse_name` 과
`combat.corpse_desc` 에서 옮겨 왔다. 번역 파일이 클라이언트로 이관되어도
이 값은 서버가 보유해야 한다.
"""

from typing import Dict

# {name} 을 사망자 이름으로 치환한다
_NAME_TEMPLATES: Dict[str, str] = {
    "en": "Corpse of {name}",
    "ko": "{name}의 사체",
}

_DESCRIPTION_TEMPLATES: Dict[str, str] = {
    "en": "The lifeless remains of {name}.",
    "ko": "{name}의 시체입니다.",
}


def corpse_name(names: Dict[str, str]) -> Dict[str, str]:
    """시체 이름을 언어별로 만든다.

    Args:
        names: 사망자의 언어별 이름

    Returns:
        언어별 시체 이름
    """
    return _render(_NAME_TEMPLATES, names)


def corpse_description(names: Dict[str, str]) -> Dict[str, str]:
    """시체 설명을 언어별로 만든다."""
    return _render(_DESCRIPTION_TEMPLATES, names)


def _render(templates: Dict[str, str], names: Dict[str, str]) -> Dict[str, str]:
    """템플릿에 이름을 채운다. 없는 언어는 영어 이름으로 대체한다."""
    fallback = names.get("en") or next(iter(names.values()), "")

    return {
        locale: template.format(name=names.get(locale) or fallback)
        for locale, template in templates.items()
    }
