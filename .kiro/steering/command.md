# 명령어 실행 규칙

## 기본 원칙
- **모든 명령어는 gitbash 환경에서 실행**
- Windows 환경이지만 bash 명령어 사용 필수
- PowerShell이나 CMD 사용 금지

## 가상 환경 활성화
```bash
# 가상 환경 활성화 (gitbash)
source mud_engine_env/Scripts/activate
```

## Python 실행 규칙
```bash
# PYTHONPATH 설정과 함께 실행
source mud_engine_env/Scripts/activate && PYTHONPATH=. python -m src.mud_engine.main

# 테스트 실행
source mud_engine_env/Scripts/activate && PYTHONPATH=. pytest

# 스크립트 실행
source mud_engine_env/Scripts/activate && PYTHONPATH=. python scripts/make_admin.py
```

## 데이터베이스 작업
```bash
# SQLite 작업 (python 사용)
source mud_engine_env/Scripts/activate && python -c "
import sqlite3
conn = sqlite3.connect('data/mud_engine.db')
cursor = conn.cursor()
# SQL 쿼리 실행
conn.close()
"
```

## Git 작업
```bash
# Git 명령어는 가상 환경 불필요
git add .
git commit -m "커밋 메시지"
git push
```

## 파일 작업
```bash
# 파일 목록 확인
ls -la

# 디렉토리 생성
mkdir -p directory_name

# 파일 복사
cp source_file destination_file

# 파일 삭제
rm file_name
```

## 주의사항
- `bash -c` 명령어 사용 금지
- Windows 네이티브 명령어 (dir, copy, del 등) 사용 금지
- 모든 경로는 Unix 스타일 슬래시(/) 사용
- 가상 환경 활성화 후 Python 관련 작업 수행