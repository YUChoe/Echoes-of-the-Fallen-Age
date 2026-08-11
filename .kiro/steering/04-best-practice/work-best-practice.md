# 작업 환경 베스트 프랙티스

## Git Bash 명령어 (Windows 환경)

### 프로젝트 구조 분석
```bash
# 디렉토리 구조 확인
find src -type d -name "*" | head -20
ls -la src/mud_engine/
find src/mud_engine -maxdepth 2 -type d

# 파일 검색
find . -name "*.py" | grep -E "(session|player|command)"
find . -name "*.py" -exec grep -l "method_name" {} \;

# 코드 내용 검색
grep -r "class Session" src/
grep -r "def send_message" src/ --include="*.py"
grep -r "method_name" src/ --include="*.py"

# 메서드 시그니처 확인
grep -r "def broadcast_to_room" src/mud_engine/ --include="*.py"
grep -rn "broadcast_to_room" src/ --include="*.py"
grep -r "def method_name" src/ --include="*.py"
find . -name "*.py" -exec grep -Hn "def method_name" {} \;
```

### 프로세스 관리
```bash
# ✅ 올바른 bash 명령어
ps aux | grep python
netstat -an | grep -E '4000|4001'

# ❌ Windows CMD 명령어 (GitBash에서 사용 금지)
tasklist | findstr python
```

MSYS 의 `kill` 은 네이티브 Windows 프로세스에 시그널을 전달하지 못한다.
정상 종료가 필요하면 런처를 쓴다. `01-python-dev/dev-environment.md` 참고.

### 데이터베이스 스키마 확인

`sqlite3` CLI 는 이 환경에 없다. Python 스크립트로 읽는다.

```bash
# 어드민 리소스 8종의 실제 스키마
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/dump_admin_schema.py

# 실제 참조 관계
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/dump_admin_references.py
```

스키마는 추측하지 않는다. `data/DATABASE_SCHEMA.md` 와 실제 테이블이 어긋난
경우가 있었다.

## 개발 환경 설정 및 관리

### Python 가상환경 관리
```bash
# 가상환경은 .venv 다. 이미 만들어져 있다
# 의존성 설치
.venv/Scripts/python.exe -m pip install -r requirements.txt

# 타입 검사 및 린트 (서버 실행 전 필수)
PYTHONPATH=. .venv/Scripts/mypy.exe src/
.venv/Scripts/ruff.exe check src/ scripts/ tests/

# 테스트 실행
PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -m pytest tests/ -q
```

`black` 과 `flake8` 은 쓰지 않는다. 린트는 ruff 하나로 통일했다.

### 서버 실행 및 관리
```bash
# 서버 시작
PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -m src.mud_engine.main

# 서버 상태 확인 (게임 4000, 어드민 4001)
ps aux | grep python
netstat -an | grep -E '4000|4001'

# 정상 종료가 필요하면 런처로 띄운다
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/run_server.py --seconds 30
```

## 개발 프로세스 및 문제 해결 방법론

### 1. 사전 분석 원칙
- 새로운 기능 구현 전 반드시 기존 코드 구조 분석
- 유사 기능의 기존 구현 패턴 확인 후 일관성 유지
- 모듈 import 경로를 가정하지 말고 실제 구조 확인
- 데이터베이스 스키마와 실제 데이터 구조 사전 파악

### 2. 단계별 접근법
1. **사전 분석**: Git Bash로 프로젝트 구조 파악
2. **구현**: 기존 패턴 준수로 일관성 유지
3. **검증**: 각 수정 후 즉시 테스트
4. **최종 확인**: 전체 시스템 통합 테스트

### 3. 문제 해결 우선순위
시스템 문제 대응 우선순위:
1. **긴급**: 서버 크래시, 보안 문제
2. **높음**: 핵심 기능 오작동 (별칭 기능, 명령어 실행 실패)
3. **중간**: UI/UX 문제 (메시지 중복 출력, 색상 불일치)
4. **낮음**: 개선사항 (코드 리팩토링, 성능 최적화)

### 4. 발견된 오류 처리 원칙
- **즉시 수정 규칙**: 명확한 오류 발견 시 다른 작업보다 우선 수정
- **완결성 원칙**: 한 번 시작한 수정은 완료까지 진행
- **검증 원칙**: 수정 후 즉시 해당 기능 테스트

## 디버깅 및 데이터 분석 전략

### 체계적 디버깅 접근법
1. **현상 정확히 파악**: 개별 증상이 아닌 전체 시스템 관점에서 분석
2. **서버-클라이언트 양쪽 로그 확인**: 데이터 흐름 전체 추적
3. **데이터 흐름 추적**: DB → Repository → Model → Business Logic
4. **에러 메시지 정확히 분석**: 표면적 증상이 아닌 근본 원인 파악
5. **한 번에 하나씩 수정하여 검증**: 단계별 롯백 가능한 구조

### 파일 및 코드 검색 패턴
```bash
# 클래스 정의 찾기
grep -r "class ClassName" src/

# 메서드 정의와 사용처 모두 찾기
grep -rn "def method_name\|method_name(" src/ --include="*.py"

# 특정 패턴 검색
grep -r "session\.player" src/ --include="*.py"
grep -r "broadcast_to_room" src/ --include="*.py"

# 매니저 클래스 및 메서드 검색
grep -r "class.*Manager" src/ --include="*.py"
grep -r "def get_.*" src/ --include="*.py"
```

### 데이터 구조 및 타입 검증
```bash
# 실제 데이터 구조 확인
sqlite3 data/mud_engine.db "SELECT * FROM rooms WHERE id LIKE 'forest%' LIMIT 3"
sqlite3 data/mud_engine.db "PRAGMA table_info(monsters)"

# JSON 필드 식별
sqlite3 data/mud_engine.db "SELECT name, properties FROM monsters LIMIT 1"

# 타입 힐트 검증
mypy src/mud_engine/game/repositories.py
mypy src/mud_engine/game/models.py
```

## 테스트 및 검증 방법론

### 프로토콜 하니스 검증

브라우저 테스트는 없다. 레거시 웹서버가 제거되어 접속할 곳이 없고, Godot
클라이언트는 아직 만들지 않았다. `scripts/harness/` 가 유일한 검증 수단이다.

```bash
# 서버 실행
PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -m src.mud_engine.main

# 하니스 (별도 셸에서)
PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -m scripts.harness.run_all
```

테스트 계정은 `player5426` / `test1234` (관리자)다. 절차와 시나리오 구성은
`harness-test.md` 에 있다.

#### 단계별 검증 순서
1. **정적 검사**: mypy + ruff 통과. 실패하면 서버를 띄우지 않는다
2. **단위 테스트**: pytest
3. **하니스**: 서버를 띄우고 실패 0 확인
4. **감사 로그**: 어드민 작업을 했으면 `logs/admin_audit.log` 확인

### 하위 호환성 및 베이스라인 관리
- 기존 기능 파기 방지를 위해 업데이트 전후 테스트
- API 변경 시 기존 클라이언트와의 호환성 고려
- 메시지 형식 일관성 유지

### 자동화된 검증 도구
```bash
# 정적 분석 도구 실행
mypy src/ --strict
black src/ --check
flake8 src/

# 단위 테스트
pytest tests/ -v
pytest tests/test_combat.py -v

# 서버 상태 및 로그 모니터링
tail -f logs/mud_engine.log
```

## 환경 설정 및 베스트 프랙티스

### Git Bash 사용 원칙 (Windows 환경)
- Windows 환경에서는 Git Bash 명령어만 사용
- CMD/PowerShell 명령어 사용 금지
- bash 호환 명령어로 프로젝트 분석 수행

### 개발 도구 활용
- `find`와 `grep`을 조합한 효율적인 코드 검색
- 정규식을 활용한 패턴 매칭
- 파일 타입별 필터링으로 정확한 검색

### 코드 분석 체크리스트

#### 새로운 기능 구현 전
- [ ] `find`와 `grep` 명령어로 프로젝트 구조 파악
- [ ] 유사 기능 검색으로 기존 패턴 확인
- [ ] 관련 클래스와 메서드 구조 파악
- [ ] 의존성 및 연동 방식 파악
- [ ] 데이터베이스 스키마 및 실제 데이터 구조 확인

#### 디버깅 수행 시
- [ ] 에러 메시지 정확히 분석
- [ ] 실제 데이터베이스 데이터 구조 먼저 확인
- [ ] 객체 타입과 내용 동시 로깅
- [ ] 데이터 변환 지점마다 중간 결과 확인
- [ ] 전체 데이터 흐름 추적 (DB → Repository → Model → Business Logic)
- [ ] 오류 발생 지점의 컨텍스트 정보 수집

#### 테스트 수행 시
- [ ] 정상 케이스 동작 확인
- [ ] 예외 상황 처리 확인
- [ ] 서버 로그를 통한 내부 동작 검증
- [ ] 다른 플레이어에게 미치는 영향 확인
- [ ] 브라우저 기반 실제 사용자 시나리오 검증