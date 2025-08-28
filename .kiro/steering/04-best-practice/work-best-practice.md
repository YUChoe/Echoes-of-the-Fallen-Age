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
kill -9 <PID>

# ❌ Windows CMD 명령어 (GitBash에서 사용 금지)
netstat -ano | findstr :8080
tasklist | findstr python
```

## 개발 프로세스

### 1. 사전 분석 원칙
- 새로운 기능 구현 전 반드시 기존 코드 구조 분석
- 유사 기능의 기존 구현 패턴 확인 후 일관성 유지
- 모듈 import 경로를 가정하지 말고 실제 구조 확인

### 2. 단계별 접근법
1. **사전 분석**: Git Bash로 프로젝트 구조 파악
2. **구현**: 기존 패턴 준수로 일관성 유지
3. **검증**: 각 수정 후 즉시 테스트

## 디버깅 전략

### 파일 및 코드 검색 패턴
```bash
# 클래스 정의 찾기
grep -r "class ClassName" src/

# 메서드 정의와 사용처 모두 찾기
grep -rn "def method_name\|method_name(" src/ --include="*.py"

# 특정 패턴 검색
grep -r "session\.player" src/ --include="*.py"
grep -r "broadcast_to_room" src/ --include="*.py"
```

### 문제 해결 순서
1. 현상 정확히 파악
2. 서버-클라이언트 양쪽 로그 확인
3. 데이터 흐름 추적
4. 에러 메시지 정확히 분석
5. 한 번에 하나씩 수정하여 검증

## 코드 분석 체크리스트

### 새로운 기능 구현 전
- [ ] `find`와 `grep` 명령어로 프로젝트 구조 파악
- [ ] 유사 기능 검색으로 기존 패턴 확인
- [ ] 관련 클래스와 메서드 구조 파악
- [ ] 의존성 및 연동 방식 파악

### 디버깅 시
- [ ] 에러 메시지 정확히 분석
- [ ] 관련 파일에서 올바른 사용법 검색
- [ ] 한 번에 하나씩 수정하여 테스트
- [ ] 메서드 시그니처와 실제 사용법 비교

## 환경 설정

### Git Bash 사용 원칙
- Windows 환경에서는 Git Bash 명령어만 사용
- CMD/PowerShell 명령어 사용 금지
- bash 호환 명령어로 프로젝트 분석 수행

### 개발 도구 활용
- `find`와 `grep`을 조합한 효율적인 코드 검색
- 정규식을 활용한 패턴 매칭
- 파일 타입별 필터링으로 정확한 검색