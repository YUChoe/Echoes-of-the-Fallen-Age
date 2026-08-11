# 스크립트 실행 가이드

## 기본 원칙

- **script_test.sh 사용**: `scripts/` 디렉토리의 Python 스크립트 실행 시 사용
- **`PYTHONPATH=.` 필수**: src-layout 구조라 없으면 임포트가 실패한다
- **`PYTHONIOENCODING=utf-8` 필수**: 없으면 한국어 출력이 cp949로 깨진다
- **가상환경은 활성화하지 않고 인터프리터를 직접 지정**: `.venv/Scripts/python.exe`

`telnet/` 디렉토리와 `telnet_test.sh` 는 제거됐다. `telnetlib` 가 표준
라이브러리에서 빠져 동작하지 않았고, 대상 프로토콜도 텍스트 명령어에서 JSON
라인으로 바뀌었다. 서버 검증은 `scripts/harness/` 를 쓴다. `harness-test.md` 참고.

## script_test.sh 사용법

```bash
# scripts/ 디렉토리의 Python 스크립트 실행
./script_test.sh <스크립트명>

# 예시
./script_test.sh dump_admin_schema.py
./script_test.sh cleanup_wal
```

### 특징

- `.venv/Scripts/python.exe` 직접 호출
- `PYTHONPATH=.`, `PYTHONIOENCODING=utf-8` 자동 설정
- `.py` 확장자 자동 추가 (생략 가능)
- 실행 결과 및 종료 코드 표시
- 사용 가능한 스크립트 목록 표시 (인자 없이 실행 시)

### 사용 시나리오

- 데이터베이스 스키마와 참조 관계 확인
- 몬스터/플레이어 데이터 조회·수정
- 게임 데이터 초기화 및 설정
- 디버깅 및 검증 스크립트

## 직접 실행

`script_test.sh` 를 거치지 않고 실행할 때는 세 가지를 모두 붙인다.

```bash
PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe scripts/dump_admin_schema.py
```

`python -c` 는 쓰지 않는다. 인용 처리가 셸마다 달라 깨지고 재실행이 어렵다.
한 번만 쓸 조회라도 스크립트 파일로 만든다.

## 스크립트 작성 가이드

### 템플릿

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""스크립트 설명"""

import asyncio
import sys

from src.mud_engine.database import get_database_manager


async def main() -> int:
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
    sys.exit(asyncio.run(main()))
```

### DB 를 읽기만 할 때

게임 엔진을 띄우지 않고 `sqlite3` 로 직접 읽어도 된다. 서버가 실행 중일 때도
안전하다. `scripts/dump_admin_schema.py` 가 이 방식이다.

```python
import sqlite3

conn = sqlite3.connect("data/mud_engine.db")
conn.row_factory = sqlite3.Row
```

`sqlite3` CLI 는 이 환경에 없다.

### 스키마

DB 스키마는 추측하지 않는다. `data/DATABASE_SCHEMA.md` 를 확인하거나
`scripts/dump_admin_schema.py` 로 실제 테이블을 읽는다. 문서와 실제가 어긋난
경우가 있었다.

## 무한루프 방지

- 모든 스크립트는 명시적으로 `sys.exit(exit_code)` 호출
- 데이터베이스 연결은 `finally` 블록에서 확실히 종료
- 예외 처리 시 적절한 exit code 반환 (0: 성공, 1: 실패)

## git 추적

`.gitignore` 가 `scripts/*.py`(직하만)와 `test_*.py` 를 제외한다. 새 스크립트를
커밋에 넣으려면 `git add -f` 가 필요하다. `scripts/harness/` 아래는 하위
디렉터리라 정상 추적된다.

## 체크리스트

### 실행 전

- [ ] `PYTHONPATH=.`, `PYTHONIOENCODING=utf-8` 확인
- [ ] DB 를 수정하는 스크립트인지 확인. 프로덕션 데이터가 올라가 있다
- [ ] 서버 실행 상태 확인 (서버가 필요한 스크립트인 경우)

### 작성 시

- [ ] 템플릿 사용
- [ ] 데이터베이스 연결 안전 종료 패턴 적용
- [ ] 명시적 exit code 반환
- [ ] 스키마를 추측하지 않고 확인

### 실행 후

- [ ] 정상 종료 확인 (exit code 0)
- [ ] 오류 발생 시 로그 확인
- [ ] 임시 데이터를 만들었으면 정리 확인
