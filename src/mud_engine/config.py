# -*- coding: utf-8 -*-
"""환경 설정 관리 모듈"""

import os
from pathlib import Path
from typing import Any, Optional

# .env 파일 수동 로드
def load_env_file():
    """수동으로 .env 파일을 로드합니다."""
    env_path = Path('.env')
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # 따옴표 제거
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    os.environ[key] = value

# .env 파일 로드
load_env_file()


class Config:
    """환경 변수 기반 설정 관리 클래스"""

    @staticmethod
    def get_env(key: str, default: Any = None, cast_type: type = str) -> Any:
        """환경 변수 값을 가져오고 타입 변환을 수행합니다.

        Args:
            key: 환경 변수 키
            default: 기본값
            cast_type: 변환할 타입 (str, int, bool 등)

        Returns:
            변환된 환경 변수 값 또는 기본값
        """
        value = os.getenv(key, default)

        if value is None:
            return default

        if cast_type == bool:
            return str(value).lower() in ('true', '1', 'yes', 'on')
        elif cast_type == int:
            try:
                return int(value)
            except (ValueError, TypeError):
                return default
        elif cast_type == float:
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        else:
            return cast_type(value)

    # 데이터베이스 설정
    DATABASE_URL = get_env.__func__('DATABASE_URL', 'sqlite:///data/mud_engine.db')

    # 서버 설정
    SERVER_HOST = get_env.__func__('SERVER_HOST', 'localhost')
    SERVER_PORT = get_env.__func__('SERVER_PORT', 8080, int)

    # 보안 설정
    SECRET_KEY = get_env.__func__('SECRET_KEY', 'your-secret-key-change-this-in-production')

    # 개발 설정
    DEBUG = get_env.__func__('DEBUG', False, bool)
    LOG_LEVEL = get_env.__func__('LOG_LEVEL', 'INFO')

    # 다국어 설정
    DEFAULT_LOCALE = get_env.__func__('DEFAULT_LOCALE', 'en')
    SUPPORTED_LOCALES = get_env.__func__('SUPPORTED_LOCALES', 'en,ko').split(',')

    # 사용자 계정 설정
    USERNAME_MIN_LENGTH = get_env.__func__('USERNAME_MIN_LENGTH', 3, int)
    USERNAME_MAX_LENGTH = get_env.__func__('USERNAME_MAX_LENGTH', 20, int)
    PASSWORD_MIN_LENGTH = get_env.__func__('PASSWORD_MIN_LENGTH', 6, int)

    @classmethod
    def get_username_validation_config(cls) -> dict:
        """사용자명 유효성 검사 설정을 반환합니다."""
        return {
            'min_length': cls.USERNAME_MIN_LENGTH,
            'max_length': cls.USERNAME_MAX_LENGTH,
            'password_min_length': cls.PASSWORD_MIN_LENGTH
        }