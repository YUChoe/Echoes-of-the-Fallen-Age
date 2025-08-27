# MUD 게임 클라이언트 베스트 프랙티스

## MUD 게임 특화 원칙
- **실시간 게임 상태 동기화**: 플레이어, 방, 아이템 상태 실시간 반영
- **게임 메시지 프로토콜**: MUD 특화 메시지 타입 처리
- **게임 세션 관리**: 로그인/로그아웃, 재연결 처리
- **게임 UI 패턴**: 3단 레이아웃 (게임출력 | 사이드바 | 입력영역)

## MUD 게임 UI 구성

### 게임 인터페이스
- **플레이어 상태 패널**: 이름, 위치, 레벨, HP/MP 등
- **빠른 명령어 버튼**: look, inventory, who, quit 등
- **연결 상태 표시**: 실시간 서버 연결 상태

### 게임 메시지 시스템
- **타입별 색상 구분**: 시스템/플레이어/NPC/오류 메시지
- **타임스탬프**: 모든 게임 메시지에 시간 정보
- **자동 스크롤**: 새 메시지 자동 스크롤
- **게임 출력 폰트**: Courier New (모노스페이스)

### 게임 상호작용
- **키보드**: Enter로 명령어 전송
- **마우스**: 빠른 명령어 버튼 클릭
- **도움말**: 게임 명령어 가이드 모달

## 주요 실수 패턴

### 1. 메시지 프로토콜 불일치
```javascript
// ❌ 잘못된 방법 - 서버 응답 형식 미확인
if (data.type === 'login') {
    this.client.authModule.handleLoginSuccess(data);
}

// ✅ 올바른 방법 - 실제 서버 응답 형식에 맞춤
if (data.action === 'login_success') {
    this.client.authModule.handleLoginSuccess(data);
}
```

### 2. 상태 관리 로직 누락
```javascript
// ❌ 잘못된 방법 - 상태 구분 없음
logout() {
    this.sendCommand('quit');
}

// ✅ 올바른 방법 - 상태 플래그로 구분
logout() {
    this.isLoggingOut = true;
    this.sendCommand('quit');
}

this.ws.onclose = () => {
    if (this.isLoggingOut) {
        this.handleLogout();
    } else if (this.isAuthenticated) {
        this.handleUnexpectedDisconnection();
    }
};
```

### 3. 메시지 핸들러 누락
```javascript
// ❌ 누락된 핸들러 - 메시지가 무시됨
} else if (data.type === 'room_message') {
    // 핸들러 없음
}

// ✅ 완전한 핸들러 구현
} else if (data.type === 'room_message') {
    this.handleRoomMessage(data);
}

handleRoomMessage(data) {
    this.addGameMessage(data.message, 'info');
}
```

## 권장 개발 패턴

### 1. 상태 기반 이벤트 처리
```javascript
class MudClient {
    constructor() {
        this.isConnected = false;
        this.isAuthenticated = false;
        this.isLoggingOut = false;
        this.isReconnecting = false;
    }

    handleConnectionClose() {
        this.isConnected = false;

        if (this.isLoggingOut) {
            this.handleLogout();
        } else if (this.isAuthenticated && !this.isReconnecting) {
            this.handleUnexpectedDisconnection();
        }
    }
}
```

### 2. 방어적 메시지 처리
```javascript
handleMessage(data) {
    // 필수 필드 검증
    if (!data || typeof data !== 'object') {
        console.warn('Invalid message format:', data);
        return;
    }

    // 상태별 처리
    if (data.status === 'success') {
        this.handleSuccessMessage(data);
    } else if (data.error) {
        this.handleErrorMessage(data);
    } else {
        this.handleGenericMessage(data);
    }
}
```

### 3. 메시지 타입 동기화
```javascript
// 서버 메시지 타입에 맞춘 핸들러 구현
handleMessage(data) {
    switch(data.type) {
        case 'room_message':
            this.handleRoomMessage(data);
            break;
        case 'system_message':
            this.handleSystemMessage(data);
            break;
        case 'follow_stopped':
            this.handleFollowStopped(data);
            break;
        default:
            console.warn('Unknown message type:', data.type);
    }
}
```

### 4. 점진적 리팩토링
```javascript
// 1단계: 기존 기능 보존하면서 모듈 분리
// 2단계: 각 모듈별 개별 테스트
// 3단계: 전체 통합 테스트
// 4단계: 최적화 및 정리

// 리팩토링 중간 단계에서도 항상 작동하는 상태 유지
```

### 5. MUD 게임 세션 관리
```javascript
// ✅ MUD 게임 클라이언트 상태 관리
class MudGameClient {
    constructor() {
        this.isConnected = false;
        this.isAuthenticated = false;
        this.isLoggingOut = false;
        this.isReconnecting = false;
        this.currentRoom = null;
        this.playerStats = null;
    }

    handleGameMessage(data) {
        switch(data.type) {
            case 'room_description':
                this.updateRoomInfo(data);
                break;
            case 'player_stats':
                this.updatePlayerStats(data);
                break;
            case 'game_message':
                this.displayGameMessage(data);
                break;
            case 'system_message':
                this.displaySystemMessage(data);
                break;
        }
    }
}
```

### 6. MUD 게임 명령어 처리
```javascript
// ✅ 게임 명령어 자동완성 및 히스토리
class GameCommandHandler {
    constructor() {
        this.commandHistory = [];
        this.historyIndex = -1;
        this.commonCommands = ['look', 'inventory', 'who', 'say', 'tell'];
    }

    handleKeyPress(event) {
        if (event.key === 'Enter') {
            this.sendCommand(event.target.value);
            this.addToHistory(event.target.value);
            event.target.value = '';
        } else if (event.key === 'ArrowUp') {
            this.showPreviousCommand(event.target);
        } else if (event.key === 'ArrowDown') {
            this.showNextCommand(event.target);
        }
    }

    sendCommand(command) {
        if (command.trim()) {
            this.websocket.send(JSON.stringify({
                type: 'command',
                command: command.trim()
            }));
        }
    }
}
```

## MUD 게임 개발 체크리스트

### 게임 클라이언트 구현 전
- [ ] MUD 서버 메시지 프로토콜 분석
- [ ] 게임 상태 (플레이어, 방, 아이템) 데이터 구조 파악
- [ ] 게임 명령어 목록 및 응답 형식 확인
- [ ] 실시간 업데이트가 필요한 UI 요소 식별

### 게임 클라이언트 구현 중
- [ ] 게임 메시지 타입별 핸들러 구현
- [ ] 플레이어 상태 실시간 업데이트 로직
- [ ] 게임 명령어 입력 및 히스토리 기능
- [ ] 연결 끊김 시 재연결 로직

### 게임 클라이언트 테스트
- [ ] 로그인/로그아웃 플로우 테스트
- [ ] 게임 명령어 (look, inventory, move 등) 테스트
- [ ] 다중 플레이어 상호작용 테스트
- [ ] 네트워크 끊김 상황 테스트

## MUD 게임 디버깅 가이드

### 게임 상태 디버깅
```javascript
// 게임 상태 로깅
handleGameStateUpdate(data) {
    console.log('Game state update:', {
        type: data.type,
        player: this.playerStats,
        room: this.currentRoom,
        timestamp: new Date().toISOString()
    });
}
```

### 게임 메시지 디버깅
```javascript
// 게임 메시지 상세 로깅
handleGameMessage(data) {
    console.log('Game message received:', {
        type: data.type,
        content: data.message,
        sender: data.sender,
        room: data.room_id
    });
}
```

## MUD 게임 특화 주의사항
- **게임 세션 유지**: 브라우저 새로고침 시에도 게임 상태 복원
- **명령어 큐잉**: 네트워크 지연 시 명령어 순서 보장
- **실시간 동기화**: 다른 플레이어 행동 즉시 반영
- **게임 규칙 준수**: 서버 검증에 의존하되 클라이언트에서 기본 검증