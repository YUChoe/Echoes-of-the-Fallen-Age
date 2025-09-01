# 클라이언트 개발 베스트 프랙티스

## CSS와 JavaScript 상태 관리 원칙

### CSS 우선순위와 인라인 스타일 충돌 해결
```javascript
// ❌ 잘못된 방법 - 인라인 스타일 사용
element.style.display = 'none';

// ✅ 올바른 방법 - 인라인 스타일 제거 후 CSS 클래스로 제어
element.style.display = '';  // 인라인 스타일 제거
```

### CSS 클래스 기반 상태 관리 패턴
```css
/* CSS에서 상태별 규칙 정의 */
#commandBuilder {
    display: none !important;
}

.command-builder-active #commandBuilder {
    display: block !important;
}

.normal-mode-active #commandBuilder {
    display: none !important;
}
```

```javascript
// JavaScript에서는 body 클래스만 변경
document.body.className = 'command-builder-active';
```

### 올바른 초기화 패턴
```javascript
initializeGameUI() {
    // 1. 인라인 스타일 제거 (CSS 클래스가 제어하도록)
    const elements = ['commandBuilder', 'dynamicButtons', 'inputContainer'];
    elements.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.style.display = ''; // 인라인 스타일 제거
        }
    });

    // 2. 즉시 올바른 모드 활성화 (setTimeout 사용 안 함)
    if (this.isCommandBuilderMode) {
        this.activateCommandBuilderMode();
    } else {
        this.activateNormalMode();
    }
}
```

## 메시지 처리 및 통신 패턴

### 메시지 중복 출력 문제 해결
문제: 다양한 메시지 처리 경로가 중복될 때 발생

```javascript
// ❌ 복잡한 조건문 - 예측 불가능한 동작
if (data.response && !messageDisplayed) {
    if (!data.response.includes('명령을 받았습니다') &&
        !data.message &&
        !(data.data && (data.data.action === 'look' || data.data.action === 'inventory'))) {
        // 복잡한 조건으로 인한 혼란
    }
}

// ✅ 단순하고 명확한 처리
if (data.message) {
    this.client.gameModule.addGameMessage(data.message, 'info');
}
```

### 메시지 처리 통합 패턴
```javascript
class MessageHandler {
    handleMessage(data) {
        // 단순하고 명확한 분기
        if (data.error) return this.handleError(data);
        if (this.isAuthMessage(data)) return this.handleAuth(data);

        // 모든 게임 메시지는 동일한 경로로
        if (data.message) {
            this.displayMessage(data.message);
        }

        // 후처리는 별도 메서드로 분리
        this.handlePostProcessing(data);
    }

    displayMessage(message) {
        // 단일 메시지 출력 경로
        this.client.gameModule.addGameMessage(message, 'info');
    }
}
```

### CSS 클래스 통일 패턴
```css
/* 게임 메시지는 하나의 클래스 체계만 사용 */
.game-message { /* 기본 스타일 */ }
.game-message.info { color: #60a5fa; }
.game-message.success { color: #4ade80; }
.game-message.error { color: #f87171; }

/* ❌ 중복된 구현 방지
.message { ... }  다른 스타일
.game-message { ... }  또 다른 스타일
*/
```

### 방어적 데이터 접근 및 호환성 처리
```javascript
// ✅ 안전한 데이터 접근 패턴
const responseData = data.data || data;
const action = responseData.action || data.action;

// 방어적 접근으로 호환성 유지
const loginData = data.data || data;
const isAdmin = loginData.is_admin || false;

// 서버 응답 구조 변화 대응
function extractActionFromResponse(data) {
    // 새로운 형식: { status: "success", data: { action: "login_success" } }
    if (data.data && data.data.action) {
        return data.data.action;
    }

    // 이전 형식: { status: "success", action: "login_success" }
    if (data.action) {
        return data.action;
    }

    return null;
}

// 안전한 데이터 추출 유틸리티
function safeExtractData(response, path, defaultValue = null) {
    try {
        const keys = path.split('.');
        let value = response;

        for (const key of keys) {
            if (value && typeof value === 'object' && key in value) {
                value = value[key];
            } else {
                return defaultValue;
            }
        }

        return value;
    } catch (error) {
        console.warn(`데이터 추출 실패: ${path}`, error);
        return defaultValue;
    }
}

// 사용 예시
const playerName = safeExtractData(data, 'data.player.username', '알 수 없음');
```

### 메시지 처리 패턴
```javascript
// MessageHandler에서 서버 응답 처리
handleMessage(data) {
    console.log('서버 메시지 수신:', data);

    // 데이터 구조 확인 및 방어적 접근
    const messageType = data.type;
    const responseData = data.data || data;

    switch(messageType) {
        case 'room_info':
            this.client.gameModule.handleRoomInfo(responseData);
            break;
        case 'login_success':
            this.client.authModule.handleLoginSuccess(responseData);
            break;
        // ... 기타 케이스
    }
}
```

## 에러 처리 및 디버깅

### 클라이언트 디버깅 전략
```javascript
// 서버 응답 구조 확인
console.log('서버 메시지 수신:', data);

// 데이터 존재 여부 확인
if (data && data.data && data.data.action) {
    // 처리 로직
} else {
    console.warn('예상과 다른 데이터 구조:', data);
}

// 응답 타입별 로깅
console.log(`메시지 타입: ${data.type}, 데이터:`, data);
```

### 에러 상황 처리
```javascript
// 네트워크 에러 처리
this.websocket.onerror = function(error) {
    console.error('WebSocket 에러:', error);
    // 사용자에게 알림
    this.showErrorMessage('서버 연결에 문제가 발생했습니다.');
};

// 예상치 못한 메시지 형식 처리
if (!data.type) {
    console.warn('메시지 타입이 없는 응답:', data);
    return;
}
```

## UI 업데이트 패턴

### 동적 UI 갱신
```javascript
// 방 정보 업데이트
handleRoomInfo(roomData) {
    if (!roomData) return;

    // DOM 요소 안전하게 접근
    const roomNameElement = document.getElementById('room-name');
    if (roomNameElement) {
        roomNameElement.textContent = roomData.name || '알 수 없는 장소';
    }

    // 방 설명 업데이트
    this.updateRoomDescription(roomData.description);

    // 출구 정보 업데이트
    this.updateExits(roomData.exits);
}
```

### 상태 관리
```javascript
// 클라이언트 상태 관리
class GameState {
    constructor() {
        this.currentRoom = null;
        this.player = null;
        this.inventory = [];
    }

    updateRoom(roomData) {
        this.currentRoom = roomData;
        this.notifyUI('room_updated', roomData);
    }

    updatePlayer(playerData) {
        this.player = playerData;
        this.notifyUI('player_updated', playerData);
    }
}
```

## 모듈 구조 패턴

### 모듈 간 통신
```javascript
// 메시지 핸들러에서 적절한 모듈로 라우팅
case 'login_success':
    this.client.authModule.handleLoginSuccess(data);
    break;

case 'room_info':
    this.client.gameModule.handleRoomInfo(data);
    break;

case 'inventory_update':
    this.client.gameModule.handleInventoryUpdate(data);
    break;
```

### 모듈별 책임 분리
```javascript
// AuthModule - 인증 관련 처리
class AuthModule {
    handleLoginSuccess(data) {
        const loginData = data.data || data;
        this.updateLoginState(loginData);
        this.showGameInterface();
    }
}

// GameModule - 게임 플레이 관련 처리
class GameModule {
    handleRoomInfo(data) {
        this.updateRoomDisplay(data);
        this.updateMiniMap(data);
    }
}
```

## 데이터 형식 호환성

### 서버 응답 구조 변화 대응
```javascript
// 이전 형식과 새 형식 모두 지원
function extractActionFromResponse(data) {
    // 새로운 형식: { status: "success", data: { action: "login_success" } }
    if (data.data && data.data.action) {
        return data.data.action;
    }

    // 이전 형식: { status: "success", action: "login_success" }
    if (data.action) {
        return data.action;
    }

    return null;
}
```

### 타입 검사 및 기본값
```javascript
// 안전한 데이터 추출
function safeExtractData(response, path, defaultValue = null) {
    try {
        const keys = path.split('.');
        let value = response;

        for (const key of keys) {
            if (value && typeof value === 'object' && key in value) {
                value = value[key];
            } else {
                return defaultValue;
            }
        }

        return value;
    } catch (error) {
        console.warn(`데이터 추출 실패: ${path}`, error);
        return defaultValue;
    }
}

// 사용 예시
const playerName = safeExtractData(data, 'data.player.username', '알 수 없음');
```

## WebSocket 연결 및 사용자 경험 관리

### WebSocket 연결 상태 관리
```javascript
class WebSocketManager {
    constructor() {
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
    }

    connect() {
        this.websocket = new WebSocket(this.url);

        this.websocket.onopen = () => {
            console.log('서버에 연결되었습니다.');
            this.reconnectAttempts = 0;
        };

        this.websocket.onclose = () => {
            console.log('서버 연결이 끔어졌습니다.');
            this.attemptReconnect();
        };
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            setTimeout(() => {
                this.reconnectAttempts++;
                this.connect();
            }, this.reconnectDelay * this.reconnectAttempts);
        }
    }
}
```

### 로딩 상태 및 사용자 피드백 관리
```javascript
// 로딩 인디케이터 표시
function showLoading(message = '처리 중...') {
    const loadingElement = document.getElementById('loading');
    if (loadingElement) {
        loadingElement.textContent = message;
        loadingElement.style.display = 'block';
    }
}

function hideLoading() {
    const loadingElement = document.getElementById('loading');
    if (loadingElement) {
        loadingElement.style.display = 'none';
    }
}

// 성공/에러 메시지 표시
function showMessage(message, type = 'info') {
    const messageContainer = document.getElementById('message-container');
    if (!messageContainer) return;

    const messageElement = document.createElement('div');
    messageElement.className = `message message-${type}`;
    messageElement.textContent = message;

    messageContainer.appendChild(messageElement);

    // 자동으로 메시지 제거
    setTimeout(() => {
        messageElement.remove();
    }, 3000);
}
```

### 연결 상태 관리
```javascript
class WebSocketManager {
    constructor() {
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
    }

    connect() {
        this.websocket = new WebSocket(this.url);

        this.websocket.onopen = () => {
            console.log('서버에 연결되었습니다.');
            this.reconnectAttempts = 0;
        };

        this.websocket.onclose = () => {
            console.log('서버 연결이 끊어졌습니다.');
            this.attemptReconnect();
        };
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            setTimeout(() => {
                this.reconnectAttempts++;
                this.connect();
            }, this.reconnectDelay * this.reconnectAttempts);
        }
    }
}
```

## 사용자 경험 개선

### 로딩 상태 관리
```javascript
// 로딩 인디케이터 표시
function showLoading(message = '처리 중...') {
    const loadingElement = document.getElementById('loading');
    if (loadingElement) {
        loadingElement.textContent = message;
        loadingElement.style.display = 'block';
    }
}

function hideLoading() {
    const loadingElement = document.getElementById('loading');
    if (loadingElement) {
        loadingElement.style.display = 'none';
    }
}
```

### 사용자 피드백
```javascript
// 성공/에러 메시지 표시
function showMessage(message, type = 'info') {
    const messageContainer = document.getElementById('message-container');
    if (!messageContainer) return;

    const messageElement = document.createElement('div');
    messageElement.className = `message message-${type}`;
    messageElement.textContent = message;

    messageContainer.appendChild(messageElement);

    // 자동으로 메시지 제거
    setTimeout(() => {
        messageElement.remove();
    }, 3000);
}
```

## 클라이언트 체크리스트 및 품질 관리

### CSS 설계 체크리스트
- [ ] 모든 상태를 CSS 클래스로 정의
- [ ] 기본 상태와 활성 상태 명확히 구분
- [ ] !important 사용 시 주석으로 이유 명시
- [ ] 선택자 특이성 고려한 구조 설계

### JavaScript 구현 체크리스트
- [ ] 인라인 스타일 사용 최소화
- [ ] 상태 변경은 클래스 조작으로만
- [ ] 초기화 시 기존 인라인 스타일 제거
- [ ] 상태 변경 후 즉시 검증

### 메시지 처리 체크리스트
- [ ] 서버 응답 형식 확인 및 방어적 접근 구현
- [ ] 에러 상황 처리 로직 추가
- [ ] 사용자 피드백 메시지 구현
- [ ] 로딩 상태 관리 추가

### UI 업데이트 체크리스트
- [ ] DOM 요소 존재 여부 확인
- [ ] 기본값 설정으로 안전성 확보
- [ ] 사용자 경험 고려한 피드백 제공
- [ ] 반응형 디자인 고려

### MessageHandler 업데이트 체크리스트
- [ ] MessageHandler에 새로운 케이스 추가
- [ ] 해당 모듈에 핸들러 메서드 구현
- [ ] 데이터 구조 변화에 대한 호환성 확인
- [ ] 에러 처리 및 로깅 추가

## 피해야 할 패턴

### CSS 및 UI 관리
- 인라인 스타일과 CSS 클래스 혼용
- setTimeout을 통한 불필요한 지연
- 개별 요소의 직접적인 스타일 조작
- 상태 불일치 가능성이 있는 복잡한 로직

### 메시지 처리
- 개별 명령어마다 특별 처리 로직 추가
- 복잡한 플래그 변수로 상태 관리
- 여러 경로의 메시지 출력 시스템
- 임시방편적 조건문 추가

### 데이터 처리
- 데이터 구조 가정 없이 접근
- 에러 처리 누락
- 타입 검사 없이 데이터 사용
- 기본값 설정 없는 데이터 추출

## 권장 패턴

### UI 및 CSS 관리
- CSS 클래스 기반 상태 관리
- 선언적 스타일 정의
- 중앙집중식 상태 제어 (body 클래스)
- 명확한 초기화 순서

### 메시지 및 통신
- 전체 시스템 관점에서 문제 분석
- 단순한 책임 원칙에 따른 명확한 분리
- 일관된 메시지 처리 경로
- 예측 가능한 코드 구조

### 데이터 및 에러 처리
- 방어적 프로그래밍으로 안전성 확보
- 서버 응답 구조 변화에 대한 유연한 대응
- 명확한 에러 메시지와 사용자 피드백
- 자동 복구 또는 재시도 로직