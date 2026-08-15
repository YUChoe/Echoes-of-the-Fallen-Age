# -*- coding: utf-8 -*-
"""인벤토리와 컨테이너 페이로드 직렬화

서버는 아이템을 묶지 않고 개별 엔티티로 보낸다. 같은 종류가 여럿이면
uuid 가 다른 항목 여러 개가 온다. 묶어 표시하는 것은 클라이언트 규칙이다.

프로토콜 계약: docs/protocol/server-to-client.md
"""

from typing import Any, Iterable, Optional

from ...game.models.gameobject import GameObject
from ...game.models.player import Player


def serialize_equipped_slots(objects: Iterable[GameObject]) -> dict[str, Optional[str]]:
    """장착 슬롯별 uuid 매핑을 만든다.

    빈 슬롯은 담지 않는다. 클라이언트가 표시할 슬롯 목록을 자체 보유하고
    없는 키를 빈 슬롯으로 처리한다. 슬롯 이름을 서버가 확정하지 않는 이유는
    허용값이 16종이고 레거시 값(weapon, armor, accessory)이 섞여 있어서다.
    """
    equipped: dict[str, Optional[str]] = {}

    for obj in objects:
        if not obj.is_equipped or not obj.equipment_slot:
            continue
        equipped[str(obj.equipment_slot)] = str(obj.id)

    return equipped


def build_inventory(
    player: Player,
    objects: list[GameObject],
    gold: int = 0,
    seq: Optional[int] = None,
) -> dict[str, Any]:
    """inventory 메시지를 만든다.

    Args:
        player: 소유 플레이어. 최대 소지 무게 계산에 쓴다
        objects: 인벤토리 오브젝트 목록. 장착 중인 것도 포함한다
        gold: 화폐 합계. CurrencyManager 가 계산한 값을 호출부가 전달한다
        seq: 클라이언트 요청에 대한 응답이면 그 번호
    """
    from .entity import serialize_object
    from .envelope import build

    return build(
        "inventory",
        seq=seq,
        total_weight=round(player.get_current_carry_weight(objects), 2),
        max_weight=round(player.get_max_carry_weight(), 2),
        gold=int(gold),
        items=[serialize_object(obj) for obj in objects],
        equipped=serialize_equipped_slots(objects),
    )


def build_container_contents(
    container_id: str,
    objects: list[GameObject],
    seq: Optional[int] = None,
) -> dict[str, Any]:
    """container_contents 메시지를 만든다.

    컨테이너 내부 아이템도 방과 인벤토리와 같은 오브젝트 스키마를 따른다.
    기존 구현에는 내부 목록을 배열 인덱스로 지정하는 경로가 있었으나
    uuid 로 통일된다.
    """
    from .entity import serialize_object
    from .envelope import build

    return build(
        "container_contents",
        seq=seq,
        container_id=str(container_id),
        items=[serialize_object(obj) for obj in objects],
    )


def build_readable_content(
    object_id: str,
    content: dict[str, str],
    page: int = 1,
    total_pages: int = 1,
    readable_type: str = "note",
    seq: Optional[int] = None,
) -> dict[str, Any]:
    """readable_content 메시지를 만든다.

    `content` 는 언어별 dict 이며 번역 키가 아니다. 책과 두루마리의 본문은 DB
    의 이중언어 컬럼에 담긴 콘텐츠이므로 클라이언트 번역 파일로 옮기지 않는다.
    엔티티 이름·설명과 같은 성질이다.
    """
    from .envelope import build

    return build(
        "readable_content",
        seq=seq,
        object_id=str(object_id),
        readable_type=str(readable_type),
        page=int(page),
        total_pages=int(total_pages),
        content=dict(content),
    )
