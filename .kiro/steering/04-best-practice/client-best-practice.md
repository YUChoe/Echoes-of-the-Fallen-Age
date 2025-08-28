# 클라이언트 개발 베스트 프랙티스

## 서버-클라이언트 통신 처리

### 방어적 데이터 접근
```javascript
// ✅ 안전한 데이터 접근 패턴
const responseData = data.data || data;
const action = responseData.action || data.action;

// 방어적 접근으로 호환성 유지
const loginData = data.data || data;
const isAdmin = loginData.is_admin || false;
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

## WebSocket 연결 관리

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

## 클라이언트 체크리스트

### 새로운 기능 구현 시
- [ ] 서버 응답 형식 확인 및 방어적 접근 구현
- [ ] 에러 상황 처리 로직 추가
- [ ] 사용자 피드백 메시지 구현
- [ ] 로딩 상태 관리 추가

### 메시지 처리 추가 시
- [ ] MessageHandler에 새로운 케이스 추가
- [ ] 해당 모듈에 핸들러 메서드 구현
- [ ] 데이터 구조 변화에 대한 호환성 확인
- [ ] 에러 처리 및 로깅 추가

### UI 업데이트 시
- [ ] DOM 요소 존재 여부 확인
- [ ] 기본값 설정으로 안전성 확보
- [ ] 사용자 경험 고려한 피드백 제공
- [ ] 반응형 디자인 고려