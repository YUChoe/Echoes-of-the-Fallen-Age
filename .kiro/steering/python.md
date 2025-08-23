# Python 개발 규칙

### 기본 규칙 
- PEP8 준수
- 변수와 함수 네이밍은 snake_case

### 가상 환경 사용 필수

**⚠️ 절대로 가상 환경만을 사용할 것!**

- gitbash 환경에서 실행
- 모든 Python 명령어는 반드시 가상 환경 내에서 실행
- 가상 환경 활성화: `source mud_engine_env/Scripts/activate`
- 패키지 설치, 테스트 실행, 서버 실행 등 모든 작업은 가상 환경에서만 수행
- 전역 Python 환경 사용 금지

### 실행 방법

- Command 에 `bash -c` 등을 사용하지 말 것
- **⚠️ PYTHONPATH 설정 필수**: 모든 Python 실행 시 PYTHONPATH를 프로젝트 루트로 설정
- 올바른 실행 예시: `PYTHONPATH=. python -m src.mud_engine.main`
- 테스트 실행 시: `PYTHONPATH=. pytest`
- **Git 커밋**: 가상 환경 불필요 - 직접 `git add`, `git commit` 사용 가능

### 가상 환경 확인 방법

```bash
# 가상 환경 활성화 후 패키지 목록 확인
source mud_engine_env/Scripts/activate && pip list

# 가상 환경 활성화 후 테스트 실행 (PYTHONPATH 포함)
source mud_engine_env/Scripts/activate && PYTHONPATH=. pytest

# 가상 환경 활성화 후 서버 실행 (PYTHONPATH 포함)
source mud_engine_env/Scripts/activate && PYTHONPATH=. python -m src.mud_engine.main
```

