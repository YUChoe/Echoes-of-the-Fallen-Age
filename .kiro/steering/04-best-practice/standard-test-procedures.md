# 표준 테스트 절차

## 몬스터 스폰 테스트 절차

### 개요
웹 기반 MUD 게임에서 몬스터 스폰 기능을 테스트하기 위한 표준화된 절차입니다.
이 절차는 실제 프로젝트에서 검증되었으며, 브라우저 캐시 문제 등 일반적인 함정을 방지합니다.

### 사전 준비사항
- Python 가상환경 활성화 가능
- 테스트 계정 (aa / aaaabbbb) 생성 완료
- Playwright MCP 도구 사용 가능
- 브라우저 개발자 도구 사용법 숙지

### 1단계: 서버 환경 준비

#### 1.1 기존 프로세스 정리
```bash
# 실행 중인 Python 프로세스 확인
ps aux | grep python

# 기존 서버 프로세스 종료 (PID 확인 후)
kill -9 <PID>
```

#### 1.2 서버 백그라운드 실행
```bash
# 가상환경 활성화 및 서버 시작
source mud_engine_env/Scripts/activate && PYTHONPATH=. python -m src.mud_engine.main &
```

**중요**: `&` 기호를 사용하여 백그라운드 실행해야 브라우저 테스트와 병행 가능

#### 1.3 서버 시작 확인
- 콘솔에서 "서버가 http://localhost:8080 에서 실행 중입니다." 메시지 확인
- 몬스터 스폰 포인트 설정 로그 확인 (forest_0_0 ~ forest_7_7)

### 2단계: 브라우저 클라이언트 접속

#### 2.1 브라우저 열기
```javascript
// Playwright MCP 사용
await page.goto('http://localhost:8080');
```

#### 2.2 페이지 로드 확인
- 페이지 제목: "Echoes of the Fallen Age"
- 로그인 폼 표시 확인
- 브라우저 콘솔에서 JavaScript 오류 없음 확인

### 3단계: 테스트 계정 로그인

#### 3.1 로그인 정보 입력
- **사용자명**: aa
- **비밀번호**: aaaabbbb

#### 3.2 로그인 성공 확인
- 게임 인터페이스 표시
- "aa님, 환영합니다!" 메시지 확인
- Town Square 방 정보 표시

### 4단계: 테스트 위치로 이동

#### 4.1 일반 모드 전환
```javascript
// 명령어 조합 모드에서 일반 모드로 전환
await page.click('button[name="일반 모드"]');
```

#### 4.2 forest_7_7로 이동
```javascript
// 명령어 입력 및 실행
await page.fill('input[name="commandInput"]', 'goto forest_7_7');
await page.click('button[name="전송"]');
```

#### 4.3 이동 성공 확인
- "✅ '숲 (7,7)' (ID: forest_7_7)로 이동했습니다." 메시지 확인
- 방 이름: "🏰 Forest (7,7)" 표시
- 방 설명: "A peaceful spot where old willow trees bend over a small pond. Frogs croak softly."

### 5단계: 몬스터 스폰 확인

#### 5.1 방 정보 새로고침
```javascript
// look 명령어 실행
await page.fill('input[name="commandInput"]', 'look');
await page.click('button[name="전송"]');
```

#### 5.2 몬스터 정보 UI 확인
**예상 결과**:
```
👹 이곳에 있는 몬스터들:
• Green Slime (레벨 1, HP: 50/50)
• Wild Goblin (레벨 1, HP: 80/80)
• Green Slime (레벨 1, HP: 50/50)
```

#### 5.3 브라우저 콘솔 로그 확인
**필수 확인 항목**:
- `WebSocket 메시지 수신: {type: room_info, room: Object}`
- `GameModule.handleRoomInfo 호출됨`
- `몬스터 정보: [Object, Object, Object]`
- `몬스터 개수: 3`

### 6단계: 오류 분석 및 디버깅

#### 6.1 문제 발생 시 체크리스트
- [ ] 서버가 정상 실행 중인가?
- [ ] 브라우저 캐시 문제는 없는가? (강제 새로고침 시도)
- [ ] WebSocket 연결이 정상인가?
- [ ] 서버 로그에서 오류 메시지 확인
- [ ] 브라우저 콘솔에서 JavaScript 오류 확인

#### 6.2 캐시 문제 해결
```bash
# 1. 서버 재시작
ps aux | grep python
kill -9 <PID>
source mud_engine_env/Scripts/activate && PYTHONPATH=. python -m src.mud_engine.main &

# 2. 브라우저 강제 새로고침 (Ctrl+F5)
# 3. 개발자 도구에서 "Disable cache" 옵션 활성화
```

#### 6.3 실시간 디버깅
```javascript
// WebSocket 메시지 가로채기
const originalOnMessage = window.mudClient.ws.onmessage;
window.mudClient.ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('WebSocket 메시지 수신:', data);
    if (data.type === 'room_info') {
        console.log('room_info 상세:', data.room);
        if (data.room.monsters) {
            console.log('몬스터 정보:', data.room.monsters);
        }
    }
    return originalOnMessage.call(this, event);
};

// 메서드 호출 추적
const originalHandleRoomInfo = window.mudClient.gameModule.handleRoomInfo;
window.mudClient.gameModule.handleRoomInfo = function(data) {
    console.log('🔥 GameModule.handleRoomInfo 호출됨!', data);
    return originalHandleRoomInfo.call(this, data);
};
```

### 7단계: 테스트 완료 및 정리

#### 7.1 성공 기준 확인
- [ ] 서버 백그라운드 실행 성공
- [ ] 브라우저 클라이언트 접속 성공
- [ ] 테스트 계정 로그인 성공
- [ ] forest_7_7 이동 성공
- [ ] 몬스터 정보 UI 표시 성공
- [ ] 브라우저 콘솔에서 정상 로그 확인
- [ ] 서버 로그에서 몬스터 스폰 확인

#### 7.2 브라우저 디버깅 코드 소스 반영
**중요**: 브라우저에서 임시로 추가한 디버깅 코드는 반드시 실제 소스 코드에 반영
- 과도한 로그는 제거하고 필요한 것만 유지
- 소스 코드 수정 후 다시 서버 재시작하여 검증

#### 7.3 테스트 결과 문서화
- 성공/실패 여부 기록
- 발견된 문제점 및 해결 방법 기록
- 개선사항 제안

## 주의사항

### 절대 하지 말 것
- 코드 수정 후 서버 재시작 없이 테스트
- 브라우저 캐시 확인 없이 문제 원인 추정
- 한 번에 여러 변경사항 적용 후 테스트
- 서버와 클라이언트 로그 분리 확인

### 반드시 할 것
- 각 단계별 성공 확인 후 다음 단계 진행
- 문제 발생 시 캐시 문제부터 확인
- 브라우저 개발자 도구 적극 활용
- 실시간 디버깅으로 정확한 원인 파악

## 트러블슈팅 가이드

### 몬스터가 표시되지 않는 경우
1. **서버 로그 확인**: 몬스터 스폰 로그가 있는가?
2. **WebSocket 메시지 확인**: room_info 메시지에 monsters 데이터가 있는가?
3. **메서드 호출 확인**: GameModule.handleRoomInfo가 호출되는가?
4. **캐시 문제 확인**: 브라우저에서 최신 코드가 로드되었는가?

### 브라우저 콘솔 오류 발생 시
1. **JavaScript 구문 오류**: 소스 코드 문법 확인
2. **객체 접근 오류**: 전역 객체 구조 확인
3. **WebSocket 연결 오류**: 서버 상태 및 포트 확인
4. **메서드 미정의 오류**: 모듈 로드 순서 확인

이 절차를 따르면 몬스터 스폰 기능을 안정적으로 테스트할 수 있으며, 유사한 기능 테스트에도 응용 가능합니다.