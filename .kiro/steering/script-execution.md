# 스크립트 실행 가이드

## 기본 원칙

- **script_test.sh 사용**: scripts/ 디렉토리의 Python 스크립트 실행 시 반드시 사용
- **telnet_test.sh 사용**: telnet/ 디렉토리의 테스트 스크립트 실행 시 반드시 사용
- **직접 python 명령어 금지**: 가상환경과 PYTHONPATH 설정 누락으로 인한 오류 방지
- telnet_test.sh는 telnet-mcp 사용 불가인 경우에만 사용한다.

## script_test.sh 사용법

### 기본 사용법

```bash
# scripts/ 디렉토리의 Python 스크립트 실행
./script_test.sh <스크립트명>

# 예시
./script_test.sh check_monk_name.py
./script_test.sh update_monk_name
```

### 특징

- 자동으로 가상환경 활성화 (`mud_engine_env`)
- PYTHONPATH=. 자동 설정
- .py 확장자 자동 추가 (생략 가능)
- 실행 결과 및 종료 코드 표시
- 사용 가능한 스크립트 목록 표시 (인자 없이 실행 시)

### 사용 시나리오

- 데이터베이스 스키마 확인
- 몬스터/플레이어 데이터 조회/수정
- 게임 데이터 초기화 및 설정
- 디버깅 및 검증 스크립트

## telnet_test.sh 사용법

### 기본 사용법

```bash
# telnet/ 디렉토리의 테스트 스크립트 실행
./telnet_test.sh <테스트파일명>

# 예시
./telnet_test.sh test_monk_debug.py
./telnet_test.sh telnet_client
```

### 특징

- Telnet 서버 테스트 전용
- 자동으로 가상환경 활성화
- .py 확장자 자동 추가 (생략 가능)
- 실행 결과 및 종료 코드 표시
- 사용 가능한 테스트 파일 목록 표시

### 사용 시나리오

- Telnet 서버 연결 테스트
- 명령어 실행 및 응답 확인
- 게임 기능 통합 테스트
- 사용자 시나리오 검증

## 금지사항

### 직접 python 명령어 사용 금지

```bash
# ❌ 금지 - 가상환경 및 PYTHONPATH 누락
python scripts/check_monk_name.py
source mud_engine_env/Scripts/activate && python scripts/check_monk_name.py

# ✅ 올바른 방법
./script_test.sh check_monk_name
```

### 이유

- 가상환경 활성화 누락으로 인한 모듈 import 오류
- PYTHONPATH 설정 누락으로 인한 경로 오류
- 일관되지 않은 실행 환경
- 무한루프 및 프로세스 종료 문제

## 스크립트 작성 가이드

### Python 스크립트 템플릿 (scripts/)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""스크립트 설명"""

import asyncio
import sys
from src.mud_engine.database import get_database_manager


async def main():
    """메인 함수"""
    print("=== 스크립트 시작 ===\n")

    db_manager = None
    try:
        db_manager = await get_database_manager()

        # 작업 수행

        print("\n✅ 작업 완료")
        return 0

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # 데이터베이스 연결 확실히 종료
        if db_manager:
            try:
                await db_manager.close()
            except Exception:
                pass


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
```

### Telnet 테스트 스크립트 템플릿 (telnet/)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Telnet 테스트 설명"""

import sys
import time
from telnet_client import TelnetClient


def main():
    """메인 함수"""
    print("=== Telnet 테스트 시작 ===\n")

    client = TelnetClient()

    try:
        # 연결
        result = client.connect("127.0.0.1", 4000, 5)
        if not result["success"]:
            print(f"❌ 연결 실패: {result.get('error')}")
            return 1

        session_id = result["sessionId"]

        # 테스트 수행

        # 종료
        client.disconnect(session_id)
        print("\n✅ 테스트 완료")
        return 0

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
```

## 무한루프 방지

### 필수 사항

- 모든 스크립트는 명시적으로 `sys.exit(exit_code)` 호출
- 데이터베이스 연결은 `finally` 블록에서 확실히 종료
- 예외 처리 시 적절한 exit code 반환 (0: 성공, 1: 실패)

### 데이터베이스 연결 안전 종료 패턴

```python
db_manager = None
try:
    db_manager = await get_database_manager()
    # 작업 수행
finally:
    if db_manager:
        try:
            await db_manager.close()
        except Exception:
            pass
```

## 체크리스트

### 스크립트 실행 전

- [ ] script_test.sh 또는 telnet_test.sh 사용 확인
- [ ] 서버 실행 상태 확인 (Telnet 테스트 시)
- [ ] 스크립트 파일 존재 여부 확인

### 스크립트 작성 시

- [ ] 적절한 템플릿 사용
- [ ] 데이터베이스 연결 안전 종료 패턴 적용
- [ ] 명시적 exit code 반환
- [ ] 예외 처리 및 로깅 포함
- [ ] 무한루프 방지 코드 포함

### 실행 후

- [ ] 정상 종료 확인 (exit code 0)
- [ ] 오류 발생 시 로그 확인
- [ ] 데이터베이스 연결 정리 확인
