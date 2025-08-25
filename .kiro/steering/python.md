# Python 개발 규칙

## 기본 규칙
- PEP8 준수
- 변수와 함수 네이밍은 snake_case

## 가상 환경 사용 필수
**⚠️ 절대로 가상 환경만을 사용할 것!**
- 모든 Python 명령어는 반드시 가상 환경 내에서 실행
- 패키지 설치, 테스트 실행, 서버 실행 등 모든 작업은 가상 환경에서만 수행
- 전역 Python 환경 사용 금지

## PYTHONPATH 설정 필수
- **⚠️ PYTHONPATH 설정 필수**: 모든 Python 실행 시 PYTHONPATH를 프로젝트 루트로 설정
- 올바른 실행 예시: `PYTHONPATH=. python -m src.mud_engine.main`
- 테스트 실행 시: `PYTHONPATH=. pytest`

