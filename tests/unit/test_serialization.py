"""
직렬화 계층 단위 테스트

계약(docs/protocol/entities.md)에 정의된 페이로드를 실제 모델에서 산출할 수 있는지,
파생 boolean 판정이 기존 명령어 구현과 일치하는지 확인한다.
"""

import json

import pytest

from src.mud_engine.game.models.gameobject import GameObject
from src.mud_engine.game.models.player import Player
from src.mud_engine.game.monster import Monster, MonsterBehavior, MonsterStats, MonsterType
from src.mud_engine.server import serialization as ser


def _make_monster(**overrides):
    """테스트용 몬스터 생성"""
    kwargs = {
        "name": {"en": "Ash Raider", "ko": "재의 약탈자"},
        "description": {"en": "A raider.", "ko": "약탈자다."},
        "monster_type": MonsterType.AGGRESSIVE,
        "behavior": MonsterBehavior.ROAMING,
        "stats": MonsterStats(strength=12, dexterity=14, constitution=10, current_hp=18),
        "faction_id": "wild",
    }
    kwargs.update(overrides)
    return Monster(**kwargs)


def _make_object(**overrides):
    """테스트용 게임 오브젝트 생성"""
    kwargs = {
        "name": {"en": "Health Potion", "ko": "체력 물약"},
        "description": {"en": "Restores health.", "ko": "체력을 회복한다."},
        "location_type": "inventory",
        "location_id": "player-1",
        "properties": {"category": "consumable", "hp_restore": 25, "template_id": "health_potion"},
        "weight": 0.3,
        "max_stack": 10,
    }
    kwargs.update(overrides)
    return GameObject(**kwargs)


class TestLocalizedDict:
    """언어별 dict 처리"""

    def test_keeps_dict_as_is(self):
        """모델의 name dict를 그대로 유지한다"""
        assert ser.localized_dict({"en": "Sword", "ko": "검"}) == {"en": "Sword", "ko": "검"}

    def test_parses_json_string(self):
        """JSON 문자열로 들어온 경우 파싱한다"""
        assert ser.localized_dict('{"en": "Sword", "ko": "검"}') == {"en": "Sword", "ko": "검"}

    def test_returns_empty_for_invalid(self):
        """파싱 불가하면 빈 dict"""
        assert ser.localized_dict("not json") == {}
        assert ser.localized_dict(None) == {}


class TestPropertyCoercion:
    """properties 방어 파싱"""

    def test_dict_passthrough(self):
        assert ser.coerce_properties({"a": 1}) == {"a": 1}

    def test_json_string_parsed(self):
        """BaseModel.to_dict()가 dict를 문자열로 만들기 때문에 필요하다"""
        assert ser.coerce_properties('{"is_container": true}') == {"is_container": True}

    def test_invalid_becomes_empty(self):
        assert ser.coerce_properties("broken") == {}
        assert ser.coerce_properties(None) == {}


class TestDerivedBooleans:
    """파생 boolean 판정

    판정식은 기존 명령어 구현에서 가져온 것이다.
    is_container  = properties.get('is_container', False)
        commands/container_commands.py OpenCommand._is_container, PutCommand._is_container
        commands/use_command.py UseCommand._is_container
    is_readable   = bool(properties.get('readable', {}))
        commands/read_command.py ReadCommand._is_readable
    is_usable     = any(k in properties for k in usable_keys)
        commands/use_command.py

    기존 명령어 클래스를 직접 임포트해 비교하지 않는 이유는 `commands` 패키지가
    순환 임포트로 임포트 불가 상태이기 때문이다. 같은 이유로 기존 테스트
    test_object_commands.py, test_movement_commands.py 도 수집되지 않는다.
    Task 4(액션 디스패처)에서 구조를 재작성하며 해소된다.
    """

    @pytest.mark.parametrize(
        ("properties", "expected"),
        [
            ({}, False),
            ({"is_container": True}, True),
            ({"is_container": False}, False),
            ({"category": "misc"}, False),
            ('{"is_container": true}', True),
            ("broken json", False),
            (None, False),
        ],
    )
    def test_is_container(self, properties, expected):
        assert ser.is_container(properties) is expected

    @pytest.mark.parametrize(
        ("properties", "expected"),
        [
            ({}, False),
            ({"readable": {}}, False),
            ({"readable": {"content": {"ko": "글"}}}, True),
            ({"readable": {"pages": [{"ko": "1쪽"}]}}, True),
            ('{"readable": {"content": {"ko": "글"}}}', True),
            ({"readable": "broken"}, False),
            ("broken json", False),
        ],
    )
    def test_is_readable(self, properties, expected):
        assert ser.is_readable(properties) is expected

    @pytest.mark.parametrize(
        ("properties", "expected"),
        [
            ({}, False),
            ({"hp_restore": 25}, True),
            ({"stamina_restore": 3}, True),
            ({"mana_restore": 10}, True),
            ({"heal_amount": 5}, True),
            ({"category": "weapon"}, False),
        ],
    )
    def test_is_usable_follows_usable_keys(self, properties, expected):
        """사용 판정이 use_command의 usable_keys 목록을 따른다"""
        assert ser.is_usable(properties) is expected


class TestSerializeMonster:
    """몬스터 페이로드"""

    def test_contains_contract_fields(self):
        """계약에 정의된 필드를 담는다"""
        payload = ser.serialize_monster(_make_monster(), viewer_faction="ash_knights")

        assert payload["kind"] == "monster"
        assert payload["name"] == {"en": "Ash Raider", "ko": "재의 약탈자"}
        assert payload["hp"] == 18
        assert payload["max_hp"] == 30  # 10 + constitution(10) * 2
        assert payload["monster_type"] == "aggressive"
        assert payload["behavior"] == "roaming"
        assert payload["is_alive"] is True

    def test_omits_removed_concepts(self):
        """레벨과 상인 여부는 포함하지 않는다"""
        payload = ser.serialize_monster(_make_monster())

        assert "level" not in payload
        assert "is_merchant" not in payload

    def test_provides_strength_indicators(self):
        """레벨 대신 계산 지표를 제공한다"""
        payload = ser.serialize_monster(_make_monster())

        assert payload["armor_class"] == 12  # 10 + (14 - 10) // 2
        assert payload["attack_power"] == 7  # 1 + 12 // 2

    def test_disposition_is_relative_to_viewer(self):
        """disposition은 보는 플레이어 기준으로 계산된다"""
        monster = _make_monster(faction_id="ash_knights")

        friendly = ser.serialize_monster(monster, viewer_faction="ash_knights")
        hostile = ser.serialize_monster(monster, viewer_faction="wild")

        assert friendly["disposition"] == "friendly"
        assert hostile["disposition"] == "hostile"

    def test_can_talk_is_injected(self):
        """can_talk은 호출부가 주입한다"""
        assert ser.serialize_monster(_make_monster(), can_talk=True)["can_talk"] is True
        assert ser.serialize_monster(_make_monster())["can_talk"] is False

    def test_name_is_not_split_into_columns(self):
        """DB 컬럼 형태로 쪼개지 않는다"""
        payload = ser.serialize_monster(_make_monster())

        assert "name_en" not in payload
        assert "name_ko" not in payload


class TestSerializeObject:
    """오브젝트 페이로드"""

    def test_contains_contract_fields(self):
        payload = ser.serialize_object(_make_object())

        assert payload["kind"] == "object"
        assert payload["name"] == {"en": "Health Potion", "ko": "체력 물약"}
        assert payload["weight"] == 0.3
        assert payload["stack_count"] == 1
        assert payload["is_usable"] is True
        assert payload["is_container"] is False
        assert payload["template_id"] == "health_potion"

    def test_omits_max_stack(self):
        """max_stack은 서버가 그에 따라 동작하지 않으므로 보내지 않는다"""
        payload = ser.serialize_object(_make_object())
        assert "max_stack" not in payload

    def test_stack_count_from_quantity(self):
        """stack_count는 properties.quantity를 반영한다. 현재 화폐만 1을 초과한다"""
        currency = _make_object(
            name={"en": "Silver Coin", "ko": "은화"},
            properties={"category": "currency", "quantity": 500},
            max_stack=9999,
        )
        assert ser.serialize_object(currency)["stack_count"] == 500

    @pytest.mark.parametrize(
        ("properties", "expected"),
        [
            ({}, 1),
            ({"quantity": 1}, 1),
            ({"quantity": 500}, 500),
            ({"quantity": 0}, 1),
            ({"quantity": -5}, 1),
            ({"quantity": True}, 1),
            ({"quantity": "많음"}, 1),
            ('{"quantity": 300}', 300),
        ],
    )
    def test_stack_count_edge_cases(self, properties, expected):
        assert ser.stack_count(properties) == expected

    def test_category_comes_from_properties(self):
        """category는 모델 필드가 아니라 properties에서 온다"""
        payload = ser.serialize_object(_make_object())
        assert payload["category"] == "consumable"

    def test_category_defaults_when_absent(self):
        obj = _make_object(properties={"hp_restore": 1})
        assert ser.serialize_object(obj)["category"] == "misc"

    def test_equipment_slot_none_when_not_equippable(self):
        assert ser.serialize_object(_make_object())["equipment_slot"] is None


class TestSerializePlayer:
    """플레이어 페이로드"""

    def test_uses_display_name_fallback(self):
        """display_name이 없으면 username을 쓴다"""
        player = Player(username="nagne", password_hash="hash")
        payload = ser.serialize_player(player)

        assert payload["display_name"] == "nagne"
        assert payload["name"] == {"en": "nagne", "ko": "nagne"}

    def test_prefers_display_name(self):
        player = Player(username="player5426", password_hash="hash", display_name="SUPERADMIN")
        assert ser.serialize_player(player)["display_name"] == "SUPERADMIN"

    def test_omits_coordinates(self):
        """다른 플레이어에게 좌표를 노출하지 않는다"""
        player = Player(username="nagne", password_hash="hash")
        payload = ser.serialize_player(player)

        assert "x" not in payload
        assert "y" not in payload
        assert "last_room_x" not in payload


class TestEnvelope:
    """봉투와 인코딩"""

    def test_build_includes_type(self):
        assert ser.build("room_info")["type"] == "room_info"

    def test_seq_omitted_when_none(self):
        assert "seq" not in ser.build("event")

    def test_seq_included_when_given(self):
        assert ser.build("login_result", seq=7)["seq"] == 7

    def test_encode_has_no_newline(self):
        """JSON 라인 하나에는 개행이 없어야 한다"""
        line = ser.encode(ser.build("event", message={"key": "a.b", "params": {}}))
        assert "\n" not in line
        assert "\r" not in line

    def test_encode_preserves_korean(self):
        """한국어를 이스케이프하지 않는다"""
        line = ser.encode(ser.build("chat", message="안녕하세요"))
        assert "안녕하세요" in line

    def test_encode_escapes_embedded_newline(self):
        """문자열 값의 개행은 이스케이프되어 라인을 깨지 않는다"""
        line = ser.encode(ser.build("chat", message="첫 줄\n둘째 줄"))

        assert "\n" not in line
        assert json.loads(line)["message"] == "첫 줄\n둘째 줄"

    def test_encode_line_terminates_with_newline(self):
        payload = ser.encode_line(ser.build("pong"))

        assert payload.endswith(b"\n")
        assert payload.count(b"\n") == 1

    def test_action_rejected_carries_seq_and_reason(self):
        rejected = ser.action_rejected(
            seq=43, verb="talk", reason_code="NOT_APPLICABLE", message_key="action.cannot_talk"
        )

        assert rejected["type"] == "action_rejected"
        assert rejected["seq"] == 43
        assert rejected["verb"] == "talk"
        assert rejected["reason_code"] == "NOT_APPLICABLE"
        assert rejected["message"]["key"] == "action.cannot_talk"

    def test_error_is_for_protocol_violations(self):
        err = ser.error("MALFORMED_MESSAGE", detail="line is not valid JSON")

        assert err["type"] == "error"
        assert err["reason_code"] == "MALFORMED_MESSAGE"

    def test_message_payload_shape(self):
        payload = ser.message_payload("combat.start", {"monster": {"en": "Rat", "ko": "쥐"}})

        assert payload == {
            "key": "combat.start",
            "params": {"monster": {"en": "Rat", "ko": "쥐"}},
        }
