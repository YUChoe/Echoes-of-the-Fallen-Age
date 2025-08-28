# Python 개발 환경 규칙

## 환경 변수
- `VENV_NAME`: 가상환경 디렉토리명 (예: `mud_engine_env`)
- `MAIN_MODULE`: 메인 모듈 경로 (예: `src.mud_engine.main`)
- `PROJECT_PORT`: 서비스 포트 (예: `8080`)
- `PYTHON_VERSION`: Python 3.13 사용 확정
- `MYPY_VERSION`: mypy 1.15.0 사용

## 기본 원칙
- **PEP8 준수**
- **snake_case 네이밍**
- **가상 환경 필수**: 모든 Python 작업은 가상 환경에서만 실행
- **PYTHONPATH 설정**: `PYTHONPATH=.` 항상 포함
- **gitbash 사용**: Windows에서도 bash 명령어만 사용

## 핵심 개발 원칙
- **비동기 프로그래밍**: 모든 비동기 함수는 `async/await` 패턴 사용
- **표준 로깅**: Python logging 모듈 사용으로 일관된 로그 관리
- **다국어 지원**: 모든 텍스트는 딕셔너리 형태로 저장하여 국제화 지원
- **리포지토리 패턴**: 데이터베이스 작업은 리포지토리 패턴으로 추상화
- **이벤트 기반 아키텍처**: 컴포넌트 간 결합도 최소화를 위한 이벤트 시스템

## 코드 품질 기준
- 타입 힌트와 enum 적극 활용
- 의존성 주입으로 테스트 가능한 코드 작성
- 방어적 프로그래밍으로 안정성 확보
- 충분한 로깅으로 디버깅 지원
- **mypy 정적 검사 필수**: 소스 수정 후 실행 전에 반드시 mypy 검사 통과

## 실행 패턴
```bash
# mypy 정적 검사 (실행 전 필수)
source ${VENV_NAME}/Scripts/activate && PYTHONPATH=. mypy src/

# 가상 환경 활성화 + Python 실행
source ${VENV_NAME}/Scripts/activate && PYTHONPATH=. python -m ${MAIN_MODULE}

# 테스트 실행
source ${VENV_NAME}/Scripts/activate && PYTHONPATH=. pytest

# 스크립트 실행
source ${VENV_NAME}/Scripts/activate && PYTHONPATH=. python scripts/script_name.py
```

## 현재 프로젝트 설정
```bash
# mypy 정적 검사 (실행 전 필수)
source mud_engine_env/Scripts/activate && PYTHONPATH=. mypy src/

# 이 프로젝트의 실제 명령어
source mud_engine_env/Scripts/activate && PYTHONPATH=. python -m src.mud_engine.main
source mud_engine_env/Scripts/activate && PYTHONPATH=. pytest
```

## mypy 정적 검사 규칙
- **실행 전 필수**: 모든 소스 코드 수정 후 실행 전에 mypy 검사 통과 필수
- **설정 파일**: setup.cfg의 [mypy] 섹션 설정 참조
- **검사 범위**: src/ 디렉토리 전체
- **에러 허용 안함**: mypy 에러가 있으면 실행 금지

```bash
# mypy 검사 명령어
source mud_engine_env/Scripts/activate && PYTHONPATH=. mypy src/

# 특정 파일만 검사
source mud_engine_env/Scripts/activate && PYTHONPATH=. mypy src/mud_engine/specific_file.py
```

## 프로세스 관리
```bash
# 프로세스 확인 및 종료
ps aux | grep python
kill -9 <PID>
```

## 금지사항
- PowerShell, CMD 사용 금지
- 전역 Python 환경 사용 금지
- Windows 네이티브 명령어 사용 금지
- 서비스 포트 변경 금지 (프로세스 종료로 해결)
- mypy 에러 무시하고 실행 금지