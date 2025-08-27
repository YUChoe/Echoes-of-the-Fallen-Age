# 클라이언트 개발 베스트 프랙티스

## 핵심 원칙
- **프로토콜 동기화**: 서버-클라이언트 메시지 형식 일치
- **상태 관리**: 명확한 상태 플래그로 애플리케이션 상태 추적
- **방어적 처리**: 메시지 형식 검증 후 처리
- **즉시 테스트**: 각 단계마다 실제 동작 확인

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

## 체크리스트

### 리팩토링 전
- [ ] 기존 코드의 전체 플로우 문서화
- [ ] 서버-클라이언트 메시지 프로토콜 분석
- [ ] 핵심 기능별 테스트 시나리오 작성
- [ ] 상태 관리 로직 파악

### 리팩토링 중
- [ ] 모듈 간 의존성 명확히 정의
- [ ] 메시지 핸들링 로직 일관성 유지
- [ ] 상태 변화 시점과 조건 명확히 구분
- [ ] 각 모듈별 책임 범위 명확히 분리

### 리팩토링 후
- [ ] 전체 사용자 시나리오 End-to-End 테스트
- [ ] 서버 로그와 클라이언트 동작 동시 확인
- [ ] 예외 상황 처리 로직 검증
- [ ] 성능 및 메모리 사용량 확인

## 디버깅 가이드

### 문제 발생 시 확인 순서
1. **브라우저 개발자 도구**: Network 탭에서 실제 메시지 확인
2. **서버 로그**: 서버에서 보내는 메시지 형식 확인
3. **클라이언트 로그**: 메시지 수신 및 처리 과정 추적
4. **상태 변화**: 애플리케이션 상태 변화 시점 분석

### 효과적인 디버깅
```javascript
// 메시지 처리 전후 로깅
handleMessage(data) {
    console.log('Received message:', data);

    // 처리 로직

    console.log('Message processed, current state:', {
        isConnected: this.isConnected,
        isAuthenticated: this.isAuthenticated,
        currentScreen: this.currentScreen
    });
}
```

## 핵심 교훈
- **확인 우선**: 가정하지 말고 실제 동작 확인
- **점진적 접근**: 한 번에 모든 것을 바꾸지 말고 단계적 진행
- **상태 추적**: 애플리케이션 상태 변화를 명확히 관리
- **프로토콜 준수**: 서버-클라이언트 간 메시지 형식 일관성 유지