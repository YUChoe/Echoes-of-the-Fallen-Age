# Browser MCP 테스트 베스트 프랙티스

## 개요
브라우저 자동화를 통한 웹 애플리케이션 테스트 시 발생할 수 있는 실수들과 올바른 접근 방법을 정리한 가이드입니다.

## 표준 테스트 절차 (몬스터 스폰 테스트 기준)

### 1. 서버 백그라운드 실행
```bash
# 기존 프로세스 확인 및 종료
ps aux | grep python
kill -9 <PID>

# 서버 백그라운드 실행 (&를 사용하여 백그라운드 실행)
source mud_engine_env/Scripts/activate && PYTHONPATH=. python -m src.mud_engine.main &
```

### 2. Playwright MCP를 이용한 브라우저 접속
```javascript
// 브라우저 열기
await page.goto('http://localhost:8080');
```

### 3. 테스트 계정 로그인
- **계정**: aa / aaaabbbb (미리 생성된 테스트 계정)
- **권한**: 관리자 권한 보유
- **로그인 절차**: 사용자명 입력 → 비밀번호 입력 → 로그인 버튼 클릭

### 4. 테스트 대상 위치로 이동
```javascript
// 일반 모드로 전환 (명령어 입력 가능)
await page.click('button[name="일반 모드"]');

// forest_7_7로 이동 (몬스터 스폰 지역)
await page.fill('input[name="commandInput"]', 'goto forest_7_7');
await page.click('button[name="전송"]');
```

### 5. 몬스터 스폰 확인
```javascript
// look 명령어로 방 정보 새로고침
await page.fill('input[name="commandInput"]', 'look');
await page.click('button[name="전송"]');

// UI에서 몬스터 정보 확인
// 예상 결과: "👹 이곳에 있는 몬스터들:" 섹션에 몬스터 목록 표시
// 예시: • Green Slime (레벨 1, HP: 50/50)
//      • Wild Goblin (레벨 1, HP: 80/80)
```

### 6. 오류 분석 방법
- **브라우저 콘솔 로그**: 클라이언트 측 JavaScript 오류 및 디버깅 정보
- **서버 로그**: logs/ 디렉토리의 서버 측 로그 파일 확인
- **WebSocket 메시지**: 브라우저 개발자 도구 Network 탭에서 WebSocket 통신 확인
- **단계별 추적**: 서버 → 클라이언트 → 메시지 핸들러 → UI 업데이트 전체 흐름 확인

### 7. 브라우저 디버깅 내용 소스 코드 반영 원칙
- **반드시 반영**: 브라우저에서 임시로 수정한 디버깅 코드는 실제 소스 코드에 반영
- **선별적 유지**: 과도한 디버깅 로그는 제거하고 필요한 것만 유지
- **캐시 문제 방지**: 소스 코드 수정 후 반드시 서버 재시작 및 브라우저 새로고침

### 8. 성공 기준
- [ ] 서버가 백그라운드에서 정상 실행
- [ ] 브라우저에서 테스트 계정으로 로그인 성공
- [ ] forest_7_7로 이동 성공
- [ ] look 명령어 실행 후 몬스터 정보가 UI에 표시
- [ ] 브라우저 콘솔에서 GameModule.handleRoomInfo 호출 확인
- [ ] 서버 로그에서 몬스터 스폰 관련 로그 확인

## 주요 실수 분석 및 해결책

### 1. 캐시 문제 간과

#### 실수한 부분
- 서버 코드를 수정한 후 브라우저에서 즉시 테스트를 진행
- 브라우저가 캐시된 이전 버전의 JavaScript 파일을 사용하고 있다는 것을 간과
- 코드 변경사항이 반영되지 않았는데도 계속 클라이언트 측 문제로 판단

#### 올바른 접근법
```bash
# 서버 코드 수정 후 반드시 서버 재시작
ps aux | grep python
kill -9 <PID>
source mud_engine_env/Scripts/activate && PYTHONPATH=. python -m src.mud_engine.main &
```

- **서버 재시작**: 서버 측 코드 변경 시 반드시 서버 재시작
- **브라우저 새로고침**: 클라이언트 측 코드 변경 시 강제 새로고침 (Ctrl+F5)
- **캐시 확인**: 브라우저 개발자 도구에서 실제 로드된 파일 버전 확인

### 2. 디버깅 로그 누락 문제

#### 실수한 부분
- 코드에 디버깅 로그를 추가했지만 브라우저에서 해당 로그가 출력되지 않음
- 파일이 업데이트되지 않았다는 것을 인지하지 못하고 계속 다른 원인을 찾음

#### 올바른 접근법
```javascript
// 디버깅 로그 추가 후 반드시 확인
console.log('GameModule.handleRoomInfo 호출됨:', data);

// 브라우저에서 메서드 내용 직접 확인
window.mudClient.gameModule.handleRoomInfo.toString()
```

- **로그 확인**: 디버깅 로그 추가 후 브라우저 콘솔에서 실제 출력 여부 확인
- **메서드 검증**: 브라우저에서 실제 로드된 메서드 내용 직접 확인
- **버전 동기화**: 파일 수정과 브라우저 로드 버전의 일치 여부 검증

### 3. WebSocket 메시지 가로채기 실수

#### 실수한 부분
```javascript
// 잘못된 WebSocket 접근
window.client.websocket.onmessage  // client 객체가 undefined

// 잘못된 속성명 사용
window.mudClient.websocket  // websocket이 아니라 ws
```

#### 올바른 접근법
```javascript
// 올바른 WebSocket 접근
window.mudClient.ws.onmessage

// 객체 구조 먼저 확인
console.log('mudClient 객체 구조:', Object.keys(window.mudClient));
console.log('WebSocket 관련 속성들:',
    Object.keys(window.mudClient).filter(key =>
        key.toLowerCase().includes('ws') ||
        key.toLowerCase().includes('socket')
    )
);
```

- **객체 구조 확인**: 전역 객체의 실제 구조를 먼저 파악
- **속성명 검증**: 가정하지 말고 실제 속성명 확인
- **단계적 접근**: 한 번에 깊은 속성에 접근하지 말고 단계별로 확인

### 4. 문제 원인 잘못 추정

#### 실수한 부분
- 서버에서 몬스터 데이터를 전송하지 않는다고 가정
- 실제로는 클라이언트에서 `room_info` 메시지를 받고 있었지만 `GameModule.handleRoomInfo`가 호출되지 않는 문제였음
- 서버 측 문제로 잘못 판단하여 불필요한 디버깅 시간 소모

#### 올바른 접근법
```javascript
// 1단계: 메시지 수신 여부 확인
console.log('서버 메시지 수신:', data);

// 2단계: 메시지 타입별 처리 확인
if (data.type === 'room_info') {
    console.log('room_info 메시지 수신됨');
}

// 3단계: 핸들러 호출 여부 확인
console.log('handleSpecificMessageTypes 호출됨');

// 4단계: 개별 메서드 호출 여부 확인
console.log('GameModule.handleRoomInfo 호출됨');
```

- **단계별 디버깅**: 데이터 흐름을 단계별로 추적
- **가정 검증**: 추측하지 말고 각 단계에서 실제 동작 확인
- **전체 흐름 파악**: 서버 → 클라이언트 → 메시지 핸들러 → UI 업데이트 전체 흐름 이해

## 브라우저 MCP 테스트 체크리스트

### 테스트 시작 전
- [ ] 서버가 최신 코드로 실행 중인지 확인
- [ ] 브라우저 캐시 클리어 또는 강제 새로고침
- [ ] 개발자 도구 콘솔 열어두기

### 디버깅 진행 시
- [ ] 각 단계별로 로그 출력 확인
- [ ] 브라우저에서 실제 로드된 코드 버전 확인
- [ ] WebSocket 메시지 송수신 상태 확인
- [ ] 전역 객체 구조 파악 후 접근

### 문제 발생 시
- [ ] 서버 로그와 클라이언트 로그 동시 확인
- [ ] 캐시 문제 가능성 먼저 검토
- [ ] 데이터 흐름을 단계별로 추적
- [ ] 가정보다는 실제 확인에 의존

## 효율적인 디버깅 패턴

### 1. 캐시 문제 해결 우선순위
```bash
# 1. 서버 재시작
kill -9 <server_pid>
source mud_engine_env/Scripts/activate && PYTHONPATH=. python -m src.mud_engine.main &

# 2. 브라우저 강제 새로고침
# Ctrl+F5 또는 개발자 도구에서 "Disable cache" 체크
```

### 2. 단계별 검증 패턴
```javascript
// Step 1: 메시지 수신 확인
console.log('1. 메시지 수신:', data);

// Step 2: 타입 확인
console.log('2. 메시지 타입:', data.type);

// Step 3: 핸들러 진입 확인
console.log('3. 핸들러 진입');

// Step 4: 메서드 호출 확인
console.log('4. 메서드 호출');
```

### 3. 객체 구조 안전 접근 패턴
```javascript
// 안전한 접근 방법
if (window.mudClient) {
    console.log('mudClient 존재');
    if (window.mudClient.ws) {
        console.log('WebSocket 존재');
        // 이제 안전하게 접근 가능
    }
}
```

## 주의사항

### 절대 하지 말아야 할 것들
- 캐시 확인 없이 코드 변경사항이 반영되었다고 가정
- 객체 구조 확인 없이 깊은 속성에 바로 접근
- 한 번에 여러 가지 변경사항을 적용하고 테스트
- 서버와 클라이언트 로그를 따로 확인

### 반드시 해야 할 것들
- 코드 변경 후 서버 재시작 및 브라우저 새로고침
- 단계별 디버깅으로 문제 지점 정확히 파악
- 실제 데이터 흐름 추적으로 가정 검증
- 브라우저 개발자 도구 적극 활용

## 결론

브라우저 MCP 테스트에서 가장 중요한 것은 **캐시 문제 인식**과 **단계별 검증**입니다.
코드 변경 후 즉시 테스트하지 말고 반드시 캐시 클리어를 하고,
문제 발생 시 추측보다는 실제 확인을 통해 단계별로 원인을 파악해야 합니다.