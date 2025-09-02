# 선공형 몬스터 UI 표시 시스템 설계

## 개요

현재 선공형 몬스터 시스템은 서버에서 정상적으로 작동하고 브라우저 콘솔에서도 메시지가 확인되지만, 실제 게임 UI에는 표시되지 않는 문제가 있습니다. 이 문제를 해결하기 위해 메시지 라우팅과 UI 표시 로직을 개선합니다.

## 아키텍처

### 현재 문제 분석

1. **서버 → 클라이언트 통신**: 정상 작동 (monster_aggro 메시지 전송됨)
2. **브라우저 콘솔 로깅**: 정상 작동 (메시지 수신 확인됨)
3. **UI 표시**: 실패 (메시지가 화면에 표시되지 않음)

### 해결 방안 아키텍처

```
서버 (PlayerMovementManager)
    ↓ monster_aggro 메시지 전송
WebSocket 연결
    ↓ 메시지 수신
MessageHandler (클라이언트)
    ↓ 메시지 타입 확인
GameModule.handleMonsterAggro (새로 구현)
    ↓ UI 업데이트
게임 메시지 영역 표시
```

## 컴포넌트 및 인터페이스

### 1. MessageHandler 수정

**파일**: `static/js/modules/MessageHandler.js`

**수정 사항**:
- `handleSpecificMessageTypes` 메서드에 `monster_aggro` 케이스 추가
- GameModule의 handleMonsterAggro 메서드 호출 로직 추가

```javascript
case 'monster_aggro':
    if (this.client.gameModule && typeof this.client.gameModule.handleMonsterAggro === 'function') {
        this.client.gameModule.handleMonsterAggro(data);
    } else {
        // 대체 처리: 기본 메시지 표시
        this.client.gameModule.addGameMessage(data.message || '몬스터가 당신을 공격합니다!', 'warning');
    }
    break;
```

### 2. GameModule 확장

**파일**: `static/js/modules/GameModule.js`

**새로운 메서드**:
```javascript
handleMonsterAggro(data) {
    console.log('선공형 몬스터 공격:', data);

    // 공격 메시지 표시
    const message = data.message || `${data.monster_name || '몬스터'}가 당신을 공격합니다!`;
    this.addGameMessage(message, 'warning');

    // 전투 상태 UI 업데이트 (필요시)
    if (data.combat_started) {
        this.updateCombatStatus(data.combat_info);
    }
}
```

### 3. 메시지 스타일링

**파일**: `static/css/style.css`

**추가 스타일**:
```css
.game-message.warning {
    color: #f59e0b;
    font-weight: bold;
    background-color: rgba(245, 158, 11, 0.1);
    border-left: 3px solid #f59e0b;
    padding-left: 8px;
}

.monster-aggro-message {
    animation: pulse 0.5s ease-in-out;
}

@keyframes pulse {
    0% { opacity: 0.7; }
    50% { opacity: 1; }
    100% { opacity: 0.7; }
}
```

## 데이터 모델

### monster_aggro 메시지 구조

```javascript
{
    type: "monster_aggro",
    message: "야생 고블린이 당신을 공격합니다!",
    monster_id: "uuid-string",
    monster_name: "야생 고블린",
    combat_started: true,
    combat_info: {
        combat_id: "combat-uuid",
        participants: [...],
        current_turn: "player_id"
    },
    timestamp: "2025-01-02T22:35:00.000Z"
}
```

## 에러 처리

### 1. 메시지 핸들러 에러 처리

```javascript
try {
    this.client.gameModule.handleMonsterAggro(data);
} catch (error) {
    console.error('선공형 몬스터 메시지 처리 오류:', error);
    // 대체 처리
    this.client.gameModule.addGameMessage('몬스터가 당신을 공격합니다!', 'warning');
}
```

### 2. UI 업데이트 실패 처리

```javascript
handleMonsterAggro(data) {
    try {
        const message = data.message || '몬스터가 당신을 공격합니다!';
        this.addGameMessage(message, 'warning');
    } catch (error) {
        console.error('몬스터 공격 메시지 표시 실패:', error);
        // 최소한의 알림
        alert('몬스터가 공격했습니다!');
    }
}
```

### 3. 서버 메시지 검증

```javascript
if (!data || typeof data !== 'object') {
    console.warn('잘못된 monster_aggro 메시지 형식:', data);
    return;
}
```

## 테스트 전략

### 1. 단위 테스트

- MessageHandler의 monster_aggro 메시지 라우팅 테스트
- GameModule의 handleMonsterAggro 메서드 테스트
- UI 메시지 표시 기능 테스트

### 2. 통합 테스트

- 서버에서 클라이언트까지 전체 메시지 흐름 테스트
- 브라우저 콘솔과 UI 동기화 테스트
- 다양한 몬스터 타입에 대한 공격 메시지 테스트

### 3. 실시간 테스트 시나리오

1. **기본 시나리오**:
   - 서버 시작 → 브라우저 접속 → 로그인 → goto forest_7_7
   - 예상 결과: 야생 고블린 공격 메시지가 UI에 표시됨

2. **에러 시나리오**:
   - GameModule.handleMonsterAggro 메서드가 없는 상황
   - 예상 결과: 대체 메시지 표시 로직 작동

3. **성능 테스트**:
   - 연속적인 방 이동으로 다중 선공형 몬스터 공격
   - 예상 결과: 모든 공격 메시지가 순서대로 표시됨

## 구현 우선순위

### Phase 1: 핵심 기능 구현
1. MessageHandler에 monster_aggro 케이스 추가
2. GameModule에 handleMonsterAggro 메서드 구현
3. 기본 메시지 표시 기능 구현

### Phase 2: 향상된 기능
1. 메시지 스타일링 및 애니메이션 추가
2. 에러 처리 로직 강화
3. 전투 상태 UI 연동

### Phase 3: 테스트 및 최적화
1. 실시간 테스트 수행
2. 브라우저 호환성 확인
3. 성능 최적화

## 호환성 고려사항

### 브라우저 호환성
- 모든 주요 브라우저에서 동작하는 표준 JavaScript 사용
- ES6+ 기능 사용 시 폴리필 고려

### 기존 시스템과의 호환성
- 기존 메시지 처리 로직과 충돌하지 않도록 설계
- 다른 전투 관련 메시지와 일관된 형식 유지

### 확장성
- 향후 다른 몬스터 행동 패턴 추가 시 쉽게 확장 가능한 구조
- 메시지 타입별 핸들러 패턴 적용