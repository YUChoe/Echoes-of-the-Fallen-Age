"""
다국어 지원 유틸리티 함수들
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class TranslationFileManager:
    """번역 파일 관리 클래스"""

    def __init__(self, translations_dir: str = "data/translations"):
        """
        TranslationFileManager 초기화

        Args:
            translations_dir: 번역 파일 디렉토리 경로
        """
        self.translations_dir = Path(translations_dir)
        self.translations_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"TranslationFileManager 초기화: {self.translations_dir}")

    def create_translation_file(self, locale: str, translations: Dict[str, str]) -> bool:
        """
        번역 파일 생성

        Args:
            locale: 로케일
            translations: 번역 딕셔너리

        Returns:
            bool: 생성 성공 여부
        """
        try:
            file_path = self.translations_dir / f"{locale}.json"

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(translations, f, ensure_ascii=False, indent=2)

            logger.info(f"번역 파일 생성: {file_path}")
            return True

        except Exception as e:
            logger.error(f"번역 파일 생성 실패: {e}")
            return False

    def load_translation_file(self, locale: str) -> Optional[Dict[str, str]]:
        """
        번역 파일 로드

        Args:
            locale: 로케일

        Returns:
            Optional[Dict[str, str]]: 번역 딕셔너리 (실패 시 None)
        """
        try:
            file_path = self.translations_dir / f"{locale}.json"

            if not file_path.exists():
                logger.warning(f"번역 파일이 존재하지 않음: {file_path}")
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                translations = json.load(f)

            logger.info(f"번역 파일 로드: {file_path} ({len(translations)}개)")
            return translations

        except Exception as e:
            logger.error(f"번역 파일 로드 실패: {e}")
            return None

    def update_translation_file(self, locale: str, key: str, value: str) -> bool:
        """
        번역 파일 업데이트

        Args:
            locale: 로케일
            key: 번역 키
            value: 번역 값

        Returns:
            bool: 업데이트 성공 여부
        """
        try:
            # 기존 번역 로드
            translations = self.load_translation_file(locale) or {}

            # 번역 업데이트
            translations[key] = value

            # 파일 저장
            return self.create_translation_file(locale, translations)

        except Exception as e:
            logger.error(f"번역 파일 업데이트 실패: {e}")
            return False

    def remove_translation_from_file(self, locale: str, key: str) -> bool:
        """
        번역 파일에서 키 제거

        Args:
            locale: 로케일
            key: 번역 키

        Returns:
            bool: 제거 성공 여부
        """
        try:
            translations = self.load_translation_file(locale)

            if not translations or key not in translations:
                logger.warning(f"번역 키를 찾을 수 없음: {key} ({locale})")
                return False

            del translations[key]

            return self.create_translation_file(locale, translations)

        except Exception as e:
            logger.error(f"번역 파일에서 키 제거 실패: {e}")
            return False

    def get_available_locales(self) -> List[str]:
        """사용 가능한 로케일 목록 반환"""
        locales = []

        for file_path in self.translations_dir.glob("*.json"):
            locale = file_path.stem
            locales.append(locale)

        return sorted(locales)

    def get_file_stats(self, locale: str) -> Optional[Dict[str, Any]]:
        """번역 파일 통계 정보"""
        try:
            translations = self.load_translation_file(locale)

            if not translations:
                return None

            file_path = self.translations_dir / f"{locale}.json"

            return {
                'locale': locale,
                'file_path': str(file_path),
                'total_keys': len(translations),
                'file_size': file_path.stat().st_size,
                'keys': list(translations.keys())
            }

        except Exception as e:
            logger.error(f"번역 파일 통계 조회 실패: {e}")
            return None

    def validate_translation_files(self) -> Dict[str, Any]:
        """번역 파일 유효성 검사"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'locales': {},
            'missing_keys': {},
            'extra_keys': {}
        }

        try:
            available_locales = self.get_available_locales()

            if not available_locales:
                validation_result['valid'] = False
                validation_result['errors'].append("번역 파일이 없습니다")
                return validation_result

            # 모든 로케일의 번역 로드
            all_translations = {}
            all_keys = set()

            for locale in available_locales:
                translations = self.load_translation_file(locale)
                if translations:
                    all_translations[locale] = translations
                    all_keys.update(translations.keys())
                    validation_result['locales'][locale] = len(translations)

            # 누락된 키와 추가 키 확인
            for locale, translations in all_translations.items():
                locale_keys = set(translations.keys())

                missing = all_keys - locale_keys
                if missing:
                    validation_result['missing_keys'][locale] = list(missing)
                    validation_result['warnings'].append(
                        f"{locale}에서 누락된 키: {', '.join(missing)}"
                    )

            logger.info(f"번역 파일 유효성 검사 완료: {len(available_locales)}개 로케일")

        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"유효성 검사 실패: {e}")
            logger.error(f"번역 파일 유효성 검사 실패: {e}")

        return validation_result


def create_default_translation_files() -> bool:
    """기본 번역 파일들 생성"""
    try:
        manager = TranslationFileManager()

        # 영어 번역
        en_translations = {
            "welcome_message": "Welcome to the MUD Engine!",
            "login_prompt": "Please enter your username:",
            "password_prompt": "Please enter your password:",
            "invalid_credentials": "Invalid username or password.",
            "command_not_found": "Command not found. Type \"help\" for available commands.",
            "room_exits": "Exits: {exits}",
            "inventory_empty": "Your inventory is empty.",
            "item_not_found": "Item not found.",
            "player_joined": "{player} has joined the game.",
            "player_left": "{player} has left the game.",
            "say_format": "{player} says: {message}",
            "tell_format": "{player} tells you: {message}",
            "look_room": "You are in {room_name}. {room_description}",
            "move_success": "You move {direction}.",
            "move_failed": "You cannot go that way.",
            "get_success": "You take the {item}.",
            "get_failed": "You cannot take that.",
            "drop_success": "You drop the {item}.",
            "drop_failed": "You are not carrying that.",
            "help_commands": "Available commands: look, go <direction>, say <message>, tell <player> <message>, get <item>, drop <item>, inventory, who, help, quit",
            "server_starting": "Server is starting...",
            "server_ready": "Server is ready!",
            "server_stopping": "Server is stopping...",
            "database_connected": "Database connected successfully.",
            "database_error": "Database connection failed.",
            "user_online": "Users online: {count}",
            "character_created": "Character created successfully.",
            "character_deleted": "Character deleted.",
            "room_created": "Room created successfully.",
            "object_created": "Object created successfully."
        }

        # 한국어 번역
        ko_translations = {
            "welcome_message": "MUD 엔진에 오신 것을 환영합니다!",
            "login_prompt": "사용자명을 입력하세요:",
            "password_prompt": "비밀번호를 입력하세요:",
            "invalid_credentials": "잘못된 사용자명 또는 비밀번호입니다.",
            "command_not_found": "명령어를 찾을 수 없습니다. \"help\"를 입력하여 사용 가능한 명령어를 확인하세요.",
            "room_exits": "출구: {exits}",
            "inventory_empty": "인벤토리가 비어있습니다.",
            "item_not_found": "아이템을 찾을 수 없습니다.",
            "player_joined": "{player}님이 게임에 참여했습니다.",
            "player_left": "{player}님이 게임을 떠났습니다.",
            "say_format": "{player}님이 말합니다: {message}",
            "tell_format": "{player}님이 당신에게 말합니다: {message}",
            "look_room": "당신은 {room_name}에 있습니다. {room_description}",
            "move_success": "{direction}쪽으로 이동했습니다.",
            "move_failed": "그쪽으로 갈 수 없습니다.",
            "get_success": "{item}을(를) 가져왔습니다.",
            "get_failed": "그것을 가져올 수 없습니다.",
            "drop_success": "{item}을(를) 떨어뜨렸습니다.",
            "drop_failed": "그것을 가지고 있지 않습니다.",
            "help_commands": "사용 가능한 명령어: look, go <방향>, say <메시지>, tell <플레이어> <메시지>, get <아이템>, drop <아이템>, inventory, who, help, quit",
            "server_starting": "서버를 시작하는 중...",
            "server_ready": "서버가 준비되었습니다!",
            "server_stopping": "서버를 중지하는 중...",
            "database_connected": "데이터베이스 연결 성공.",
            "database_error": "데이터베이스 연결 실패.",
            "user_online": "온라인 사용자: {count}명",
            "character_created": "캐릭터가 성공적으로 생성되었습니다.",
            "character_deleted": "캐릭터가 삭제되었습니다.",
            "room_created": "방이 성공적으로 생성되었습니다.",
            "object_created": "객체가 성공적으로 생성되었습니다."
        }

        # 파일 생성
        success = True
        success &= manager.create_translation_file('en', en_translations)
        success &= manager.create_translation_file('ko', ko_translations)

        if success:
            logger.info("기본 번역 파일 생성 완료")
        else:
            logger.error("기본 번역 파일 생성 실패")

        return success

    except Exception as e:
        logger.error(f"기본 번역 파일 생성 실패: {e}")
        return False


def validate_translation_key(key: str) -> bool:
    """번역 키 유효성 검사"""
    if not key or not isinstance(key, str):
        return False

    # 키는 영문, 숫자, 언더스코어만 허용
    import re
    return re.match(r'^[a-zA-Z0-9_]+$', key) is not None


def format_direction_name(direction: str, locale: str = 'en') -> str:
    """방향 이름 포맷팅"""
    direction_names = {
        'en': {
            'north': 'north',
            'south': 'south',
            'east': 'east',
            'west': 'west',
            'up': 'up',
            'down': 'down',
            'northeast': 'northeast',
            'northwest': 'northwest',
            'southeast': 'southeast',
            'southwest': 'southwest'
        },
        'ko': {
            'north': '북쪽',
            'south': '남쪽',
            'east': '동쪽',
            'west': '서쪽',
            'up': '위쪽',
            'down': '아래쪽',
            'northeast': '북동쪽',
            'northwest': '북서쪽',
            'southeast': '남동쪽',
            'southwest': '남서쪽'
        }
    }

    return direction_names.get(locale, {}).get(direction, direction)