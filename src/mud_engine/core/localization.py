"""
다국어 지원 시스템
"""

import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class LocalizationManager:
    """다국어 메시지 관리자"""
    
    def __init__(self):
        """초기화"""
        self.messages: Dict[str, Dict[str, str]] = {}
        self.default_locale = "en"
        self.supported_locales = ["en", "ko"]
        self._load_default_messages()
    
    def _load_default_messages(self) -> None:
        """기본 메시지 로드"""
        # 기본 시스템 메시지들
        self.messages = {
            # 인증 관련
            "auth.login_success": {
                "en": "✅ Welcome, {username}!",
                "ko": "✅ '{username}'님, 환영합니다!"
            },
            "auth.login_failed": {
                "en": "❌ Invalid username or password.",
                "ko": "❌ 사용자명 또는 비밀번호가 올바르지 않습니다."
            },
            "auth.already_logged_in": {
                "en": "❌ User is already logged in.",
                "ko": "❌ 이미 로그인된 사용자입니다."
            },
            "auth.not_authenticated": {
                "en": "❌ You are not authenticated.",
                "ko": "❌ 인증되지 않은 사용자입니다."
            },
            
            # 게임 입장
            "game.entered": {
                "en": "Game entered! Type 'help' for commands.",
                "ko": "게임에 입장했습니다! 'help' 명령어로 도움말을 확인하세요."
            },
            "game.player_joined": {
                "en": "🎮 {username} joined the game.",
                "ko": "🎮 {username}님이 게임에 참여했습니다."
            },
            "game.player_left": {
                "en": "👋 {username} left the game.",
                "ko": "👋 {username}님이 게임을 떠났습니다."
            },
            
            # 이동 관련
            "movement.no_exit": {
                "en": "❌ You cannot go {direction}.",
                "ko": "❌ {direction} 방향으로는 갈 수 없습니다."
            },
            "movement.room_not_found": {
                "en": "❌ Room not found.",
                "ko": "❌ 방을 찾을 수 없습니다."
            },
            "movement.moved": {
                "en": "{username} moved {direction}.",
                "ko": "{username}님이 {direction}(으)로 이동했습니다."
            },
            
            # 전투 관련
            "combat.start": {
                "en": "⚔️ Combat started with {monster}!",
                "ko": "⚔️ {monster}와(과) 전투를 시작합니다!"
            },
            "combat.victory": {
                "en": "🎉 Victory! You defeated {monster}!",
                "ko": "🎉 승리! {monster}을(를) 처치했습니다!"
            },
            "combat.defeat": {
                "en": "💀 You were defeated...",
                "ko": "💀 전투에서 패배했습니다..."
            },
            "combat.your_turn": {
                "en": "🎯 Your turn! Choose your action:",
                "ko": "🎯 당신의 턴입니다! 행동을 선택하세요:"
            },
            "combat.monster_turn": {
                "en": "⏳ {monster}'s turn...",
                "ko": "⏳ {monster}의 턴입니다..."
            },
            "combat.attack_hit": {
                "en": "✅ Hit! {damage} damage to {target}!",
                "ko": "✅ 명중! {target}에게 {damage} 데미지!"
            },
            "combat.attack_miss": {
                "en": "❌ Missed {target}!",
                "ko": "❌ {target}을(를) 빗나갔습니다!"
            },
            "combat.defend": {
                "en": "{actor} takes a defensive stance. (Next damage reduced by 50%)",
                "ko": "{actor}이(가) 방어 자세를 취했습니다. (다음 공격 데미지 50% 감소)"
            },
            "combat.flee_success": {
                "en": "💨 You fled from combat!",
                "ko": "💨 전투에서 도망쳤습니다!"
            },
            "combat.flee_failed": {
                "en": "❌ Failed to flee!",
                "ko": "❌ 도망치지 못했습니다!"
            },
            
            # 아이템 관련
            "item.not_found": {
                "en": "❌ Item '{item}' not found.",
                "ko": "❌ '{item}' 아이템을 찾을 수 없습니다."
            },
            "item.picked_up": {
                "en": "📦 You picked up {item}.",
                "ko": "📦 {item}을(를) 주웠습니다."
            },
            "item.dropped": {
                "en": "📦 You dropped {item}.",
                "ko": "📦 {item}을(를) 떨어뜨렸습니다."
            },
            "item.too_heavy": {
                "en": "❌ Too heavy to carry.",
                "ko": "❌ 너무 무거워서 들 수 없습니다."
            },
            "item.disappeared": {
                "en": "💨 {item} disappeared before your eyes.",
                "ko": "💨 {item}이(가) 눈앞에서 사라졌습니다."
            },
            
            # 명령어 관련
            "command.unknown": {
                "en": "❌ Unknown command: {command}",
                "ko": "❌ 알 수 없는 명령어: {command}"
            },
            "command.invalid_args": {
                "en": "❌ Invalid arguments. Usage: {usage}",
                "ko": "❌ 잘못된 인자입니다. 사용법: {usage}"
            },
            "command.admin_only": {
                "en": "❌ This command is for administrators only.",
                "ko": "❌ 이 명령어는 관리자만 사용할 수 있습니다."
            },
            
            # 시스템 메시지
            "system.server_shutdown": {
                "en": "🔧 Server is shutting down...",
                "ko": "🔧 서버가 종료됩니다..."
            },
            "system.maintenance": {
                "en": "🔧 Server maintenance in progress.",
                "ko": "🔧 서버 점검 중입니다."
            },
            
            # 에러 메시지
            "error.generic": {
                "en": "❌ An error occurred.",
                "ko": "❌ 오류가 발생했습니다."
            },
            "error.database": {
                "en": "❌ Database error occurred.",
                "ko": "❌ 데이터베이스 오류가 발생했습니다."
            },
            "error.network": {
                "en": "❌ Network error occurred.",
                "ko": "❌ 네트워크 오류가 발생했습니다."
            },
            
            # 언어 설정
            "language.changed": {
                "en": "✅ Language changed to English.",
                "ko": "✅ 언어가 한국어로 변경되었습니다."
            },
            "language.invalid": {
                "en": "❌ Invalid language. Supported: {languages}",
                "ko": "❌ 지원되지 않는 언어입니다. 지원 언어: {languages}"
            },
            
            # 도움말
            "help.header": {
                "en": "📖 Available Commands:",
                "ko": "📖 사용 가능한 명령어:"
            },
            "help.footer": {
                "en": "Type 'help <command>' for detailed information.",
                "ko": "'help <명령어>'로 자세한 정보를 확인하세요."
            }
        }
        
        logger.info(f"기본 메시지 {len(self.messages)}개 로드 완료")
    
    def get_message(self, key: str, locale: str = None, **kwargs) -> str:
        """
        메시지 조회
        
        Args:
            key: 메시지 키 (예: "auth.login_success")
            locale: 언어 코드 (None이면 기본 언어)
            **kwargs: 메시지 포맷팅용 변수들
        
        Returns:
            str: 로케일에 맞는 메시지
        """
        if locale is None:
            locale = self.default_locale
        
        if locale not in self.supported_locales:
            locale = self.default_locale
        
        # 메시지 조회
        message_dict = self.messages.get(key)
        if not message_dict:
            logger.warning(f"메시지 키를 찾을 수 없음: {key}")
            return f"[Missing message: {key}]"
        
        # 로케일별 메시지 조회
        message = message_dict.get(locale)
        if not message:
            # 기본 언어로 폴백
            message = message_dict.get(self.default_locale)
            if not message:
                logger.warning(f"메시지를 찾을 수 없음: {key} (locale: {locale})")
                return f"[Missing message: {key}]"
        
        # 변수 치환
        try:
            return message.format(**kwargs)
        except KeyError as e:
            logger.warning(f"메시지 포맷팅 실패: {key}, 누락된 변수: {e}")
            return message
        except Exception as e:
            logger.error(f"메시지 포맷팅 오류: {key}, 오류: {e}")
            return message
    
    def add_message(self, key: str, messages: Dict[str, str]) -> None:
        """
        메시지 추가
        
        Args:
            key: 메시지 키
            messages: 언어별 메시지 딕셔너리 (예: {"en": "Hello", "ko": "안녕하세요"})
        """
        self.messages[key] = messages
        logger.debug(f"메시지 추가: {key}")
    
    def load_from_file(self, file_path: str) -> bool:
        """
        파일에서 메시지 로드
        
        Args:
            file_path: JSON 파일 경로
        
        Returns:
            bool: 성공 여부
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"메시지 파일이 존재하지 않음: {file_path}")
                return False
            
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 기존 메시지에 추가
            for key, messages in data.items():
                if isinstance(messages, dict):
                    self.messages[key] = messages
                else:
                    logger.warning(f"잘못된 메시지 형식: {key}")
            
            logger.info(f"메시지 파일 로드 완료: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"메시지 파일 로드 실패: {file_path}, 오류: {e}")
            return False
    
    def save_to_file(self, file_path: str) -> bool:
        """
        메시지를 파일로 저장
        
        Args:
            file_path: JSON 파일 경로
        
        Returns:
            bool: 성공 여부
        """
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.messages, f, ensure_ascii=False, indent=2)
            
            logger.info(f"메시지 파일 저장 완료: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"메시지 파일 저장 실패: {file_path}, 오류: {e}")
            return False
    
    def get_supported_locales(self) -> list:
        """지원되는 언어 목록 반환"""
        return self.supported_locales.copy()
    
    def is_supported_locale(self, locale: str) -> bool:
        """지원되는 언어인지 확인"""
        return locale in self.supported_locales


# 전역 인스턴스
_localization_manager = None


def get_localization_manager() -> LocalizationManager:
    """전역 다국어 관리자 인스턴스 반환"""
    global _localization_manager
    if _localization_manager is None:
        _localization_manager = LocalizationManager()
    return _localization_manager


def get_message(key: str, locale: str = None, **kwargs) -> str:
    """
    편의 함수: 메시지 조회
    
    Args:
        key: 메시지 키
        locale: 언어 코드
        **kwargs: 포맷팅 변수들
    
    Returns:
        str: 로케일에 맞는 메시지
    """
    return get_localization_manager().get_message(key, locale, **kwargs)