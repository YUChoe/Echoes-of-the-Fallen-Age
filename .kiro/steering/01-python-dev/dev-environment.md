# Python 개발 환경 규칙

## 프로젝트 환경
- Python 3.14.6
- 가상환경: `.venv`
- 메인 모듈: `src.mud_engine.main`
- 게임 포트(Telnet): 4000 / 어드민 포트: 4001
- src-layout 구조 (`src/mud_engine/`)

웹 포트 8080은 존재하지 않는다. 레거시 웹서버는 페이즈2에서 제거됐고 웹어드민은
어드민 채널(TCP 4001)로 이전했다.

어드민 포트는 기본 바인드가 루프백(`127.0.0.1`)이다. 외부에 노출하지 않는다.
`ADMIN_HOST`, `ADMIN_PORT`로 바꿀 수 있다.

## 기본 원칙
- PEP8 준수, snake_case 네이밍
- 가상 환경 필수, `PYTHONPATH=.` 항상 포함
- Windows 환경에서 Git Bash만 사용 (PowerShell/CMD 금지)
- 비동기 프로그래밍: `async/await` 패턴
- 리포지토리 패턴으로 DB 접근 추상화
- 이벤트 기반 아키텍처 (EventBus)
- 번역은 클라이언트 책임. 서버는 `message_key` + `params`만 보낸다
- 타입 힌트, enum 적극 활용
- 방어적 프로그래밍, 충분한 로깅

## 정적 검사 (실행 전 필수)
소스 수정 후 서버 실행 전에 mypy + ruff 모두 통과해야 함.

```bash
# mypy 타입 검사 (설정: setup.cfg [mypy])
PYTHONPATH=. .venv/Scripts/mypy.exe src/

# ruff 린트 검사 (설정: pyproject.toml [tool.ruff])
.venv/Scripts/ruff.exe check src/ scripts/ tests/
```

에러가 있으면 실행 금지.

ruff의 `ignore`에 `F401`(미사용 임포트), `F841`(미사용 지역변수), `E722`가
들어 있다. 코드를 삭제한 뒤 남는 임포트를 린트가 잡아주지 않으므로 직접 확인한다.
mypy도 잡지 않는다.

## 실행 명령어
```bash
# 서버 실행
PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -m src.mud_engine.main

# 테스트
PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -m pytest tests/ -q

# 프로토콜 하니스 (서버 실행 중이어야 한다)
PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -m scripts.harness.run_all

# 스크립트 (scripts/ 디렉토리)
./script_test.sh <스크립트명>
```

`PYTHONIOENCODING=utf-8`을 붙이지 않으면 한국어 출력이 cp949로 깨진다.

## 프로세스 관리

Windows에서는 MSYS의 `kill`이 네이티브 Windows 프로세스에 시그널을 전달하지
못한다. `taskkill`도 창 없는 콘솔 앱에는 `/F` 강제 종료만 가능하다. 강제 종료는
종료 절차를 건너뛰므로 WAL 체크포인트와 세션 종료 알림이 빠진다.

정상 종료가 필요하면 런처를 쓴다. 서버를 새 프로세스 그룹으로 띄우고
`CTRL_BREAK_EVENT`를 보내 SIGBREAK로 전달한다.

```bash
# Ctrl+Break 를 기다린다
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/run_server.py

# 지정한 시간 뒤 정상 종료. 검증 절차에 쓴다
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/run_server.py --seconds 30
```

```bash
ps aux | grep python
```

- Unix 환경에서는 `kill -2 <PID>`(SIGINT)가 동작한다
- `kill -9`(SIGKILL) 사용 금지: 종료 절차가 실행되지 않는다
- 시그널 핸들러는 재진입을 막고 예외를 던지지 않는다. `utils/shutdown.py`

## 서버 실행 상태 확인 (필수)
서버를 시작하기 전에 반드시 포트가 이미 사용 중인지 확인할 것.
```bash
# bash 환경에서 포트 사용 확인
ss -tlnp 2>/dev/null | grep -E '4000|4001' || netstat -an | grep -E '4000|4001'
```
- 포트가 사용 중이면 서버가 이미 실행 중인 것이므로 재시작하지 말 것
- 백그라운드로 시작한 서버는 대화 컨텍스트가 바뀌면 핸들을 잃으므로, 포트 체크로
  실행 여부를 판단할 것

## 금지사항
- PowerShell, CMD 사용
- 전역 Python 환경 사용
- 서비스 포트 변경 (프로세스 종료로 해결)
- mypy 또는 ruff 에러 무시하고 실행
- DB 스키마 추측: `data/DATABASE_SCHEMA.md` 확인 후 사용
