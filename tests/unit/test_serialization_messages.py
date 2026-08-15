"""
메시지 빌더 단위 테스트

room_info, combat_state, inventory, player_state 페이로드가 계약을 따르는지 확인한다.
계약: docs/protocol/server-to-client.md
"""

import json

import pytest

from src.mud_engine.game.combatant import Combatant, CombatantType
from src.mud_engine.game.models.gameobject import GameObject
from src.mud_engine.game.models.player import Player
from src.mud_engine.game.models.room import Room
from src.mud_engine.server import serialization as ser


def _make_room(**overrides):
    kwargs = {
        "description": {"en": "A wide plaza.", "ko": "넓은 광장이다."},
        "x": 0,
        "y": 7,
        "room_type": "gate",
        "blocked_exits": ["west"],
    }
    kwargs.update(overrides)
    return Room(**kwargs)


def _make_player(**overrides):
    kwargs = {"username": "player5426", "password_hash": "hash"}
    kwargs.update(overrides)
    return Player(**kwargs)


def _make_object(**overrides):
    kwargs = {
        "name": {"en": "Iron Sword", "ko": "철검"},
        "description": {"en": "", "ko": ""},
        "location_type": "inventory",
        "location_id": "player-1",
        "properties": {"category": "weapon"},
        "weight": 1.5,
    }
    kwargs.update(overrides)
    return GameObject(**kwargs)


def _make_combatant(combatant_type=CombatantType.MONSTER, **overrides):
    kwargs = {
        "id": "combatant-1",
        "name": "Ash Raider",
        "combatant_type": combatant_type,
        "agility": 14,
        "max_hp": 30,
        "current_hp": 18,
        "attack_power": 6,
        "defense": 3,
    }
    kwargs.update(overrides)
    return Combatant(**kwargs)


class _StubCombat:
    """CombatInstance 대역

    game.combat 은 combat_handler 를 거쳐 자신에게 돌아오는 순환 임포트가 있어
    테스트에서 직접 임포트할 수 없다. build_combat_state 가 사용하는 속성만
    갖춘 대역을 쓴다. 민첩 내림차순 턴 순서 규칙도 재현한다.
    """

    def __init__(self, combatants, turn_number=1, is_active=True):
        self.id = "combat-1"
        self.combatants = combatants
        self.turn_number = turn_number
        self.is_active = is_active
        self.current_turn_index = 0
        self.turn_order = [
            c.id for c in sorted(combatants, key=lambda c: c.agility, reverse=True)
        ]

    def get_current_combatant(self):
        if not self.turn_order or self.current_turn_index >= len(self.turn_order):
            return None
        current_id = self.turn_order[self.current_turn_index]
        for combatant in self.combatants:
            if combatant.id == current_id:
                return combatant
        return None


class TestSerializeRoom:
    """방 정보"""

    def test_contains_contract_fields(self):
        payload = ser.serialize_room(_make_room(), exits=["north", "east"], has_passage=True)

        assert payload["x"] == 0
        assert payload["y"] == 7
        assert payload["room_type"] == "gate"
        assert payload["description"] == {"en": "A wide plaza.", "ko": "넓은 광장이다."}
        assert payload["exits"] == ["north", "east"]
        assert payload["blocked_exits"] == ["west"]
        assert payload["has_passage"] is True

    def test_omits_name(self):
        """rooms 테이블에 이름 컬럼이 없으므로 제공하지 않는다"""
        payload = ser.serialize_room(_make_room(), exits=[])
        assert "name" not in payload

    def test_unknown_room_type_fallback(self):
        payload = ser.serialize_room(_make_room(room_type=""), exits=[])
        assert payload["room_type"] == ser.UNKNOWN_ROOM_TYPE

    def test_has_passage_defaults_false(self):
        payload = ser.serialize_room(_make_room(), exits=[])
        assert payload["has_passage"] is False


class TestNearbyRooms:
    """미니맵용 주변 방"""

    def test_contains_only_coordinates_and_terrain(self):
        rooms = [_make_room(x=1, y=2, room_type="forest")]
        payload = ser.serialize_nearby_rooms(rooms)

        assert payload == [{"x": 1, "y": 2, "room_type": "forest"}]

    def test_excludes_rooms_without_coordinates(self):
        """좌표가 없으면 렌더링할 수 없으므로 제외한다"""
        rooms = [_make_room(x=None, y=None), _make_room(x=3, y=4)]
        payload = ser.serialize_nearby_rooms(rooms)

        assert len(payload) == 1
        assert payload[0]["x"] == 3


class TestBuildRoomInfo:
    """room_info 메시지"""

    def test_message_shape(self):
        message = ser.build_room_info(
            room=_make_room(),
            exits=["north"],
            entities=[],
            nearby_rooms=[_make_room(x=0, y=8)],
            time_of_day="day",
            has_passage=False,
        )

        assert message["type"] == "room_info"
        assert message["time_of_day"] == "day"
        assert message["entities"] == []
        assert len(message["nearby_rooms"]) == 1

    def test_encodes_to_single_line(self):
        """직렬화 결과가 개행 없는 한 줄이어야 한다"""
        message = ser.build_room_info(
            room=_make_room(),
            exits=["north"],
            entities=[],
            nearby_rooms=[],
            time_of_day="night",
        )
        line = ser.encode(message)

        assert "\n" not in line
        assert json.loads(line)["room"]["description"]["ko"] == "넓은 광장이다."


class TestSerializeCombatant:
    """전투 참가자"""

    def test_uses_defense_not_armor_class(self):
        """Combatant는 armor_class를 갖지 않는다"""
        payload = ser.serialize_combatant(_make_combatant())

        assert payload["defense"] == 3
        assert "armor_class" not in payload

    def test_hp_fields(self):
        payload = ser.serialize_combatant(_make_combatant())

        assert payload["hp"] == 18
        assert payload["max_hp"] == 30
        assert payload["is_alive"] is True

    def test_dead_combatant(self):
        payload = ser.serialize_combatant(_make_combatant(current_hp=0))
        assert payload["is_alive"] is False

    def test_player_name_duplicated_across_locales(self):
        """Combatant.name은 문자열이므로 양쪽 언어에 복제한다"""
        payload = ser.serialize_combatant(
            _make_combatant(combatant_type=CombatantType.PLAYER, name="나그네")
        )

        assert payload["name"] == {"en": "나그네", "ko": "나그네"}
        assert payload["combatant_type"] == "player"

    def test_monster_name_from_data(self):
        """몬스터는 data['monster']의 언어별 dict를 사용한다"""

        class _StubMonster:
            name = {"en": "Ash Raider", "ko": "재의 약탈자"}

        combatant = _make_combatant(data={"monster": _StubMonster()})
        payload = ser.serialize_combatant(combatant)

        assert payload["name"] == {"en": "Ash Raider", "ko": "재의 약탈자"}

    def test_falls_back_when_monster_missing(self):
        payload = ser.serialize_combatant(_make_combatant(data={}))
        assert payload["name"] == {"en": "Ash Raider", "ko": "Ash Raider"}


class TestBuildCombatState:
    """combat_state 메시지"""

    def _combat(self):
        player = _make_combatant(
            combatant_type=CombatantType.PLAYER, id="player-1", name="나그네", agility=20
        )
        monster = _make_combatant(id="monster-1", agility=10)
        return _StubCombat([player, monster])

    def test_splits_allies_and_enemies(self):
        message = ser.build_combat_state(self._combat(), viewer_id="player-1")

        assert len(message["allies"]) == 1
        assert len(message["enemies"]) == 1
        assert message["allies"][0]["combatant_type"] == "player"
        assert message["enemies"][0]["combatant_type"] == "monster"

    def test_turn_order_by_agility(self):
        """민첩이 높은 순서로 턴이 정해진다"""
        message = ser.build_combat_state(self._combat(), viewer_id="player-1")

        assert message["turn_order"] == ["player-1", "monster-1"]
        assert message["current_turn"] == "player-1"

    def test_is_my_turn(self):
        combat = self._combat()

        assert ser.build_combat_state(combat, viewer_id="player-1")["is_my_turn"] is True
        assert ser.build_combat_state(combat, viewer_id="monster-1")["is_my_turn"] is False

    def test_is_over_reflects_is_active(self):
        combat = self._combat()
        assert ser.build_combat_state(combat, viewer_id="player-1")["is_over"] is False

        combat.is_active = False
        assert ser.build_combat_state(combat, viewer_id="player-1")["is_over"] is True

    def test_round_uses_turn_number(self):
        combat = self._combat()
        combat.turn_number = 3

        assert ser.build_combat_state(combat, viewer_id="player-1")["round"] == 3


class TestBuildInventory:
    """inventory 메시지"""

    def test_weight_and_items(self):
        player = _make_player()
        objects = [_make_object(), _make_object(weight=2.0)]

        message = ser.build_inventory(player, objects, silver=1240)

        assert message["type"] == "inventory"
        assert message["total_weight"] == 3.5
        assert message["max_weight"] > 0
        assert message["silver"] == 1240
        assert len(message["items"]) == 2

    def test_equipped_slots(self):
        equipped = _make_object(equipment_slot="right_hand", is_equipped=True)
        carried = _make_object()

        message = ser.build_inventory(_make_player(), [equipped, carried])

        assert message["equipped"] == {"right_hand": str(equipped.id)}

    def test_unequipped_item_not_in_slots(self):
        obj = _make_object(equipment_slot="right_hand", is_equipped=False)
        message = ser.build_inventory(_make_player(), [obj])

        assert message["equipped"] == {}

    def test_container_contents(self):
        message = ser.build_container_contents("container-1", [_make_object()], seq=50)

        assert message["type"] == "container_contents"
        assert message["seq"] == 50
        assert message["container_id"] == "container-1"
        assert len(message["items"]) == 1


class TestBuildPlayerState:
    """player_state 메시지"""

    def test_contains_contract_fields(self):
        player = _make_player(display_name="SUPERADMIN")

        message = ser.build_player_state(
            player,
            room_id="room-1",
            stamina=3.5,
            max_stamina=5.0,
            silver=1240,
            in_combat=True,
        )
        payload = message["player"]

        assert message["type"] == "player_state"
        assert payload["display_name"] == "SUPERADMIN"
        assert payload["room_id"] == "room-1"
        assert payload["stamina"] == 3.5
        assert payload["max_stamina"] == 5.0
        assert payload["silver"] == 1240
        assert payload["in_combat"] is True
        assert payload["in_dialogue"] is False
        assert payload["following"] is None

    def test_primary_stats_exposed(self):
        payload = ser.build_player_state(_make_player())["player"]

        assert set(payload["stats"]) == {
            "strength",
            "dexterity",
            "intelligence",
            "wisdom",
            "constitution",
            "charisma",
        }

    def test_hp_from_current_values(self):
        """HP의 진실은 PlayerStats.current_values['hp']이다"""
        player = _make_player()
        payload = ser.build_player_state(player)["player"]

        assert payload["hp"] == player.stats.get_current_hp()
        assert payload["max_hp"] > 0

    def test_coordinates_from_last_room(self):
        player = _make_player(last_room_x=3, last_room_y=-2)
        payload = ser.build_player_state(player)["player"]

        assert payload["x"] == 3
        assert payload["y"] == -2

    def test_omits_password_hash(self):
        payload = ser.build_player_state(_make_player())["player"]
        assert "password_hash" not in payload


class TestMessagesAreSingleLine:
    """모든 메시지가 개행 없는 한 줄로 인코딩되어야 한다"""

    @pytest.mark.parametrize(
        "message_factory",
        [
            lambda: ser.build_room_info(
                room=_make_room(), exits=["north"], entities=[], nearby_rooms=[], time_of_day="day"
            ),
            lambda: ser.build_inventory(_make_player(), [_make_object()]),
            lambda: ser.build_player_state(_make_player()),
            lambda: ser.build_container_contents("c-1", [_make_object()]),
        ],
    )
    def test_encodes_without_newline(self, message_factory):
        line = ser.encode(message_factory())

        assert "\n" not in line
        assert json.loads(line)["type"]
