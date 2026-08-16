# 프로토콜 하니스 테스트

## 개요

서버는 개행 구분 JSON 라인 프로토콜을 쓴다. 텍스트 명령어와 메뉴, ANSI 색상은
페이즈2에서 제거됐다. Godot 클라이언트가 아직 없으므로 `scripts/harness/` 가
유일한 검증 수단이다.

Telnet MCP 도구는 쓰지 않는다. 대화형 텍스트 세션을 전제하는 도구이며 현재
프로토콜과 맞지 않는다.

## 채널

| 채널 | 포트 | 첫 발화 | IAC 협상 |
|---|---|---|---|
| 게임 | 4000 | 서버가 `welcome` 을 보낸다 | 있음 |
| 어드민 | 4001 | 서버가 `welcome` 을 보낸다 | 없음 |

두 채널의 `welcome` 에 `channel` 필드가 있다(`game` / `admin`). 타 채널 전용
메시지를 보내면 `NOT_APPLICABLE` 로 거절된다.

어드민 포트는 기본 바인드가 루프백이다.

## 테스트 계정

- 관리자: `player5426` / `test1234` (`is_admin=1`)
- 일반 계정: 로그인 이력이 없고 비밀번호를 모른다. 비관리자 경로는 단위 테스트로 덮는다

## 실행

```bash
# 1. 정적 검사 (서버 실행 전 필수)
PYTHONPATH=. .venv/Scripts/mypy.exe src/
.venv/Scripts/ruff.exe check src/ scripts/ tests/

# 2. 단위 테스트
PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -m pytest tests/ -q

# 3. 서버 기동
PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -m src.mud_engine.main

# 4. 하니스 (서버 실행 중이어야 한다)
PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -m scripts.harness.run_all

# 서버 없이 단위 검증만
PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -m scripts.harness.run_all --unit-only
```

## 판정 기준

실패 0만 확인한다. 건너뜀 수가 흔들리는 것은 정상이다. 읽을 수 있는 아이템,
컨테이너, 적대 몬스터가 테스트 계정 사거리에 있어야 하는 시나리오들이고 몬스터가
로밍하기 때문이다.

어드민 시나리오와 인증 시나리오는 몬스터 로밍의 영향을 받지 않으므로 항상
통과해야 한다.

## 시나리오 구성

| 시나리오 | 대상 |
|---|---|
| `framing (unit)` | 라인 분할, IAC 필터. 서버 불필요 |
| `framing (server)` | 서버 왕복 프레이밍 |
| `auth` | `welcome`, 회원가입, 로그인, `ping`/`pong`, 봉투 위반, 채널 구별 |
| `action` | 액션 디스패처, 거절 코드, 채팅, 대화, 전투 |
| `admin` | 어드민 인증, 리소스 CRUD, 참조 무결성, 액션 14종, 통계, 맵, 계정 생성 |

## 새 시나리오를 쓸 때

기대값은 구현에서 가져오지 않고 계약 문서(`docs/protocol/`)의 값을 그대로 적는다.
구현과 계약이 어긋나면 드러나야 한다.

프로덕션 데이터를 바꾸지 않는다. 어드민 CRUD 검증은 좌표 -9999, -9998 에 임시
방을 만들었다가 지운다. 액션 검증은 데이터를 바꾸지 않는 것만 호출한다.

`HarnessClient` 는 어드민 채널에 붙일 때 `filter_telnet=False` 로 만든다.
어드민 채널은 IAC 협상을 하지 않는다.

```python
from .client import DEFAULT_ADMIN_PORT, HarnessClient

with HarnessClient(port=DEFAULT_ADMIN_PORT, verbose=False, filter_telnet=False) as c:
    c.connect()
    c.wait_for("welcome", timeout_ms=3000)
    seq = c.send_json({"type": "admin_login", "username": "player5426", "password": "test1234"})
    c.wait_for("admin_login_result", seq=seq, timeout_ms=5000)
```

## 서버 종료

Windows 에서는 MSYS 의 `kill` 이 네이티브 프로세스에 시그널을 전달하지 못한다.
정상 종료가 필요하면 런처를 쓴다.

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/run_server.py --seconds 30
```

강제 종료는 WAL 체크포인트와 세션 종료 알림을 건너뛴다.

## 로그 확인

```bash
# 서버 로그
tail -f logs/mud_engine-*.log | grep -E "(ERROR|WARNING)"

# 어드민 감사 로그. 한 줄이 한 건의 JSON 이다
tail logs/admin_audit.log
```

## 참고

- `docs/protocol/` — 계약. 세 저장소의 단일 기준이다
- `scripts/harness/client.py` — 라인 단위 검증 클라이언트
- `scripts/dump_admin_schema.py` — 실제 테이블 스키마 확인
- `scripts/dump_admin_references.py` — 실제 참조 관계 확인
