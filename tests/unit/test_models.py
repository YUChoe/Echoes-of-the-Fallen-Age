"""
데이터 모델 단위 테스트
"""

import json
import time
import pytest
from datetime import datetime

from src.mud_engine.game.models import Player, Character, Room, GameObject, Session


class TestPlayer:
    """Player 모델 테스트"""

    def test_valid_player_creation(self):
        """유효한 플레이어 생성 테스트"""
        player = Player(
            username="testuser",
            password_hash="hashed_password",
            email="test@example.com",
            preferred_locale="ko"
        )

        assert player.username == "testuser"
        assert player.password_hash == "hashed_password"
        assert player.email == "test@example.com"
        assert player.preferred_locale == "ko"
        assert player.id is not None

    def test_invalid_username(self):
        """잘못된 사용자명 테스트"""
        with pytest.raises(ValueError, match="사용자명은 3-20자의 영문, 숫자, 언더스코어만 허용됩니다"):
            Player(username="ab", password_hash="hash")  # 너무 짧음

        with pytest.raises(ValueError, match="사용자명은 3-20자의 영문, 숫자, 언더스코어만 허용됩니다"):
            Player(username="user@name", password_hash="hash")  # 특수문자 포함

    def test_invalid_email(self):
        """잘못된 이메일 테스트"""
        with pytest.raises(ValueError, match="올바른 이메일 형식이 아닙니다"):
            Player(username="testuser", password_hash="hash", email="invalid-email")

    def test_invalid_locale(self):
        """잘못된 로케일 테스트"""
        with pytest.raises(ValueError, match="지원되지 않는 언어입니다"):
            Player(username="testuser", password_hash="hash", preferred_locale="fr")

    def test_username_validation(self):
        """사용자명 유효성 검사 테스트"""
        assert Player.is_valid_username("validuser123")
        assert Player.is_valid_username("user_name")
        assert not Player.is_valid_username("ab")  # 너무 짧음
        assert not Player.is_valid_username("a" * 21)  # 너무 김
        assert not Player.is_valid_username("user@name")  # 특수문자

    def test_email_validation(self):
        """이메일 유효성 검사 테스트"""
        assert Player.is_valid_email("test@example.com")
        assert Player.is_valid_email("user.name+tag@domain.co.uk")
        assert not Player.is_valid_email("invalid-email")
        assert not Player.is_valid_email("@domain.com")

    def test_to_dict_excludes_password(self):
        """딕셔너리 변환 시 비밀번호 제외 테스트"""
        player = Player(username="testuser", password_hash="secret")
        data = player.to_dict()

        assert "password_hash" not in data
        assert data["username"] == "testuser"

    def test_to_dict_with_password(self):
        """비밀번호 포함 딕셔너리 변환 테스트"""
        player = Player(username="testuser", password_hash="secret")
        data = player.to_dict_with_password()

        assert data["password_hash"] == "secret"
        assert data["username"] == "testuser"


class TestCharacter:
    """Character 모델 테스트"""

    def test_valid_character_creation(self):
        """유효한 캐릭터 생성 테스트"""
        character = Character(
            player_id="player-123",
            name="테스트캐릭터",
            current_room_id="room-001"
        )

        assert character.player_id == "player-123"
        assert character.name == "테스트캐릭터"
        assert character.current_room_id == "room-001"
        assert character.inventory == []
        assert character.stats == {}

    def test_invalid_character_name(self):
        """잘못된 캐릭터 이름 테스트"""
        with pytest.raises(ValueError, match="캐릭터 이름은 2-15자의 한글, 영문, 숫자만 허용됩니다"):
            Character(player_id="player-123", name="a")  # 너무 짧음

        with pytest.raises(ValueError, match="캐릭터 이름은 2-15자의 한글, 영문, 숫자만 허용됩니다"):
            Character(player_id="player-123", name="name@#$")  # 특수문자

    def test_character_name_validation(self):
        """캐릭터 이름 유효성 검사 테스트"""
        assert Character.is_valid_character_name("테스트")
        assert Character.is_valid_character_name("TestChar")
        assert Character.is_valid_character_name("캐릭터123")
        assert Character.is_valid_character_name("Test User")  # 공백 허용
        assert not Character.is_valid_character_name("a")  # 너무 짧음
        assert not Character.is_valid_character_name("a" * 16)  # 너무 김
        assert not Character.is_valid_character_name("test@char")  # 특수문자

    def test_inventory_management(self):
        """인벤토리 관리 테스트"""
        character = Character(player_id="player-123", name="테스트")

        # 아이템 추가
        character.add_to_inventory("item-001")
        assert character.has_in_inventory("item-001")
        assert len(character.inventory) == 1

        # 중복 추가 방지
        character.add_to_inventory("item-001")
        assert len(character.inventory) == 1

        # 아이템 제거
        removed = character.remove_from_inventory("item-001")
        assert removed is True
        assert not character.has_in_inventory("item-001")
        assert len(character.inventory) == 0

        # 존재하지 않는 아이템 제거
        removed = character.remove_from_inventory("item-999")
        assert removed is False

    def test_stats_management(self):
        """스탯 관리 테스트"""
        character = Character(player_id="player-123", name="테스트")

        # 스탯 설정
        character.set_stat("health", 100)
        character.set_stat("mana", 50)

        assert character.get_stat("health") == 100
        assert character.get_stat("mana") == 50
        assert character.get_stat("strength", 10) == 10  # 기본값

    def test_json_serialization(self):
        """JSON 직렬화 테스트"""
        character = Character(
            player_id="player-123",
            name="테스트",
            inventory=["item-001", "item-002"],
            stats={"health": 100, "mana": 50}
        )

        data = character.to_dict()

        # JSON 문자열로 변환되었는지 확인
        assert isinstance(data["inventory"], str)
        assert isinstance(data["stats"], str)

        # 역직렬화 테스트
        restored = Character.from_dict(data)
        assert restored.inventory == ["item-001", "item-002"]
        assert restored.stats == {"health": 100, "mana": 50}


class TestRoom:
    """Room 모델 테스트"""

    def test_valid_room_creation(self):
        """유효한 방 생성 테스트"""
        room = Room(
            name={"en": "Test Room", "ko": "테스트 방"},
            description={"en": "A test room", "ko": "테스트용 방입니다"},
            exits={"north": "room-002", "south": "room-003"}
        )

        assert room.name["en"] == "Test Room"
        assert room.name["ko"] == "테스트 방"
        assert room.exits["north"] == "room-002"

    def test_invalid_room_data(self):
        """잘못된 방 데이터 테스트"""
        with pytest.raises(ValueError, match="방 이름은 최소 하나의 언어로 설정되어야 합니다"):
            Room(name={}, description={})

        with pytest.raises(ValueError, match="올바르지 않은 출구 방향입니다"):
            Room(
                name={"en": "Test"},
                exits={"invalid_direction": "room-002"}
            )

    def test_localized_content(self):
        """다국어 콘텐츠 테스트"""
        room = Room(
            name={"en": "Test Room", "ko": "테스트 방"},
            description={"en": "A test room", "ko": "테스트용 방입니다"}
        )

        assert room.get_localized_name("en") == "Test Room"
        assert room.get_localized_name("ko") == "테스트 방"
        assert room.get_localized_name("fr") == "Test Room"  # 기본값

        assert room.get_localized_description("ko") == "테스트용 방입니다"

    def test_exit_management(self):
        """출구 관리 테스트"""
        room = Room(name={"en": "Test Room"})

        # 출구 추가
        room.add_exit("north", "room-002")
        assert room.get_exit("north") == "room-002"
        assert "north" in room.get_available_exits()

        # 출구 제거
        removed = room.remove_exit("north")
        assert removed is True
        assert room.get_exit("north") is None
        assert "north" not in room.get_available_exits()

        # 존재하지 않는 출구 제거
        removed = room.remove_exit("south")
        assert removed is False

    def test_json_serialization(self):
        """JSON 직렬화 테스트"""
        room = Room(
            name={"en": "Test Room", "ko": "테스트 방"},
            description={"en": "A test room"},
            exits={"north": "room-002"}
        )

        data = room.to_dict()

        # JSON 문자열로 변환되었는지 확인
        assert isinstance(data["name"], str)
        assert isinstance(data["description"], str)
        assert isinstance(data["exits"], str)

        # 역직렬화 테스트
        restored = Room.from_dict(data)
        assert restored.name == {"en": "Test Room", "ko": "테스트 방"}
        assert restored.exits == {"north": "room-002"}


class TestGameObject:
    """GameObject 모델 테스트"""

    def test_valid_object_creation(self):
        """유효한 객체 생성 테스트"""
        obj = GameObject(
            name={"en": "Test Item", "ko": "테스트 아이템"},
            description={"en": "A test item", "ko": "테스트용 아이템입니다"},
            object_type="item",
            location_type="room",
            location_id="room-001"
        )

        assert obj.name["en"] == "Test Item"
        assert obj.object_type == "item"
        assert obj.location_type == "room"
        assert obj.location_id == "room-001"

    def test_invalid_object_data(self):
        """잘못된 객체 데이터 테스트"""
        with pytest.raises(ValueError, match="객체 이름은 최소 하나의 언어로 설정되어야 합니다"):
            GameObject(name={}, object_type="item", location_type="room")

        with pytest.raises(ValueError, match="올바르지 않은 객체 타입입니다"):
            GameObject(
                name={"en": "Test"},
                object_type="invalid_type",
                location_type="room"
            )

        with pytest.raises(ValueError, match="올바르지 않은 위치 타입입니다"):
            GameObject(
                name={"en": "Test"},
                object_type="item",
                location_type="invalid_location"
            )

    def test_localized_content(self):
        """다국어 콘텐츠 테스트"""
        obj = GameObject(
            name={"en": "Test Item", "ko": "테스트 아이템"},
            description={"en": "A test item", "ko": "테스트용 아이템입니다"},
            object_type="item",
            location_type="room"
        )

        assert obj.get_localized_name("en") == "Test Item"
        assert obj.get_localized_name("ko") == "테스트 아이템"
        assert obj.get_localized_description("ko") == "테스트용 아이템입니다"

    def test_property_management(self):
        """속성 관리 테스트"""
        obj = GameObject(
            name={"en": "Test Item"},
            object_type="item",
            location_type="room"
        )

        # 속성 설정
        obj.set_property("weight", 5)
        obj.set_property("durability", 100)

        assert obj.get_property("weight") == 5
        assert obj.get_property("durability") == 100
        assert obj.get_property("value", 0) == 0  # 기본값

    def test_location_management(self):
        """위치 관리 테스트"""
        obj = GameObject(
            name={"en": "Test Item"},
            object_type="item",
            location_type="room",
            location_id="room-001"
        )

        # 방에 있는지 확인
        assert obj.is_in_room("room-001")
        assert not obj.is_in_room("room-002")

        # 인벤토리로 이동
        obj.move_to_inventory("character-001")
        assert obj.location_type == "inventory"
        assert obj.location_id == "character-001"
        assert obj.is_in_inventory("character-001")

        # 방으로 이동
        obj.move_to_room("room-002")
        assert obj.location_type == "room"
        assert obj.location_id == "room-002"
        assert obj.is_in_room("room-002")


class TestSession:
    """Session 모델 테스트"""

    def test_valid_session_creation(self):
        """유효한 세션 생성 테스트"""
        session = Session(
            player_id="player-123",
            character_id="character-456",
            current_room_id="room-001",
            locale="ko"
        )

        assert session.player_id == "player-123"
        assert session.character_id == "character-456"
        assert session.current_room_id == "room-001"
        assert session.locale == "ko"

    def test_invalid_session_data(self):
        """잘못된 세션 데이터 테스트"""
        with pytest.raises(ValueError, match="플레이어 ID는 필수입니다"):
            Session(player_id="", character_id="character-456")

        with pytest.raises(ValueError, match="지원되지 않는 언어입니다"):
            Session(
                player_id="player-123",
                character_id="character-456",
                locale="fr"
            )

    def test_activity_management(self):
        """활동 관리 테스트"""
        session = Session(
            player_id="player-123",
            character_id="character-456"
        )

        # 활동 업데이트
        old_activity = session.last_activity
        time.sleep(0.001)
        session.update_activity()
        assert session.last_activity > old_activity

        # 활성 상태 확인
        assert session.is_active(timeout_minutes=30)

    def test_to_dict_excludes_websocket(self):
        """딕셔너리 변환 시 WebSocket 제외 테스트"""
        session = Session(
            player_id="player-123",
            character_id="character-456",
            websocket="mock_websocket"
        )

        data = session.to_dict()
        assert "websocket" not in data
        assert data["player_id"] == "player-123"


if __name__ == "__main__":
    # 간단한 테스트 실행
    print("🧪 모델 기본 테스트 실행...")

    try:
        # Player 테스트
        player = Player(username="testuser", password_hash="hash123")
        print(f"✅ Player 생성: {player.username}")

        # Character 테스트
        character = Character(player_id=player.id, name="테스트캐릭터")
        character.add_to_inventory("item-001")
        character.set_stat("health", 100)
        print(f"✅ Character 생성: {character.name}")

        # Room 테스트
        room = Room(
            name={"en": "Test Room", "ko": "테스트 방"},
            description={"en": "A test room", "ko": "테스트용 방입니다"}
        )
        room.add_exit("north", "room-002")
        print(f"✅ Room 생성: {room.get_localized_name('ko')}")

        # GameObject 테스트
        obj = GameObject(
            name={"en": "Test Sword", "ko": "테스트 검"},
            object_type="weapon",
            location_type="room",
            location_id=room.id
        )
        obj.set_property("damage", 10)
        print(f"✅ GameObject 생성: {obj.get_localized_name('ko')}")

        # Session 테스트
        session = Session(
            player_id=player.id,
            character_id=character.id,
            current_room_id=room.id,
            locale="ko"
        )
        print(f"✅ Session 생성: {session.id}")

        print("🎉 모든 기본 테스트 통과!")

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        raise