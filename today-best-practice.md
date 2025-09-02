# 오늘의 베스트 프랙티스 (2025-09-02)

## 몬스터 성향 정보 표시 기능 구현 중 발생한 실수와 해결 방법

### 문제 상황
몬스터의 성향 정보(공격적/수동적/중립적)가 클라이언트에서 undefined로 표시되는 문제 발생

### 주요 실수들과 해결 방법

#### 1. 브라우저 캐시 문제 간과 (Critical)

**실수한 부분:**
- 서버 측 코드(GameModule.js)를 수정한 후 브라우저에서 즉시 테스트 진행
- 브라우저가 캐시된 이전 버전의 JavaScript 파일을 사용하고 있다는 것을 간과
- 코드 변경사항이 반영되지 않았는데도 계속 클라이언트 측 문제로 판단

**올바른 해결법:**
```bash
# 1. 서버 재시작 (필수)
ps aux | grep python
kill -9 <PID>
source mud_engine_env/Scripts/activate && PYTHONPATH=. python -m src.mud_engine.main &

# 2. 브라우저 강제 새로고침 (Ctrl+F5)
# 3. 개발자 도구에서 실제 로드된 파일 버전 확인
```

**교훈:**
- 정적 파일(CSS, JS) 수정 후 반드시 서버 재시작 + 브라우저 새로고침
- 브라우저 개발자 도구에서 실제 로드된 코드 내용 확인 필수

#### 2. 실시간 디버깅 방법 활용

**효과적인 해결 방법:**
```javascript
// 브라우저에서 실제 로드된 메서드 내용 확인
console.log(window.mudClient.gameModule.handleRoomInfo.toString());

// 성향 정보 코드 포함 여부 확인
const hasTemperamentCode = handleRoomInfoSource.includes('temperamentMap');
console.log('성향 정보 코드 포함 여부:', hasTemperamentCode);

// 실시간으로 메서드 재정의하여 테스트
window.mudClient.gameModule.handleRoomInfo = function(data) {
    // 수정된 로직으로 즉시 테스트
};
```

**교훈:**
- 브라우저에서 실시간으로 메서드를 재정의하여 즉시 테스트 가능
- 코드 변경사항이 반영되지 않을 때 임시 해결책으로 활용
- 정상 작동 확인 후 실제 소스 파일에 반영

#### 3. 데이터 흐름 추적의 중요성

**올바른 디버깅 접근법:**
```javascript
// 1단계: WebSocket 메시지 수신 확인
const originalOnMessage = window.mudClient.ws.onmessage;
window.mudClient.ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'room_info') {
        console.log('몬스터 데이터:', data.room.monsters);
        data.room.monsters.forEach((monster, index) => {
            console.log(`몬스터 ${index + 1}:`, monster);
            console.log(`  - 타입: ${monster.monster_type}`);
            console.log(`  - 공격적: ${monster.is_aggressive}`);
        });
    }
    return originalOnMessage.call(this, event);
};

// 2단계: 메서드 호출 추적
const originalHandleRoomInfo = window.mudClient.gameModule.handleRoomInfo;
window.mudClient.gameModule.handleRoomInfo = function(data) {
    console.log('🔥 handleRoomInfo 호출됨!', data);
    return originalHandleRoomInfo.call(this, data);
};
```

**교훈:**
- 서버에서 데이터가 정상적으로 전송되는지 먼저 확인
- 클라이언트에서 데이터를 받고 있는지 WebSocket 메시지 가로채기로 확인
- 메서드가 실제로 호출되는지 추적

#### 4. 문제 원인 정확한 파악

**이번 사례의 실제 원인:**
- 서버: 몬스터 데이터에 성향 정보(`monster_type`, `is_aggressive` 등) 정상 전송 ✅
- 클라이언트: WebSocket으로 데이터 정상 수신 ✅
- 문제: `GameModule.handleRoomInfo`에서 성향 정보를 UI에 표시하지 않음 ❌

**잘못된 추정들:**
- "서버에서 몬스터 데이터를 전송하지 않는다" ❌
- "WebSocket 연결에 문제가 있다" ❌
- "데이터베이스에 성향 정보가 없다" ❌

**교훈:**
- 추측보다는 단계별 검증으로 정확한 원인 파악
- 서버 → 클라이언트 → UI 표시 전체 흐름을 순서대로 확인
- 각 단계에서 실제 데이터 내용 로깅으로 검증

### 성공적인 해결 과정

1. **서버 측 데이터 전송 확인**: 몬스터 정보에 성향 데이터가 포함되어 전송됨을 확인
2. **클라이언트 수신 확인**: WebSocket 메시지 가로채기로 데이터 정상 수신 확인
3. **UI 표시 로직 수정**: `handleRoomInfo`에서 성향 정보를 포함한 몬스터 표시 로직 추가
4. **실시간 테스트**: 브라우저에서 메서드 재정의로 즉시 테스트
5. **소스 반영**: 정상 작동 확인 후 실제 파일에 반영

### 최종 결과

**수정 전:**
```
• Green Slime (레벨 1, HP: 50/50)
• Wild Goblin (레벨 1, HP: 80/80)
```

**수정 후:**
```
• Green Slime (레벨 1, HP: 50/50) [수동적]
• Wild Goblin (레벨 1, HP: 80/80) [공격적]
```

### 핵심 교훈

1. **캐시 문제 우선 해결**: 코드 변경 후 반드시 서버 재시작 + 브라우저 새로고침
2. **단계별 검증**: 서버 → 클라이언트 → UI 순서로 데이터 흐름 추적
3. **실시간 디버깅 활용**: 브라우저에서 메서드 재정의로 즉시 테스트
4. **추측 금지**: 각 단계에서 실제 데이터 확인으로 정확한 원인 파악
5. **전체 흐름 이해**: 문제를 부분적으로 보지 말고 전체 시스템 관점에서 접근

이러한 접근 방법을 통해 복잡한 클라이언트-서버 통신 문제도 체계적으로 해결할 수 있습니다.