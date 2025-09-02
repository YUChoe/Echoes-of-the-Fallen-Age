# 실시간 전투 UI 표시 시스템 설계

## 개요

현재 자동 전투 시스템은 서버에서 정상적으로 작동하지만, 전투 진행 상황이 클라이언트에 실시간으로 표시되지 않는 문제가 있습니다. 이 설계는 서버-클라이언트 간 전투 메시지 전송 및 UI 업데이트 시스템을 개선하여 플레이어가 전투 상황을 실시간으로 확인할 수 있도록 합니다.

## 아키텍처

### 현재 시스템 분석

**서버 측 (정상 작동):**
- `AutoCombat` 클래스: 자동 전투 루프 및 턴 처리
- `CombatSystem` 클래스: 전투 관리 및 브로드캐스트 콜백
- 전투 명령어: `AttackCommand`, `DefendCommand`, `FleeCommand`, `CombatStatusCommand`
- 브로드캐스트 메커니즘: `broadcast_callback` 함수를 통한 메시지 전송

**클라이언트 측 (문제 지점):**
- `MessageHandler`: 서버 메시지 수신 및 라우팅
- `GameModule`: 게임 메시지 표시 및 UI 업데이트
- 전투 관련 메시지 타입 처리 누락

### 개선된 아키텍처

```
[서버] AutoCombat → broadcast_callback → GameEngine.broadcast_to_room
                                              ↓
[WebSocket] {"type": "combat_message", "message": "...", "combat_status": {...}}
                                              ↓
[클라이언트] MessageHandler → handleSpecificMessageTypes → GameModule.handleCombatMessage
                                              ↓
[UI] 실시간 전투 메시지 표시 + 전투 상태 UI 업데이트
```

## 컴포넌트 및 인터페이스

### 1. 서버 측 메시지 타입 정의

```python
class CombatMessageType(Enum):
    COMBAT_START = "combat_start"
    COMBAT_MESSAGE = "combat_message"
    COMBAT_STATUS = "combat_status"
    COMBAT_END = "combat_end"
    TURN_START = "turn_start"
    ACTION_RESULT = "action_result"
```

### 2. 서버 측 브로드캐스트 개선

**현재 구현:**
```python
async def broadcast_callback(room_id: str, message: str):
    await game_engine.broadcast_to_room(
        room_id,
        {"type": "combat_message", "message": message},
        exclude_session=session.session_id
    )
```

**개선된 구현:**
```python
async def enhanced_broadcast_callback(room_id: str, message: str,
                                    message_type: str = "combat_message",
                                    combat_status: Dict = None):
    broadcast_data = {
        "type": message_type,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }

    if combat_status:
        broadcast_data["combat_status"] = combat_status

    await game_engine.broadcast_to_room(room_id, broadcast_data)
```

### 3. 클라이언트 측 메시지 처리 확장

**MessageHandler 확장:**
```javascript
handleSpecificMessageTypes(data) {
    switch (data.type) {
        // 기존 케이스들...
        case 'combat_start':
            this.client.gameModule.handleCombatStart(data);
            break;
        case 'combat_message':
            this.client.gameModule.handleCombatMessage(data);
            break;
        case 'combat_status':
            this.client.gameModule.handleCombatStatus(data);
            break;
        case 'combat_end':
            this.client.gameModule.handleCombatEnd(data);
            break;
        case 'turn_start':
            this.client.gameModule.handleTurnStart(data);
            break;
        case 'action_result':
            this.client.gameModule.handleActionResult(data);
            break;
    }
}
```

### 4. GameModule 전투 처리 메서드 추가

```javascript
class GameModule {
    // 전투 시작 처리
    handleCombatStart(data) {
        this.addGameMessage(data.message, 'combat-start');
        this.showCombatUI(data.combat_status);
    }

    // 전투 메시지 처리
    handleCombatMessage(data) {
        this.addGameMessage(data.message, 'combat');
        if (data.combat_status) {
            this.updateCombatStatus(data.combat_status);
        }
    }

    // 전투 상태 업데이트
    handleCombatStatus(data) {
        this.updateCombatStatus(data.combat_status);
    }

    // 전투 종료 처리
    handleCombatEnd(data) {
        this.addGameMessage(data.message, 'combat-end');
        this.hideCombatUI();
    }

    // 턴 시작 처리
    handleTurnStart(data) {
        this.addGameMessage(data.message, 'turn-start');
        this.highlightCurrentTurn(data.current_player);
        if (data.is_player_turn) {
            this.showActionButtons();
        }
    }

    // 액션 결과 처리
    handleActionResult(data) {
        this.addGameMessage(data.message, 'action-result');
        this.updateCombatStatus(data.combat_status);
    }
}
```

## 데이터 모델

### 전투 상태 메시지 구조

```json
{
    "type": "combat_status",
    "combat_status": {
        "room_id": "forest_7_7",
        "state": "waiting_for_action",
        "turn_number": 3,
        "current_turn": "플레이어명",
        "turn_timeout": 2.0,
        "player": {
            "name": "플레이어명",
            "hp": 85,
            "max_hp": 100,
            "hp_percentage": 85.0,
            "initiative": 15
        },
        "monster": {
            "name": "Green Slime",
            "hp": 30,
            "max_hp": 50,
            "hp_percentage": 60.0,
            "initiative": 12
        },
        "last_turn": "플레이어가 몬스터에게 15 데미지를 입혔습니다.",
        "is_ongoing": true
    }
}
```

### 전투 메시지 구조

```json
{
    "type": "combat_message",
    "message": "⚔️ 플레이어가 Green Slime에게 15 데미지를 입혔습니다.",
    "timestamp": "2024-12-25T14:30:45.123Z",
    "combat_status": {
        // 위와 동일한 구조
    }
}
```

## 에러 처리

### 서버 측 에러 처리

```python
class CombatBroadcastError(Exception):
    """전투 브로드캐스트 오류"""
    pass

async def safe_broadcast_callback(room_id: str, message: str, **kwargs):
    try:
        await enhanced_broadcast_callback(room_id, message, **kwargs)
    except Exception as e:
        logger.error(f"전투 브로드캐스트 실패: {e}")
        # 대체 메시지 전송 또는 로컬 로깅
```

### 클라이언트 측 에러 처리

```javascript
handleCombatMessage(data) {
    try {
        this.addGameMessage(data.message, 'combat');
        if (data.combat_status) {
            this.updateCombatStatus(data.combat_status);
        }
    } catch (error) {
        console.error('전투 메시지 처리 오류:', error);
        this.addGameMessage('전투 정보 표시 중 오류가 발생했습니다.', 'error');
    }
}
```

## 테스트 전략

### 1. 서버 측 테스트

**브로드캐스트 콜백 테스트:**
```python
async def test_combat_broadcast():
    # 전투 시작
    combat = await combat_system.start_combat(player, monster, room_id, broadcast_callback)

    # 메시지 전송 확인
    assert len(sent_messages) > 0
    assert sent_messages[0]["type"] == "combat_start"

    # 턴 처리 후 메시지 확인
    combat.set_player_action(CombatAction.ATTACK)
    await asyncio.sleep(3)  # 턴 처리 대기

    assert any(msg["type"] == "combat_message" for msg in sent_messages)
```

### 2. 클라이언트 측 테스트

**메시지 처리 테스트:**
```javascript
// 전투 메시지 수신 시뮬레이션
const testCombatMessage = {
    type: 'combat_message',
    message: '⚔️ 테스트 공격!',
    combat_status: {
        player: { hp: 90, max_hp: 100 },
        monster: { hp: 40, max_hp: 50 }
    }
};

messageHandler.handleMessage(testCombatMessage);

// UI 업데이트 확인
assert(document.querySelector('.combat-ui').style.display !== 'none');
assert(document.querySelector('.player-hp').textContent.includes('90/100'));
```

### 3. 통합 테스트

**실시간 전투 플로우 테스트:**
1. 브라우저에서 `attack slime` 명령어 입력
2. 서버에서 전투 시작 메시지 브로드캐스트 확인
3. 클라이언트에서 전투 UI 표시 확인
4. 자동 턴 진행 중 실시간 메시지 수신 확인
5. 전투 종료 시 UI 정리 확인

## UI/UX 개선사항

### 1. 전투 전용 CSS 스타일

```css
.game-message.combat-start {
    background: linear-gradient(90deg, #ff6b6b, #ffa500);
    color: white;
    font-weight: bold;
    border-left: 4px solid #ff4757;
}

.game-message.combat {
    background: #fff3cd;
    border-left: 4px solid #ffc107;
    color: #856404;
}

.game-message.combat-end {
    background: linear-gradient(90deg, #4ecdc4, #44bd87);
    color: white;
    font-weight: bold;
    border-left: 4px solid #2ed573;
}

.combat-ui {
    position: fixed;
    top: 20px;
    right: 20px;
    background: rgba(0, 0, 0, 0.8);
    color: white;
    padding: 15px;
    border-radius: 8px;
    min-width: 250px;
}

.hp-bar {
    width: 100%;
    height: 20px;
    background: #333;
    border-radius: 10px;
    overflow: hidden;
    margin: 5px 0;
}

.hp-fill {
    height: 100%;
    background: linear-gradient(90deg, #ff4757, #ffa502);
    transition: width 0.3s ease;
}

.turn-indicator {
    text-align: center;
    font-weight: bold;
    color: #ffd700;
    margin: 10px 0;
}
```

### 2. 전투 액션 버튼

```html
<div id="combatActions" class="combat-actions" style="display: none;">
    <button class="combat-btn attack" data-cmd="attack">⚔️ 공격</button>
    <button class="combat-btn defend" data-cmd="defend">🛡️ 방어</button>
    <button class="combat-btn flee" data-cmd="flee">💨 도망</button>
</div>
```

### 3. 실시간 HP 바 애니메이션

```javascript
updateHPBar(elementId, currentHP, maxHP) {
    const hpBar = document.querySelector(`#${elementId} .hp-fill`);
    const percentage = (currentHP / maxHP) * 100;

    hpBar.style.width = `${percentage}%`;

    // HP가 낮을 때 색상 변경
    if (percentage < 30) {
        hpBar.style.background = 'linear-gradient(90deg, #ff4757, #ff3742)';
    } else if (percentage < 60) {
        hpBar.style.background = 'linear-gradient(90deg, #ffa502, #ff6348)';
    } else {
        hpBar.style.background = 'linear-gradient(90deg, #2ed573, #7bed9f)';
    }
}
```

## 성능 고려사항

### 1. 메시지 빈도 제한

```python
class CombatBroadcastThrottler:
    def __init__(self, min_interval: float = 0.1):
        self.min_interval = min_interval
        self.last_broadcast = 0

    async def throttled_broadcast(self, callback, *args, **kwargs):
        now = time.time()
        if now - self.last_broadcast >= self.min_interval:
            await callback(*args, **kwargs)
            self.last_broadcast = now
```

### 2. 클라이언트 메시지 큐

```javascript
class CombatMessageQueue {
    constructor() {
        this.queue = [];
        this.processing = false;
    }

    async addMessage(message) {
        this.queue.push(message);
        if (!this.processing) {
            await this.processQueue();
        }
    }

    async processQueue() {
        this.processing = true;
        while (this.queue.length > 0) {
            const message = this.queue.shift();
            await this.displayMessage(message);
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        this.processing = false;
    }
}
```

## 보안 고려사항

### 1. 메시지 검증

```python
def validate_combat_message(message: str) -> bool:
    # XSS 방지를 위한 메시지 검증
    if len(message) > 1000:
        return False

    # 허용되지 않은 HTML 태그 확인
    forbidden_tags = ['<script>', '<iframe>', '<object>']
    return not any(tag in message.lower() for tag in forbidden_tags)
```

### 2. 클라이언트 입력 검증

```javascript
sanitizeMessage(message) {
    // HTML 이스케이프
    const div = document.createElement('div');
    div.textContent = message;
    return div.innerHTML;
}
```

이 설계는 현재 작동하는 자동 전투 시스템에 최소한의 변경으로 실시간 UI 표시 기능을 추가하는 것을 목표로 합니다. 서버 측 브로드캐스트 메커니즘은 이미 구현되어 있으므로, 주로 클라이언트 측 메시지 처리 및 UI 업데이트에 집중합니다.