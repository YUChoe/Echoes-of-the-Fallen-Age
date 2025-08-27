# Python 개발 환경 규칙

## 환경 변수
- `VENV_NAME`: 가상환경 디렉토리명 (예: `mud_engine_env`)
- `MAIN_MODULE`: 메인 모듈 경로 (예: `src.mud_engine.main`)
- `PROJECT_PORT`: 서비스 포트 (예: `8080`)

## 기본 원칙
- **PEP8 준수**
- **snake_case 네이밍**
- **가상 환경 필수**: 모든 Python 작업은 가상 환경에서만 실행
- **PYTHONPATH 설정**: `PYTHONPATH=.` 항상 포함
- **gitbash 사용**: Windows에서도 bash 명령어만 사용

## 실행 패턴
```bash
# 가상 환경 활성화 + Python 실행
source ${VENV_NAME}/Scripts/activate && PYTHONPATH=. python -m ${MAIN_MODULE}

# 테스트 실행
source ${VENV_NAME}/Scripts/activate && PYTHONPATH=. pytest

# 스크립트 실행
source ${VENV_NAME}/Scripts/activate && PYTHONPATH=. python scripts/script_name.py
```

## 현재 프로젝트 설정
```bash
# 이 프로젝트의 실제 명령어
source mud_engine_env/Scripts/activate && PYTHONPATH=. python -m src.mud_engine.main
source mud_engine_env/Scripts/activate && PYTHONPATH=. pytest
```

## 프로세스 관리
```bash
# 프로세스 확인 및 종료
ps aux | grep python
kill -9 <PID>

# 포트 충돌 해결 (Windows)
netstat -ano | findstr :${PROJECT_PORT}
taskkill /PID <프로세스ID> /F
```

## 현재 프로젝트 프로세스 관리
```bash
# 8080 포트 사용 프로세스 확인
netstat -ano | findstr :8080
taskkill /PID <프로세스ID> /F
```

## 금지사항
- PowerShell, CMD 사용 금지
- 전역 Python 환경 사용 금지
- Windows 네이티브 명령어 사용 금지
- 서비스 포트 변경 금지 (프로세스 종료로 해결)