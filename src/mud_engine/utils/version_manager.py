# -*- coding: utf-8 -*-
"""버전 정보 관리자"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class VersionManager:
    """버전 정보 관리 클래스"""
    
    def __init__(self):
        self._version_info: Optional[Dict[str, Any]] = None
        self._load_version_info()
    
    def _load_version_info(self) -> None:
        """버전 정보 파일 로드"""
        try:
            version_file = Path(__file__).parent.parent / 'version_info.json'
            
            if version_file.exists():
                with open(version_file, 'r', encoding='utf-8') as f:
                    self._version_info = json.load(f)
                logger.info(f"버전 정보 파일 로드 완료: {self.get_commit_hash()}")
            else:
                logger.warning(f"버전 정보 파일을 찾을 수 없음: {version_file}")
                logger.info("개발 환경에서는 'python scripts/generate_version_info.py'를 실행하세요")
                self._version_info = self._get_default_version_info()
                
        except Exception as e:
            logger.error(f"버전 정보 로드 실패: {e}")
            self._version_info = self._get_default_version_info()
    
    def _get_default_version_info(self) -> Dict[str, Any]:
        """기본 버전 정보 반환 (개발 환경용)"""
        from datetime import datetime
        return {
            'commit_hash': 'dev',
            'commit_hash_full': 'development',
            'branch': 'development',
            'commit_date': 'unknown',
            'tag': None,
            'is_dirty': False,
            'build_date': datetime.now().isoformat()
        }
    
    def get_commit_hash(self, short: bool = True) -> str:
        """커밋 해시 반환"""
        if not self._version_info:
            return 'unknown'
        
        if short:
            return self._version_info.get('commit_hash', 'unknown')
        else:
            return self._version_info.get('commit_hash_full', 'unknown')
    
    def get_branch(self) -> str:
        """브랜치 이름 반환"""
        if not self._version_info:
            return 'unknown'
        return self._version_info.get('branch', 'unknown')
    
    def get_tag(self) -> Optional[str]:
        """태그 정보 반환"""
        if not self._version_info:
            return None
        return self._version_info.get('tag')
    
    def get_commit_date(self) -> str:
        """커밋 날짜 반환"""
        if not self._version_info:
            return 'unknown'
        return self._version_info.get('commit_date', 'unknown')
    
    def get_build_date(self) -> str:
        """빌드 날짜 반환"""
        if not self._version_info:
            return 'unknown'
        return self._version_info.get('build_date', 'unknown')
    
    def is_dirty(self) -> bool:
        """작업 디렉토리가 더티한지 확인"""
        if not self._version_info:
            return False
        return self._version_info.get('is_dirty', False)
    
    def get_version_string(self) -> str:
        """버전 문자열 반환"""
        commit_hash = self.get_commit_hash()
        branch = self.get_branch()
        tag = self.get_tag()
        
        if tag:
            version = f"{tag} ({commit_hash})"
        else:
            version = f"{branch}@{commit_hash}"
        
        if self.is_dirty():
            version += "-dirty"
        
        return version
    
    def get_full_version_info(self) -> Dict[str, Any]:
        """전체 버전 정보 반환"""
        if not self._version_info:
            return self._get_default_version_info()
        return self._version_info.copy()


# 전역 인스턴스
_version_manager = None


def get_version_manager() -> VersionManager:
    """전역 버전 관리자 인스턴스 반환"""
    global _version_manager
    if _version_manager is None:
        _version_manager = VersionManager()
    return _version_manager


def get_version_string() -> str:
    """편의 함수: 버전 문자열 반환"""
    return get_version_manager().get_version_string()


def get_commit_hash(short: bool = True) -> str:
    """편의 함수: 커밋 해시 반환"""
    return get_version_manager().get_commit_hash(short)