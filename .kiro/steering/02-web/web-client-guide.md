# Web Client 개발 가이드 (공통)

## 기본 원칙
- **Pico.css 2.0** 프레임워크 사용
- **반응형 디자인**: 모바일/태블릿/데스크톱 지원
- **네이밍 규칙**: HTML은 snake_case, JS는 camelCase
- **모듈화**: 클래스 기반 JavaScript 구조
- **이벤트 기반 아키텍처**: 컴포넌트 간 결합도 최소화

## 기술 스택
- **CSS**: Pico.css + CSS Grid/Flexbox
- **JavaScript**: Vanilla JS (의존성 없음)
- **통신**: WebSocket API
- **저장소**: LocalStorage (설정 저장)

## UI 구성 요소

### 레이아웃 패턴
- **카드 기반**: 섹션별 정보 그룹화
- **그리드 시스템**: 유연한 반응형 레이아웃
- **모듈화**: 독립적인 컴포넌트 구조

### 색상 시스템
- **테마**: 다크/라이트 모드 지원
- **의미론적 색상**: 성공(녹색), 오류(빨간색), 정보(파란색), 경고(노란색)

### 타이포그래피
- **UI 요소**: Pico.css 기본 폰트
- **계층적 텍스트**: 헤딩, 본문, 캡션 구분

## 핵심 기능

### 인증 시스템
- 분리된 로그인/회원가입 폼
- 실시간 입력 검증
- 로딩 상태 및 오류 처리

### 상태 관리
- 명확한 상태 플래그로 애플리케이션 상태 추적
- 방어적 메시지 처리 및 검증

### 다국어 지원
```javascript
const MESSAGES = {
    ko: { connecting: '연결 중...', error: '오류 발생' },
    en: { connecting: 'Connecting...', error: 'Error occurred' }
};

function getMessage(key, lang = 'ko') {
    return MESSAGES[lang]?.[key] || MESSAGES.ko[key] || key;
}
```

## 이벤트 기반 아키텍처
```javascript
class EventManager {
    constructor() {
        this.listeners = new Map();
    }

    on(eventType, callback) {
        if (!this.listeners.has(eventType)) {
            this.listeners.set(eventType, []);
        }
        this.listeners.get(eventType).push(callback);
    }

    emit(eventType, data) {
        const callbacks = this.listeners.get(eventType) || [];
        callbacks.forEach(callback => {
            try {
                callback(data);
            } catch (error) {
                console.error(`Event handler error for ${eventType}:`, error);
            }
        });
    }
}
```

## 반응형 브레이크포인트
- **데스크톱** (1200px+): 최대 레이아웃
- **태블릿** (768px-1199px): 중간 레이아웃
- **모바일** (767px 이하): 최소 레이아웃

## 개발 원칙
- 견고한 예외 처리와 사용자 피드백 제공
- 접근성 고려 (키보드 네비게이션, 스크린 리더 지원)
- 프로토콜 동기화: 서버-클라이언트 메시지 형식 일치
- 즉시 테스트: 각 단계마다 실제 동작 확인
- 테스트 결과는 서버로그를 통해 알 수 없으므로 사용자의 피드백을 통해 완료 여부를 확인 할 것