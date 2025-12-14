#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""버전 정보 생성 스크립트"""

import subprocess
import json
import os
from datetime import datetime
from pathlib import Path


def get_git_info():
    """Git 정보 수집"""
    try:
        # 현재 커밋 해시 (짧은 버전)
        commit_hash = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=os.getcwd(),
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
        
        # 현재 커밋 해시 (전체 버전)
        commit_hash_full = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            cwd=os.getcwd(),
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
        
        # 브랜치 이름
        branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=os.getcwd(),
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
        
        # 커밋 날짜
        commit_date = subprocess.check_output(
            ['git', 'log', '-1', '--format=%ci'],
            cwd=os.getcwd(),
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
        
        # 태그 정보 (있는 경우)
        try:
            tag = subprocess.check_output(
                ['git', 'describe', '--tags', '--exact-match'],
                cwd=os.getcwd(),
                stderr=subprocess.DEVNULL
            ).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            tag = None
        
        # 작업 디렉토리 상태 확인
        try:
            subprocess.check_output(
                ['git', 'diff-index', '--quiet', 'HEAD', '--'],
                cwd=os.getcwd(),
                stderr=subprocess.DEVNULL
            )
            is_dirty = False
        except subprocess.CalledProcessError:
            is_dirty = True
        
        return {
            'commit_hash': commit_hash,
            'commit_hash_full': commit_hash_full,
            'branch': branch,
            'commit_date': commit_date,
            'tag': tag,
            'is_dirty': is_dirty,
            'build_date': datetime.now().isoformat()
        }
        
    except subprocess.CalledProcessError as e:
        print(f"Git 명령어 실행 실패: {e}")
        return None
    except FileNotFoundError:
        print("Git이 설치되지 않았거나 Git 저장소가 아닙니다.")
        return None


def generate_version_file():
    """버전 정보 파일 생성"""
    git_info = get_git_info()
    
    if not git_info:
        # Git 정보를 가져올 수 없는 경우 기본값 사용
        git_info = {
            'commit_hash': 'unknown',
            'commit_hash_full': 'unknown',
            'branch': 'unknown',
            'commit_date': 'unknown',
            'tag': None,
            'is_dirty': False,
            'build_date': datetime.now().isoformat()
        }
    
    # 버전 정보를 JSON 파일로 저장
    version_file = Path('src/mud_engine/version_info.json')
    version_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(version_file, 'w', encoding='utf-8') as f:
        json.dump(git_info, f, indent=2, ensure_ascii=False)
    
    print(f"버전 정보 파일 생성 완료: {version_file}")
    print(f"커밋 해시: {git_info['commit_hash']}")
    print(f"브랜치: {git_info['branch']}")
    print(f"빌드 시간: {git_info['build_date']}")
    
    return git_info


if __name__ == '__main__':
    generate_version_file()