# Telnet MCP 테스트 베스트 프랙티스

## 개요
Kiro IDE의 Telnet MCP 도구를 사용하여 Python MUD 엔진의 Telnet 서버 기능을 테스트하기 위한 표준 방법론입니다.
Telnet MCP는 프로그래밍 방식으로 Telnet 서버와 상호작용할 수 있는 도구입니다.

## 기본 원칙

### 1. Telnet MCP 도구 사용
- `mcp_telnet_mcp_telnet_connect`: Telnet 서버 연결
- `mcp_telnet_mcp_telnet_send`: 명령어 전송
- `mcp_telnet_mcp_telnet_read`: 응답 읽기
- `mcp_telnet_mcp_telnet_disconnect`: 연결 종료
- `mcp_telnet_mcp_telnet_list`: 활성 세션 목록

### 2. 테스트 계정
- **관리자**: player5426 / test1234 (is_admin=1)
- **일반 사용자**: testuser / test1234 (is_admin=0)
- 테스트 전 계정 존재 여부 확인 필요

### 3. 서버 연결 정보
- **호스트**: 127.0.0.1 (localhost)
- **포트**: 4000 (Telnet 서버)
- **프로토콜**: TCP (Telnet)
- **타임아웃**: 5000ms (기본값)

### 4. 진행 상황 출력 (필수)
- **중요**: read/send 한 메시지는 반드시 화면에 출력하여 진행 상황을 파악할 수 있게 할 것
- 모든 `mcp_telnet_mcp_telnet_send` 호출 후 전송한 명령어를 콘솔에 출력
- 모든 `mcp_telnet_mcp_telnet_read` 호출 후 수신한 데이터를 콘솔에 출력
- 예시:
  ```javascript
  console.log(`>>> 전송: ${command}`);
  await mcp_telnet_mcp_telnet_send({ sessionId, command });
  
  const result = await mcp_telnet_mcp_telnet_read({ sessionId, waitMs });
  console.log(`<<< 수신: ${result.data.substring(0, 100)}...`);
  ```

## 표준 테스트 패턴

### 기본 연결 및 로그인 패턴

```javascript
// 1. Telnet 서버 연결
const connectResult = await mcp_telnet_mcp_telnet_connect({
    host: "127.0.0.1",
    port: 4000,
    timeout: 5000
});
// 결과: { success: true, sessionId: "uuid", message: "Connected to 127.0.0.1:4000" }

const sessionId = connectResult.sessionId;

// 2. 초기 메시지 읽기 (환영 메시지 및 메뉴)
const initialMsg = await mcp_telnet_mcp_telnet_read({
    sessionId: sessionId,
    waitMs: 1000
});
// 결과: 환영 메시지 및 "1. 로그인 2. 회원가입 3. 종료" 메뉴

// 3. 로그인 선택 (1번)
await mcp_telnet_mcp_telnet_send({
    sessionId: sessionId,
    command: "1"
});

await mcp_telnet_mcp_telnet_read({
    sessionId: sessionId,
    waitMs: 1000
});
// 결과: "사용자명: " 프롬프트

// 4. 사용자명 입력 (관리자 계정)
await mcp_telnet_mcp_telnet_send({
    sessionId: sessionId,
    command: "player5426"
});

await mcp_telnet_mcp_telnet_read({
    sessionId: sessionId,
    waitMs: 1000
});
// 결과: "비밀번호: " 프롬프트

// 5. 비밀번호 입력
await mcp_telnet_mcp_telnet_send({
    sessionId: sessionId,
    command: "test1234"
});

const loginResult = await mcp_telnet_mcp_telnet_read({
    sessionId: sessionId,
    waitMs: 1500
});
// 결과: 로그인 성공 메시지 및 시작 방 정보
```

## 로그인 절차

### 1. 초기 메뉴
서버 접속 시 다음 메뉴가 표시됩니다:
```
╔═══════════════════════════════════════════════════════════════╗
║        Echoes of the Fallen Age                               ║
║        몰락의 대륙, 카르나스에 오신 것을 환영합니다           ║
╚═══════════════════════════════════════════════════════════════╝

1. 로그인 (login)
2. 회원가입 (register)
3. 종료 (quit)

선택>
```

### 2. 로그인 순서
1. 메뉴에서 `1` 입력 (로그인 선택)
2. 사용자명 입력
   - 관리자: `player5426`
   - 일반 사용자: `testuser`
3. 비밀번호 입력 (예: `test1234`)
4. 로그인 성공 시 시작 방에 스폰

### 3. 로그인 성공 확인
```
🏰 Town Square (또는 Forest)
============================================================
A bustling town square with a fountain in the center...

🚪 출구: north, east

✅ 'player5426'님, 환영합니다! (또는 'testuser'님)

게임에 입장했습니다!
'help' 명령어로 도움말을 확인하세요.

>
```

## 명령어 테스트 패턴

### 기본 명령어 테스트
```javascript
// look 명령어
await mcp_telnet_mcp_telnet_send({ sessionId, command: "look" });
const lookResult = await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1000 });

// 이동 명령어 (방향)
await mcp_telnet_mcp_telnet_send({ sessionId, command: "east" });
const moveResult = await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1000 });

// 이동 명령어 (go 사용)
await mcp_telnet_mcp_telnet_send({ sessionId, command: "go south" });
const goResult = await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1000 });

// 능력치 확인
await mcp_telnet_mcp_telnet_send({ sessionId, command: "stats" });
const statsResult = await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1000 });

// 인벤토리 확인
await mcp_telnet_mcp_telnet_send({ sessionId, command: "inventory" });
const invResult = await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1000 });

// 도움말
await mcp_telnet_mcp_telnet_send({ sessionId, command: "help" });
const helpResult = await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1000 });
```

### 관리자 명령어 테스트
```javascript
// 좌표 기반 이동 (admin 전용)
await mcp_telnet_mcp_telnet_send({ sessionId, command: "goto 5 7" });
const gotoResult = await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1500 });

// 방 생성 (admin 전용)
await mcp_telnet_mcp_telnet_send({ sessionId, command: "createroom test_room 테스트방" });
const createResult = await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1000 });

// 출구 생성 (admin 전용)
await mcp_telnet_mcp_telnet_send({ sessionId, command: "createexit room1 north room2" });
const exitResult = await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1000 });
```

### 전투 명령어 테스트
```javascript
// 몬스터 공격
await mcp_telnet_mcp_telnet_send({ sessionId, command: "attack goblin" });
const attackResult = await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1500 });

// 전투 중 행동
await mcp_telnet_mcp_telnet_send({ sessionId, command: "attack" });
const combatResult = await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1000 });

await mcp_telnet_mcp_telnet_send({ sessionId, command: "defend" });
const defendResult = await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1000 });

await mcp_telnet_mcp_telnet_send({ sessionId, command: "flee" });
const fleeResult = await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1000 });

// 전투 상태 확인
await mcp_telnet_mcp_telnet_send({ sessionId, command: "combat" });
const statusResult = await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1000 });
```

## 응답 처리 가이드

### 1. waitMs 설정

#### 표준 설정 (안정적)
- **초기 연결**: 1000ms
- **일반 명령어**: 1000ms
- **로그인/이동**: 1000-1500ms
- **전투 명령어**: 1500ms
- **복잡한 명령어**: 2000ms

#### 최적화 설정 (빠른 테스트)
- **초기 연결**: 500ms
- **일반 명령어**: 500ms
- **로그인**: 800ms
- **전투 명령어**: 1000ms
- **복잡한 명령어**: 1200ms

**권장**: 로컬 테스트 시 최적화 설정 사용, 원격 서버 테스트 시 표준 설정 사용

### 2. 응답 데이터 구조
```javascript
{
    "success": true,
    "data": "서버 응답 텍스트 (ANSI 색상 코드 포함)"
}
```

### 3. ANSI 색상 코드
응답에는 ANSI 색상 코드가 포함되어 있습니다:
- `\u001b[32m`: 녹색 (성공 메시지)
- `\u001b[31m`: 빨간색 (에러 메시지)
- `\u001b[36m`: 청록색 (정보 메시지)
- `\u001b[93m`: 노란색 (아이템 이름)
- `\u001b[94m`: 파란색 (방 이름)
- `\u001b[0m`: 색상 리셋

## 에러 처리

### 연결 실패
```javascript
try {
    const result = await mcp_telnet_mcp_telnet_connect({
        host: "127.0.0.1",
        port: 4000,
        timeout: 5000
    });
    
    if (!result.success) {
        console.error("연결 실패:", result.message);
        return;
    }
} catch (error) {
    console.error("연결 오류:", error);
}
```

### 타임아웃
```javascript
// waitMs를 충분히 길게 설정
const result = await mcp_telnet_mcp_telnet_read({
    sessionId: sessionId,
    waitMs: 2000  // 복잡한 명령어는 더 긴 대기 시간
});
```

### 세션 관리
```javascript
// 활성 세션 목록 확인
const sessions = await mcp_telnet_mcp_telnet_list();

// 사용 후 반드시 연결 종료
await mcp_telnet_mcp_telnet_disconnect({ sessionId: sessionId });
```

## 서버 실행 확인

### 백그라운드 실행
```bash
# 서버 시작 (controlPwshProcess 사용)
controlPwshProcess({
    action: "start",
    command: "source mud_engine_env/Scripts/activate && PYTHONPATH=. python -m src.mud_engine.main"
});

# 프로세스 출력 확인
getProcessOutput({ processId: processId, lines: 30 });

# 서버 로그 확인
tail -f logs/mud_engine-*.log
```

### 서버 시작 확인 메시지
```
🎮 Python MUD Engine v0.1.0
🌐 웹 서버가 http://127.0.0.1:8080 에서 실행 중입니다. (레거시)
📡 Telnet 서버가 telnet://0.0.0.0:4000 에서 실행 중입니다.
Ctrl+C를 눌러 서버를 종료할 수 있습니다.
```

## 테스트 체크리스트

### 테스트 전
- [ ] 서버가 실행 중인지 확인 (포트 4000)
- [ ] 테스트 계정이 존재하는지 확인
- [ ] Telnet MCP 도구가 사용 가능한지 확인

### 테스트 중
- [ ] 초기 메뉴가 정상 표시되는지 확인
- [ ] 로그인이 성공하는지 확인
- [ ] 명령어 응답이 정상적으로 수신되는지 확인
- [ ] 에러 메시지가 적절하게 표시되는지 확인
- [ ] sessionId가 유지되는지 확인
- [ ] **모든 send/read 메시지가 콘솔에 출력되는지 확인 (필수)**

### 테스트 후
- [ ] 연결이 정상적으로 종료되는지 확인
- [ ] 서버 로그에서 오류가 없는지 확인
- [ ] 테스트 결과를 문서화
- [ ] 모든 세션이 정리되었는지 확인

## 실제 사용 예시

### 기본 이동 테스트
```javascript
// 1. 연결 및 로그인 (일반 사용자)
const { sessionId } = await connect_and_login("testuser", "test1234");

// 2. 현재 위치 확인
await send_and_read(sessionId, "look", 1000);

// 3. 동쪽으로 이동
await send_and_read(sessionId, "east", 1000);

// 4. 남쪽으로 이동
await send_and_read(sessionId, "south", 1000);

// 5. 북쪽으로 이동
await send_and_read(sessionId, "north", 1000);

// 6. 서쪽으로 이동
await send_and_read(sessionId, "west", 1000);

// 7. 잘못된 방향 이동 시도
await send_and_read(sessionId, "west", 1000);
// 예상: "❌ west 방향으로는 갈 수 없습니다."

// 8. 연결 종료
await mcp_telnet_mcp_telnet_send({ sessionId, command: "quit" });
await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1000 });
await mcp_telnet_mcp_telnet_disconnect({ sessionId });
```

### goto 명령어 테스트 (관리자)
```javascript
// 1. 관리자 계정으로 로그인
const { sessionId } = await connect_and_login("player5426", "test1234");

// 2. 좌표로 이동 테스트
await send_and_read(sessionId, "goto 5 7", 1500);
await send_and_read(sessionId, "look", 1000);

// 3. 다른 좌표로 이동
await send_and_read(sessionId, "goto 0 0", 1500);
await send_and_read(sessionId, "look", 1000);

// 4. 잘못된 좌표 테스트
await send_and_read(sessionId, "goto 99 99", 1000);
// 예상: 에러 메시지

// 5. 잘못된 입력 테스트
await send_and_read(sessionId, "goto abc def", 1000);
// 예상: 에러 메시지

// 6. 종료
await disconnect(sessionId);
```

### 전투 시스템 테스트
```javascript
// 1. 로그인 (관리자 또는 일반 사용자)
const { sessionId } = await connect_and_login("player5426", "test1234");

// 2. 몬스터가 있는 위치로 이동 (관리자만 가능)
await send_and_read(sessionId, "goto 7 7", 1500);
await send_and_read(sessionId, "look", 1000);

// 3. 전투 시작
await send_and_read(sessionId, "attack goblin", 1500);

// 4. 전투 진행
await send_and_read(sessionId, "attack", 1000);
await send_and_read(sessionId, "look", 1000);

// 5. 종료
await disconnect(sessionId);
```

### 사용자 이름 변경 테스트
```javascript
// 1. 일반 사용자로 로그인
const { sessionId } = await connect_and_login("testuser", "test1234");

// 2. 이름 변경
await send_and_read(sessionId, "changename 새로운이름", 1500);
// 예상: "✅ 이름이 'testuser'에서 '새로운이름'(으)로 변경되었습니다!"

// 3. 재변경 시도 (하루 한 번 제한)
await send_and_read(sessionId, "changename 또다른이름", 1000);
// 예상: "❌ 이름은 하루에 한 번만 변경할 수 있습니다. 다음 변경까지 24.0시간 남았습니다."

// 4. 종료
await disconnect(sessionId);
```

## 성능 최적화

### 빠른 테스트를 위한 헬퍼 함수

헬퍼 함수를 사용하면 테스트 시간을 **50% 이상 단축**할 수 있습니다.

#### 빠른 로그인 헬퍼 (최적화 버전)
```javascript
async function quick_login(username, password) {
    console.log(`>>> 로그인 시작: ${username}`);
    
    const connectResult = await mcp_telnet_mcp_telnet_connect({
        host: "127.0.0.1",
        port: 4000,
        timeout: 5000
    });
    
    const sessionId = connectResult.sessionId;
    
    // 최적화된 대기 시간 사용
    await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 500 });
    await mcp_telnet_mcp_telnet_send({ sessionId, command: "1" });
    await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 500 });
    await mcp_telnet_mcp_telnet_send({ sessionId, command: username });
    await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 500 });
    await mcp_telnet_mcp_telnet_send({ sessionId, command: password });
    const loginResult = await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 800 });
    
    console.log(`<<< 로그인 완료: ${username}`);
    return { sessionId, loginResult };
}
```

#### 명령어 전송 및 읽기 헬퍼
```javascript
async function send_and_read(sessionId, command, waitMs = 500) {
    console.log(`>>> 전송: ${command}`);
    await mcp_telnet_mcp_telnet_send({ sessionId, command });
    const result = await mcp_telnet_mcp_telnet_read({ sessionId, waitMs });
    console.log(`<<< 수신: ${result.data.substring(0, 100)}...`);
    return result.data;
}
```

#### 빠른 종료 헬퍼
```javascript
async function quick_disconnect(sessionId) {
    console.log(`>>> 연결 종료`);
    await mcp_telnet_mcp_telnet_send({ sessionId, command: "quit" });
    await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 500 });
    await mcp_telnet_mcp_telnet_disconnect({ sessionId });
    console.log(`<<< 연결 종료 완료`);
}
```

### 빠른 테스트 패턴 예시

#### 기본 테스트 (최적화)
```javascript
// 1. 빠른 로그인
const { sessionId } = await quick_login("player5426", "test1234");

// 2. 명령어 체인 (최적화된 대기 시간)
await send_and_read(sessionId, "look", 500);
await send_and_read(sessionId, "goto 5 7", 500);
await send_and_read(sessionId, "look", 500);

// 3. 빠른 종료
await quick_disconnect(sessionId);
```

#### 전투 테스트 (최적화)
```javascript
const { sessionId } = await quick_login("player5426", "test1234");

// 몬스터 위치로 이동 및 전투
await send_and_read(sessionId, "goto 7 7", 500);
await send_and_read(sessionId, "attack goblin", 800);
await send_and_read(sessionId, "attack", 500);
await send_and_read(sessionId, "flee", 500);

await quick_disconnect(sessionId);
```

### 성능 비교

#### 기존 방식 (느림)
```javascript
// 총 소요 시간: ~8초
await mcp_telnet_mcp_telnet_send({ sessionId, command: "look" });
await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1000 });

await mcp_telnet_mcp_telnet_send({ sessionId, command: "goto 5 7" });
await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1500 });

await mcp_telnet_mcp_telnet_send({ sessionId, command: "look" });
await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1000 });
```

#### 최적화 방식 (빠름)
```javascript
// 총 소요 시간: ~3초 (62% 단축)
await send_and_read(sessionId, "look", 500);
await send_and_read(sessionId, "goto 5 7", 500);
await send_and_read(sessionId, "look", 500);
```

## 헬퍼 함수 패턴 (표준 버전)

### 연결 및 로그인 헬퍼
```javascript
async function connect_and_login(username, password) {
    // 연결
    const connectResult = await mcp_telnet_mcp_telnet_connect({
        host: "127.0.0.1",
        port: 4000,
        timeout: 5000
    });
    
    const sessionId = connectResult.sessionId;
    
    // 초기 메시지 읽기
    await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1000 });
    
    // 로그인 선택
    await mcp_telnet_mcp_telnet_send({ sessionId, command: "1" });
    await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1000 });
    
    // 사용자명 입력
    await mcp_telnet_mcp_telnet_send({ sessionId, command: username });
    await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1000 });
    
    // 비밀번호 입력
    await mcp_telnet_mcp_telnet_send({ sessionId, command: password });
    await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1500 });
    
    return { sessionId };
}
```

### 명령어 전송 및 읽기 헬퍼
```javascript
async function send_and_read(sessionId, command, waitMs = 1000) {
    await mcp_telnet_mcp_telnet_send({ sessionId, command });
    const result = await mcp_telnet_mcp_telnet_read({ sessionId, waitMs });
    return result.data;
}
```

### 연결 종료 헬퍼
```javascript
async function disconnect(sessionId) {
    await mcp_telnet_mcp_telnet_send({ sessionId, command: "quit" });
    await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1000 });
    await mcp_telnet_mcp_telnet_disconnect({ sessionId });
}
```

## 주의사항

### Telnet MCP 사용 시
- **세션 ID 관리**: 연결 후 받은 sessionId를 모든 후속 호출에 사용
- **응답 대기**: 각 명령어 후 충분한 waitMs 설정
- **연결 종료**: 테스트 완료 후 반드시 disconnect 호출
- **ANSI 코드**: 응답에 포함된 ANSI 색상 코드 처리 고려

### 사용자편의 (필수 준수)
- **필수**: read/send 한 메시지는 반드시 화면에 출력해서 진행 상황을 파악할 수 있게 할 것
- **필수**: 헬퍼 함수에 console.log를 포함하여 자동으로 진행 상황 표시
- **필수**: 모든 Telnet MCP 호출 시 전송/수신 내용을 콘솔에 출력
- 출력 형식:
  - 전송: `console.log(\`>>> 전송: \${command}\`);`
  - 수신: `console.log(\`<<< 수신: \${result.data.substring(0, 100)}...\`);`

### 타이밍 최적화
- **로컬 테스트**: 500ms 대기 시간으로 빠른 테스트 가능
- **원격 테스트**: 1000ms 이상 대기 시간 권장
- **복잡한 명령어**: DB 조회나 계산이 많은 경우 더 긴 대기 시간 필요
- **응답 누락 시**: waitMs를 점진적으로 증가시켜 테스트

### 성능 팁
- 헬퍼 함수 사용으로 코드 중복 제거 및 테스트 시간 단축
- 여러 명령어를 연속 실행할 때 최적화된 대기 시간 사용
- 불필요한 로그 출력 최소화 (필요시에만 상세 로그)

### 서버 상태
- 테스트 전 서버가 실행 중인지 확인
- 포트 4000이 사용 가능한지 확인
- 서버 로그를 통해 실시간 상태 모니터링

## 디버깅 팁

### 서버 로그 확인
```bash
# 실시간 로그 모니터링
tail -f logs/mud_engine-*.log | grep -E "(ERROR|WARNING|player5426)"

# 특정 플레이어 로그 필터링
tail -f logs/mud_engine-*.log | grep player5426
```

### 응답 내용 확인
```javascript
// 응답 데이터 출력
const result = await mcp_telnet_mcp_telnet_read({ sessionId, waitMs: 1000 });
console.log("서버 응답:", result.data);

// ANSI 코드 제거하여 확인
const cleanText = result.data.replace(/\u001b\[[0-9;]*m/g, '');
console.log("정리된 응답:", cleanText);
```

### 세션 상태 확인
```javascript
// 활성 세션 목록
const sessions = await mcp_telnet_mcp_telnet_list();
console.log("활성 세션:", sessions);
```

## 참고 자료

### 관련 파일
- `docs/telnet_test_guide.md` - Telnet 테스트 가이드 (socket 기반)
- `src/mud_engine/server/telnet_server.py` - Telnet 서버 구현
- `src/mud_engine/server/telnet_session.py` - Telnet 세션 관리
- `src/mud_engine/commands/` - 명령어 구현

### 서버 코드
- Telnet 서버는 포트 4000에서 실행
- 웹 서버는 포트 8080에서 실행 (레거시)
- 두 서버는 동일한 GameEngine 인스턴스 공유

## 결론

Telnet MCP를 사용하면 프로그래밍 방식으로 Telnet 서버를 테스트할 수 있어,
자동화된 테스트 시나리오 작성이 가능합니다.
이 문서의 패턴을 따라 일관되고 재사용 가능한 테스트를 작성하세요.
