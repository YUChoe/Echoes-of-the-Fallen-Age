#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""하니스 전제 조건 준비

액션 시나리오는 전제 조건이 없으면 건너뛴다. 적대 몬스터, 컨테이너, 읽을 수
있는 아이템이 테스트 계정 사거리에 있어야 하고 몬스터는 로밍한다. 그래서 실행할
때마다 커버리지가 달라졌다.

어드민 채널로 필요한 것을 직접 만들어 커버리지를 결정적으로 만든다. 프로덕션
데이터를 건드리지 않도록 좌표 -9990 에 전용 방을 만들고 끝나면 지운다.

프로덕션 몬스터와 아이템을 옮기지 않는다. 템플릿으로 새로 스폰한다.
"""

import logging
from typing import Any, Optional

from .client import DEFAULT_ADMIN_PORT, HarnessClient, HarnessError

logger = logging.getLogger(__name__)

# 하니스 전용 좌표. 프로덕션 방과 겹치지 않는다
FIXTURE_X = -9990
FIXTURE_Y = -9990
FIXTURE_ROOM_TYPE = "harness_fixture"

# 스폰할 템플릿. 실제 존재하는 것만 쓴다
HOSTILE_TEMPLATE = "template_forest_goblin"


class Fixture:
    """어드민 채널로 만든 검증용 방과 그 안의 내용물.

    `close()` 를 부르면 만든 것을 모두 지운다. 실패해도 지우려 시도한다.
    """

    def __init__(self, admin_port: int = DEFAULT_ADMIN_PORT) -> None:
        self._admin_port = admin_port
        self._admin: Optional[HarnessClient] = None
        self.room_id: Optional[str] = None
        self.spawned: list[str] = []
        self.connections: list[str] = []
        self.reason: str = ""

    # 준비 -------------------------------------------------------------------

    def open(self, username: str, password: str) -> bool:
        """어드민 채널에 붙어 검증용 방을 만든다.

        Returns:
            준비 성공 여부. 실패하면 `reason` 에 이유가 담긴다
        """
        try:
            self._admin = HarnessClient(
                port=self._admin_port, verbose=False, filter_telnet=False
            )
            self._admin.connect()
            self._admin.wait_for("welcome", timeout_ms=3000)

            seq = self._admin.send_json(
                {"type": "admin_login", "username": username, "password": password}
            )
            login = self._admin.wait_for(
                "admin_login_result", seq=seq, timeout_ms=5000
            )

            if login.get("success") is not True:
                self.reason = "어드민 인증에 실패했다"
                return False

            self.room_id = self._create_room()
            return self.room_id is not None
        except HarnessError as exc:
            self.reason = f"어드민 채널 준비 실패: {exc}"
            return False

    def _create_room(self) -> Optional[str]:
        """검증용 방을 만든다. 이미 있으면 그것을 쓴다."""
        assert self._admin is not None

        seq = self._admin.send_json(
            {
                "type": "admin_action",
                "action": "create_room",
                "params": {
                    "x": FIXTURE_X,
                    "y": FIXTURE_Y,
                    "room_type": FIXTURE_ROOM_TYPE,
                    "description_en": "Harness fixture room.",
                    "description_ko": "하니스 검증용 방.",
                },
            }
        )

        try:
            created = self._admin.wait_for(
                "admin_action_result", seq=seq, timeout_ms=8000
            )
        except HarnessError as exc:
            self.reason = f"검증용 방 생성 실패: {exc}"
            return None

        room_id = (created.get("data") or {}).get("room_id")

        if not isinstance(room_id, str):
            self.reason = f"방 생성 응답에 room_id 가 없다: {created.get('data')!r}"
            return None

        return room_id

    def spawn_hostile(self) -> Optional[str]:
        """적대 몬스터를 하나 스폰한다.

        Returns:
            몬스터 uuid. 실패하면 None
        """
        data = self._action(
            "spawn_monster",
            {"template_id": HOSTILE_TEMPLATE, "x": FIXTURE_X, "y": FIXTURE_Y},
        )

        if data is None:
            return None

        monster_id = data.get("monster_id")

        if isinstance(monster_id, str):
            self.spawned.append(monster_id)
            return monster_id

        return None

    def spawn_item(self, template_id: str) -> Optional[str]:
        """아이템을 방에 스폰한다.

        Returns:
            오브젝트 uuid. 실패하면 None
        """
        data = self._action(
            "spawn_item",
            {"template_id": template_id, "x": FIXTURE_X, "y": FIXTURE_Y},
        )

        if data is None:
            return None

        object_id = data.get("object_id")

        if isinstance(object_id, str):
            self.spawned.append(object_id)
            return object_id

        return None

    def item_templates(self) -> list[str]:
        """사용 가능한 아이템 템플릿 목록."""
        data = self._action("list_item_templates", {})
        templates = (data or {}).get("templates")
        return templates if isinstance(templates, list) else []

    def create_container(self) -> Optional[str]:
        """빈 컨테이너를 방에 만든다.

        템플릿으로는 만들 수 없다. `configs/items/` 의 어떤 템플릿도
        `is_container` 를 설정하지 않으며, 직렬화 계층은 그 키만 본다.
        """
        return self._create_object(
            "Harness Box",
            "하니스 상자",
            {"is_container": True, "max_capacity": 10},
        )

    def create_usable(self) -> Optional[str]:
        """사용할 수 있는 아이템을 방에 만든다.

        직렬화 계층은 `hp_restore` 등 네 키 중 하나가 있으면 사용 가능으로 본다.
        """
        return self._create_object(
            "Harness Tonic",
            "하니스 물약",
            {"hp_restore": 1},
        )

    def create_heavy(self) -> Optional[str]:
        """들 수 없을 만큼 무거운 아이템을 만든다. `INVENTORY_FULL` 용이다."""
        return self._create_object(
            "Harness Anvil",
            "하니스 모루",
            {},
            weight=9999.0,
        )

    def create_stack(self, count: int = 2) -> Optional[str]:
        """수량이 있는 아이템을 만든다. `INSUFFICIENT_QUANTITY` 용이다."""
        return self._create_object(
            "Harness Pebbles",
            "하니스 조약돌",
            {"stack_count": count},
            max_stack=10,
        )

    def create_readable(self) -> Optional[str]:
        """읽을 수 있는 아이템을 방에 만든다."""
        return self._create_object(
            "Harness Note",
            "하니스 쪽지",
            {
                "readable": {
                    "type": "note",
                    "content": {
                        "en": "A harness note. Nothing of consequence.",
                        "ko": "하니스 쪽지다. 대단한 내용은 없다.",
                    },
                }
            },
        )

    def _create_object(
        self,
        name_en: str,
        name_ko: str,
        properties: dict[str, Any],
        weight: float = 0.5,
        max_stack: int = 1,
    ) -> Optional[str]:
        """방에 오브젝트를 직접 만든다. 어드민 CRUD 를 쓴다."""
        if self._admin is None or self.room_id is None:
            return None

        try:
            seq = self._admin.send_json(
                {
                    "type": "admin_create",
                    "resource": "objects",
                    "values": {
                        "name_en": name_en,
                        "name_ko": name_ko,
                        "description_en": "Created by the harness.",
                        "description_ko": "하니스가 만들었다.",
                        "location_type": "room",
                        "location_id": self.room_id,
                        "properties": properties,
                        "weight": weight,
                        "max_stack": max_stack,
                    },
                }
            )
            created = self._admin.wait_for(
                "admin_mutate_result", seq=seq, timeout_ms=8000
            )
        except HarnessError as exc:
            logger.warning(f"오브젝트 생성 실패 ({name_en}): {exc}")
            return None

        object_id = (created.get("key") or {}).get("id")

        if isinstance(object_id, str):
            self.spawned.append(object_id)
            return object_id

        return None

    def create_passage(self, to_x: int, to_y: int) -> bool:
        """검증용 방에서 지정 좌표로 가는 통로를 만든다.

        `enter` 는 현재 좌표의 `room_connections` 항목을 조회해 이동한다. 방향
        출구와 달리 좌표가 인접하지 않아도 된다.
        """
        if self._admin is None:
            return False

        try:
            seq = self._admin.send_json(
                {
                    "type": "admin_create",
                    "resource": "room_connections",
                    "values": {
                        "from_x": FIXTURE_X,
                        "from_y": FIXTURE_Y,
                        "to_x": to_x,
                        "to_y": to_y,
                    },
                }
            )
            created = self._admin.wait_for(
                "admin_mutate_result", seq=seq, timeout_ms=8000
            )
        except HarnessError as exc:
            logger.warning(f"통로 생성 실패: {exc}")
            return False

        connection_id = (created.get("key") or {}).get("id")

        if isinstance(connection_id, str):
            self.connections.append(connection_id)
            return True

        return False

    def send_player(self, username: str) -> bool:
        """플레이어를 검증용 방으로 옮긴다."""
        return self.send_player_to(username, FIXTURE_X, FIXTURE_Y)

    def send_player_to(self, username: str, x: int, y: int) -> bool:
        """플레이어를 지정한 좌표로 옮긴다.

        검증이 끝나면 원래 좌표로 돌려보내는 데 쓴다. 방을 지우기 전에 빼내지
        않으면 사라진 방에 갇힌다.
        """
        data = self._action("goto", {"target_player": username, "x": x, "y": y})
        return data is not None

    # 정리 -------------------------------------------------------------------

    def close(self) -> None:
        """만든 것을 모두 지운다. 실패해도 계속 진행한다."""
        if self._admin is None:
            return

        for target_id in reversed(self.spawned):
            self._action("terminate", {"target_id": target_id})

        for connection_id in reversed(self.connections):
            self._delete("room_connections", connection_id)

        if self.room_id is not None:
            self._delete_room(self.room_id)

        self._admin.close()
        self._admin = None

    def _delete_room(self, room_id: str) -> None:
        """검증용 방을 지운다."""
        self._delete("rooms", room_id)

    def _delete(self, resource: str, record_id: str) -> None:
        """어드민 CRUD 로 행을 지운다. 실패해도 계속 진행한다."""
        if self._admin is None:
            return

        try:
            seq = self._admin.send_json(
                {"type": "admin_delete", "resource": resource, "id": record_id}
            )
            self._admin.wait_for("admin_mutate_result", seq=seq, timeout_ms=8000)
        except HarnessError as exc:
            logger.warning(f"{resource} 삭제 실패 ({record_id}): {exc}")

    # 보조 -------------------------------------------------------------------

    def _action(
        self, action: str, params: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """어드민 액션을 보내고 data 를 돌려준다. 실패하면 None."""
        if self._admin is None:
            return None

        try:
            seq = self._admin.send_json(
                {"type": "admin_action", "action": action, "params": params}
            )
            reply = self._admin.wait_for(
                "admin_action_result", seq=seq, timeout_ms=8000
            )
            return reply.get("data") or {}
        except HarnessError as exc:
            logger.warning(f"어드민 액션 실패 ({action}): {exc}")
            return None

    def __enter__(self) -> "Fixture":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
