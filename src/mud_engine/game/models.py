"""
핵심 데이터 모델 클래스들
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..database.repository import BaseModel
from ..config import Config


@dataclass
class Player(BaseModel):
    """플레이어 모델"""

    id: str = field(default_factory=lambda: str(uuid4()))
    username: str = ""
    password_hash: str = ""
    email: Optional[str] = None
    preferred_locale: str = "en"
    is_admin: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None

    def __post_init__(self):
        """초기화 후 검증"""
        self.validate()

    def validate(self) -> None:
        """플레이어 데이터 유효성 검증"""
        if not self.username:
            raise ValueError("사용자명은 필수입니다")

        if not self.is_valid_username(self.username):
            raise ValueError("사용자명은 3-20자의 영문, 숫자, 언더스코어만 허용됩니다")

        if not self.password_hash:
            raise ValueError("비밀번호 해시는 필수입니다")

        if self.email and not self.is_valid_email(self.email):
            raise ValueError("올바른 이메일 형식이 아닙니다")

        if self.preferred_locale not in ["en", "ko"]:
            raise ValueError("지원되지 않는 언어입니다 (en, ko만 지원)")

    @staticmethod
    def is_valid_username(username: str) -> bool:
        """사용자명 유효성 검사"""
        if not username:
            return False

        min_length = Config.USERNAME_MIN_LENGTH
        max_length = Config.USERNAME_MAX_LENGTH

        if len(username) < min_length or len(username) > max_length:
            return False

        return re.match(r'^[a-zA-Z0-9_]+$', username) is not None

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """이메일 유효성 검사"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (비밀번호 해시 제외)"""
        data = super().to_dict()
        # 보안상 비밀번호 해시는 일반 직렬화에서 제외
        if 'password_hash' in data:
            del data['password_hash']
        return data

    def to_dict_with_password(self) -> Dict[str, Any]:
        """비밀번호 해시 포함 딕셔너리 변환 (데이터베이스 저장용)"""
        return super().to_dict()


@dataclass
class Character(BaseModel):
    """캐릭터 모델"""

    id: str = field(default_factory=lambda: str(uuid4()))
    player_id: str = ""
    name: str = ""
    current_room_id: Optional[str] = None
    inventory: List[str] = field(default_factory=list)  # 객체 ID 목록
    stats: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """초기화 후 검증"""
        self.validate()

    def validate(self) -> None:
        """캐릭터 데이터 유효성 검증"""
        if not self.player_id:
            raise ValueError("플레이어 ID는 필수입니다")

        if not self.name:
            raise ValueError("캐릭터 이름은 필수입니다")

        if not self.is_valid_character_name(self.name):
            raise ValueError("캐릭터 이름은 2-15자의 한글, 영문, 숫자만 허용됩니다")

        if not isinstance(self.inventory, list):
            raise ValueError("인벤토리는 리스트 형태여야 합니다")

        if not isinstance(self.stats, dict):
            raise ValueError("스탯은 딕셔너리 형태여야 합니다")

    @staticmethod
    def is_valid_character_name(name: str) -> bool:
        """캐릭터 이름 유효성 검사"""
        if not name or len(name) < 2 or len(name) > 15:
            return False
        # 한글, 영문, 숫자 허용
        return re.match(r'^[가-힣a-zA-Z0-9\s]+$', name) is not None

    def add_to_inventory(self, object_id: str) -> None:
        """인벤토리에 객체 추가"""
        if object_id not in self.inventory:
            self.inventory.append(object_id)

    def remove_from_inventory(self, object_id: str) -> bool:
        """인벤토리에서 객체 제거"""
        if object_id in self.inventory:
            self.inventory.remove(object_id)
            return True
        return False

    def has_in_inventory(self, object_id: str) -> bool:
        """인벤토리에 객체가 있는지 확인"""
        return object_id in self.inventory

    def get_stat(self, stat_name: str, default: Any = 0) -> Any:
        """스탯 값 조회"""
        return self.stats.get(stat_name, default)

    def set_stat(self, stat_name: str, value: Any) -> None:
        """스탯 값 설정"""
        self.stats[stat_name] = value

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        data = super().to_dict()
        # 리스트와 딕셔너리는 JSON 문자열로 변환
        if isinstance(data.get('inventory'), list):
            data['inventory'] = json.dumps(data['inventory'], ensure_ascii=False)
        if isinstance(data.get('stats'), dict):
            data['stats'] = json.dumps(data['stats'], ensure_ascii=False)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Character':
        """딕셔너리에서 모델 생성"""
        # JSON 문자열을 파이썬 객체로 변환
        if isinstance(data.get('inventory'), str):
            try:
                data['inventory'] = json.loads(data['inventory'])
            except (json.JSONDecodeError, TypeError):
                data['inventory'] = []

        if isinstance(data.get('stats'), str):
            try:
                data['stats'] = json.loads(data['stats'])
            except (json.JSONDecodeError, TypeError):
                data['stats'] = {}

        return cls(**data)


@dataclass
class Room(BaseModel):
    """방 모델"""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: Dict[str, str] = field(default_factory=dict)  # {'en': 'name', 'ko': '이름'}
    description: Dict[str, str] = field(default_factory=dict)
    exits: Dict[str, str] = field(default_factory=dict)  # {'north': 'room_id'}
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """초기화 후 검증"""
        self.validate()

    def validate(self) -> None:
        """방 데이터 유효성 검증"""
        if not isinstance(self.name, dict):
            raise ValueError("방 이름은 딕셔너리 형태여야 합니다")

        if not self.name.get('en') and not self.name.get('ko'):
            raise ValueError("방 이름은 최소 하나의 언어로 설정되어야 합니다")

        if not isinstance(self.description, dict):
            raise ValueError("방 설명은 딕셔너리 형태여야 합니다")

        if not isinstance(self.exits, dict):
            raise ValueError("출구는 딕셔너리 형태여야 합니다")

        # 출구 방향 검증
        valid_directions = {'north', 'south', 'east', 'west', 'up', 'down', 'northeast', 'northwest', 'southeast', 'southwest'}
        for direction in self.exits.keys():
            if direction not in valid_directions:
                raise ValueError(f"올바르지 않은 출구 방향입니다: {direction}")

    def get_localized_name(self, locale: str = 'en') -> str:
        """로케일에 따른 방 이름 반환"""
        return self.name.get(locale, self.name.get('en', self.name.get('ko', 'Unknown Room')))

    def get_localized_description(self, locale: str = 'en') -> str:
        """로케일에 따른 방 설명 반환"""
        return self.description.get(locale, self.description.get('en', self.description.get('ko', 'No description available.')))

    def add_exit(self, direction: str, room_id: str) -> None:
        """출구 추가"""
        valid_directions = {'north', 'south', 'east', 'west', 'up', 'down', 'northeast', 'northwest', 'southeast', 'southwest'}
        if direction not in valid_directions:
            raise ValueError(f"올바르지 않은 출구 방향입니다: {direction}")
        self.exits[direction] = room_id
        self.updated_at = datetime.now()

    def remove_exit(self, direction: str) -> bool:
        """출구 제거"""
        if direction in self.exits:
            del self.exits[direction]
            self.updated_at = datetime.now()
            return True
        return False

    def get_exit(self, direction: str) -> Optional[str]:
        """특정 방향의 출구 방 ID 반환"""
        return self.exits.get(direction)

    def get_available_exits(self) -> List[str]:
        """사용 가능한 출구 방향 목록 반환"""
        return list(self.exits.keys())

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (데이터베이스 스키마에 맞게)"""
        data = super().to_dict()

        # name과 description을 개별 컬럼으로 분리하고 원본 제거
        if 'name' in data:
            name_dict = data.pop('name')
            # BaseModel에서 이미 JSON 문자열로 변환된 경우 다시 파싱
            if isinstance(name_dict, str):
                try:
                    name_dict = json.loads(name_dict)
                except (json.JSONDecodeError, TypeError):
                    name_dict = {}
            data['name_en'] = name_dict.get('en', '') if isinstance(name_dict, dict) else ''
            data['name_ko'] = name_dict.get('ko', '') if isinstance(name_dict, dict) else ''

        if 'description' in data:
            desc_dict = data.pop('description')
            # BaseModel에서 이미 JSON 문자열로 변환된 경우 다시 파싱
            if isinstance(desc_dict, str):
                try:
                    desc_dict = json.loads(desc_dict)
                except (json.JSONDecodeError, TypeError):
                    desc_dict = {}
            data['description_en'] = desc_dict.get('en', '') if isinstance(desc_dict, dict) else ''
            data['description_ko'] = desc_dict.get('ko', '') if isinstance(desc_dict, dict) else ''

        # exits는 JSON 문자열로 유지 (BaseModel에서 이미 변환됨)
        # 추가 처리 불필요

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Room':
        """딕셔너리에서 모델 생성"""
        # 데이터베이스 컬럼명이나 JSON 문자열을 모델 필드로 변환
        converted_data = data.copy()

        # name, description, exits가 JSON 문자열인 경우 딕셔너리로 변환
        for key in ['name', 'description', 'exits']:
            value = converted_data.get(key)
            if isinstance(value, str):
                try:
                    converted_data[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    converted_data[key] = {}

        # DB 컬럼명 (name_en, name_ko 등)을 딕셔너리 필드로 통합
        if 'name' not in converted_data:
            converted_data['name'] = {}
        if 'description' not in converted_data:
            converted_data['description'] = {}

        if 'name_en' in converted_data:
            converted_data['name']['en'] = converted_data.pop('name_en')
        if 'name_ko' in converted_data:
            converted_data['name']['ko'] = converted_data.pop('name_ko')
        if 'description_en' in converted_data:
            converted_data['description']['en'] = converted_data.pop('description_en')
        if 'description_ko' in converted_data:
            converted_data['description']['ko'] = converted_data.pop('description_ko')

        # 날짜 필드 처리 (문자열을 datetime 객체로 변환)
        for date_field in ['created_at', 'updated_at']:
            if date_field in converted_data and isinstance(converted_data[date_field], str):
                try:
                    from datetime import datetime
                    converted_data[date_field] = datetime.fromisoformat(converted_data[date_field].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    # 파싱 실패 시 현재 시간으로 설정
                    converted_data[date_field] = datetime.now()

        return cls(**converted_data)


@dataclass
class GameObject(BaseModel):
    """게임 객체 모델"""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: Dict[str, str] = field(default_factory=dict)  # {'en': 'name', 'ko': '이름'}
    description: Dict[str, str] = field(default_factory=dict)
    object_type: str = ""  # 'item', 'npc', 'furniture' 등
    location_type: str = ""  # 'room', 'inventory'
    location_id: Optional[str] = None  # room_id 또는 character_id
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """초기화 후 검증"""
        self.validate()

    def validate(self) -> None:
        """게임 객체 데이터 유효성 검증"""
        if not isinstance(self.name, dict):
            raise ValueError("객체 이름은 딕셔너리 형태여야 합니다")

        if not self.name.get('en') and not self.name.get('ko'):
            raise ValueError("객체 이름은 최소 하나의 언어로 설정되어야 합니다")

        if not isinstance(self.description, dict):
            raise ValueError("객체 설명은 딕셔너리 형태여야 합니다")

        if not self.object_type:
            raise ValueError("객체 타입은 필수입니다")

        valid_object_types = {'item', 'npc', 'furniture', 'container', 'weapon', 'armor', 'consumable'}
        if self.object_type not in valid_object_types:
            raise ValueError(f"올바르지 않은 객체 타입입니다: {self.object_type}")

        if not self.location_type:
            raise ValueError("위치 타입은 필수입니다")

        valid_location_types = {'room', 'inventory', 'container'}
        if self.location_type not in valid_location_types:
            raise ValueError(f"올바르지 않은 위치 타입입니다: {self.location_type}")

        if not isinstance(self.properties, dict):
            raise ValueError("속성은 딕셔너리 형태여야 합니다")

    def get_localized_name(self, locale: str = 'en') -> str:
        """로케일에 따른 객체 이름 반환"""
        return self.name.get(locale, self.name.get('en', self.name.get('ko', 'Unknown Object')))

    def get_localized_description(self, locale: str = 'en') -> str:
        """로케일에 따른 객체 설명 반환"""
        return self.description.get(locale, self.description.get('en', self.description.get('ko', 'No description available.')))

    def get_property(self, key: str, default: Any = None) -> Any:
        """속성 값 조회"""
        return self.properties.get(key, default)

    def set_property(self, key: str, value: Any) -> None:
        """속성 값 설정"""
        self.properties[key] = value

    def move_to_room(self, room_id: str) -> None:
        """방으로 이동"""
        self.location_type = 'room'
        self.location_id = room_id

    def move_to_inventory(self, character_id: str) -> None:
        """인벤토리로 이동"""
        self.location_type = 'inventory'
        self.location_id = character_id

    def is_in_room(self, room_id: str) -> bool:
        """특정 방에 있는지 확인"""
        return self.location_type == 'room' and self.location_id == room_id

    def is_in_inventory(self, character_id: str) -> bool:
        """특정 캐릭터의 인벤토리에 있는지 확인"""
        return self.location_type == 'inventory' and self.location_id == character_id

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (데이터베이스 스키마에 맞게)"""
        data = super().to_dict()

        # name과 description을 개별 컬럼으로 분리하고 원본 제거
        if 'name' in data:
            name_dict = data.pop('name')
            # BaseModel에서 이미 JSON 문자열로 변환된 경우 다시 파싱
            if isinstance(name_dict, str):
                try:
                    name_dict = json.loads(name_dict)
                except (json.JSONDecodeError, TypeError):
                    name_dict = {}
            data['name_en'] = name_dict.get('en', '') if isinstance(name_dict, dict) else ''
            data['name_ko'] = name_dict.get('ko', '') if isinstance(name_dict, dict) else ''

        if 'description' in data:
            desc_dict = data.pop('description')
            # BaseModel에서 이미 JSON 문자열로 변환된 경우 다시 파싱
            if isinstance(desc_dict, str):
                try:
                    desc_dict = json.loads(desc_dict)
                except (json.JSONDecodeError, TypeError):
                    desc_dict = {}
            data['description_en'] = desc_dict.get('en', '') if isinstance(desc_dict, dict) else ''
            data['description_ko'] = desc_dict.get('ko', '') if isinstance(desc_dict, dict) else ''

        # properties는 JSON 문자열로 유지 (BaseModel에서 이미 변환됨)
        # 추가 처리 불필요

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameObject':
        """딕셔너리에서 모델 생성"""
        # 데이터베이스 컬럼명을 모델 필드명으로 변환
        converted_data = {}

        for key, value in data.items():
            if key == 'name_en' or key == 'name_ko':
                # name_en, name_ko를 name 딕셔너리로 변환
                if 'name' not in converted_data:
                    converted_data['name'] = {}
                locale = 'en' if key == 'name_en' else 'ko'
                converted_data['name'][locale] = value
            elif key == 'description_en' or key == 'description_ko':
                # description_en, description_ko를 description 딕셔너리로 변환
                if 'description' not in converted_data:
                    converted_data['description'] = {}
                locale = 'en' if key == 'description_en' else 'ko'
                converted_data['description'][locale] = value
            elif key == 'properties':
                # properties JSON 문자열을 딕셔너리로 변환
                if isinstance(value, str):
                    try:
                        converted_data[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        converted_data[key] = {}
                else:
                    converted_data[key] = value or {}
            else:
                converted_data[key] = value

        # 필수 필드 기본값 설정
        if 'name' not in converted_data:
            converted_data['name'] = {}
        if 'description' not in converted_data:
            converted_data['description'] = {}
        if 'properties' not in converted_data:
            converted_data['properties'] = {}

        # 날짜 필드 처리 (문자열을 datetime 객체로 변환)
        for date_field in ['created_at']:
            if date_field in converted_data and isinstance(converted_data[date_field], str):
                try:
                    from datetime import datetime
                    converted_data[date_field] = datetime.fromisoformat(converted_data[date_field].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    # 파싱 실패 시 현재 시간으로 설정
                    converted_data[date_field] = datetime.now()

        return cls(**converted_data)


@dataclass
class Session(BaseModel):
    """세션 모델 (메모리에서만 사용, 데이터베이스 저장 안함)"""

    id: str = field(default_factory=lambda: str(uuid4()))
    player_id: str = ""
    character_id: str = ""
    websocket: Any = None  # web.WebSocketResponse (순환 참조 방지)
    current_room_id: str = ""
    locale: str = "en"
    connected_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """초기화 후 검증"""
        self.validate()

    def validate(self) -> None:
        """세션 데이터 유효성 검증"""
        if not self.player_id:
            raise ValueError("플레이어 ID는 필수입니다")

        if not self.character_id:
            raise ValueError("캐릭터 ID는 필수입니다")

        if self.locale not in ["en", "ko"]:
            raise ValueError("지원되지 않는 언어입니다 (en, ko만 지원)")

    def update_activity(self) -> None:
        """마지막 활동 시간 업데이트"""
        self.last_activity = datetime.now()

    def is_active(self, timeout_minutes: int = 30) -> bool:
        """세션이 활성 상태인지 확인"""
        if not self.last_activity:
            return False

        time_diff = datetime.now() - self.last_activity
        return time_diff.total_seconds() < (timeout_minutes * 60)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (WebSocket 제외)"""
        data = super().to_dict()
        # WebSocket 객체는 직렬화에서 제외
        if 'websocket' in data:
            del data['websocket']
        return data