# 설계 문서

## 개요

Python MUD 엔진은 aiohttp를 기반으로 한 비동기 웹 서버로, WebSocket을 통해 실시간 다중 사용자 텍스트 게임을 제공합니다. 전통적인 MUD의 텍스트 명령어 시스템과 현대적인 웹 UI를 결합한 하이브리드 인터페이스를 제공하며, SQLite를 사용한 데이터 지속성과 영어/한국어 다국어 지원을 포함합니다.

## 아키텍처

### 전체 시스템 구조

```mermaid
graph TB
    Client[웹 브라우저 클라이언트] --> WebServer[aiohttp 웹 서버]
    WebServer --> WSHandler[WebSocket 핸들러]
    WebServer --> HTTPHandler[HTTP 핸들러]

    WSHandler --> GameEngine[게임 엔진 코어]
    HTTPHandler --> GameEngine

    GameEngine --> PlayerManager[플레이어 매니저]
    GameEngine --> WorldManager[세계 매니저]
    GameEngine --> CommandProcessor[명령어 처리기]
    GameEngine --> I18nManager[다국어 매니저]

    PlayerManager --> Database[(SQLite 데이터베이스)]
    WorldManager --> Database
    I18nManager --> Database

    GameEngine --> EventSystem[이벤트 시스템]
    EventSystem --> WSHandler
```

### 레이어 구조

1. **프레젠테이션 레이어**: 웹 클라이언트 (HTML/CSS/JavaScript)
2. **네트워크 레이어**: aiohttp 서버 (HTTP/WebSocket)
3. **애플리케이션 레이어**: 게임 엔진 코어
4. **비즈니스 로직 레이어**: 게임 매니저들
5. **데이터 레이어**: SQLite 데이터베이스

## 구성 요소 및 인터페이스

### 1. 웹 서버 (aiohttp)

**역할**: HTTP 요청 및 WebSocket 연결 처리

**주요 컴포넌트**:

- `MudServer`: 메인 서버 클래스
- `WebSocketHandler`: WebSocket 연결 관리
- `StaticHandler`: 정적 파일 서빙 (HTML, CSS, JS)

**인터페이스**:

```python
class MudServer:
    async def start_server(self, host: str, port: int) -> None
    async def stop_server(self) -> None
    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse
    async def handle_static(self, request: web.Request) -> web.Response
```

### 2. 게임 엔진 코어

**역할**: 게임 로직의 중앙 조정자

**주요 컴포넌트**:

- `GameEngine`: 메인 게임 엔진
- `Session`: 플레이어 세션 관리
- `EventBus`: 이벤트 발행/구독 시스템

**인터페이스**:

```python
class GameEngine:
    async def process_command(self, session: Session, command: str) -> None
    async def broadcast_to_room(self, room_id: str, message: dict) -> None
    async def add_player_session(self, session: Session) -> None
    async def remove_player_session(self, session_id: str) -> None
```

### 3. 플레이어 매니저

**역할**: 플레이어 인증, 세션 관리, 캐릭터 데이터

**주요 컴포넌트**:

- `PlayerManager`: 플레이어 관리
- `AuthService`: 인증 서비스
- `Character`: 캐릭터 모델

**인터페이스**:

```python
class PlayerManager:
    async def authenticate(self, username: str, password: str) -> Optional[Player]
    async def create_account(self, username: str, password: str) -> Player
    async def get_player(self, player_id: str) -> Optional[Player]
    async def save_player(self, player: Player) -> None
```

### 4. 세계 매니저

**역할**: 게임 세계, 방, 객체 관리

**주요 컴포넌트**:

- `WorldManager`: 세계 관리
- `Room`: 방 모델
- `GameObject`: 게임 객체 모델

**인터페이스**:

```python
class WorldManager:
    async def get_room(self, room_id: str) -> Optional[Room]
    async def create_room(self, room_data: dict) -> Room
    async def update_room(self, room_id: str, updates: dict) -> None
    async def get_room_objects(self, room_id: str) -> List[GameObject]
```

### 5. 명령어 처리기

**역할**: 텍스트 명령어 파싱 및 실행

**주요 컴포넌트**:

- `CommandProcessor`: 명령어 처리
- `CommandRegistry`: 명령어 등록 관리
- `Command`: 개별 명령어 클래스들

**인터페이스**:

```python
class CommandProcessor:
    async def parse_command(self, input_text: str) -> Tuple[str, List[str]]
    async def execute_command(self, session: Session, command: str, args: List[str]) -> None
    def register_command(self, command_name: str, handler: Command) -> None
```

### 6. 다국어 매니저

**역할**: 영어/한국어 지원

**주요 컴포넌트**:

- `I18nManager`: 다국어 관리
- `LocaleService`: 로케일 서비스

**인터페이스**:

```python
class I18nManager:
    def get_text(self, key: str, locale: str, **kwargs) -> str
    async def load_translations(self) -> None
    def get_supported_locales(self) -> List[str]
```

## 데이터 모델

### 데이터베이스 스키마 (SQLite)

```sql
-- 플레이어 테이블
CREATE TABLE players (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT,
    preferred_locale TEXT DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- 캐릭터 테이블
CREATE TABLE characters (
    id TEXT PRIMARY KEY,
    player_id TEXT NOT NULL,
    name TEXT NOT NULL,
    current_room_id TEXT,
    inventory TEXT, -- JSON 형태로 저장
    stats TEXT, -- JSON 형태로 저장
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(id)
);

-- 방 테이블
CREATE TABLE rooms (
    id TEXT PRIMARY KEY,
    name_en TEXT NOT NULL,
    name_ko TEXT NOT NULL,
    description_en TEXT,
    description_ko TEXT,
    exits TEXT, -- JSON 형태로 저장 (방향: 목적지_방_ID)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 게임 객체 테이블
CREATE TABLE game_objects (
    id TEXT PRIMARY KEY,
    name_en TEXT NOT NULL,
    name_ko TEXT NOT NULL,
    description_en TEXT,
    description_ko TEXT,
    object_type TEXT NOT NULL, -- 'item', 'npc', 'furniture' 등
    location_type TEXT NOT NULL, -- 'room', 'inventory'
    location_id TEXT, -- room_id 또는 character_id
    properties TEXT, -- JSON 형태로 저장
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 다국어 텍스트 테이블
CREATE TABLE translations (
    key TEXT NOT NULL,
    locale TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (key, locale)
);
```

### 핵심 데이터 모델

```python
@dataclass
class Player:
    id: str
    username: str
    password_hash: str
    email: Optional[str]
    preferred_locale: str = 'en'
    created_at: datetime
    last_login: Optional[datetime] = None

@dataclass
class Character:
    id: str
    player_id: str
    name: str
    current_room_id: Optional[str]
    inventory: List[str]  # 객체 ID 목록
    stats: Dict[str, Any]
    created_at: datetime

@dataclass
class Room:
    id: str
    name: Dict[str, str]  # {'en': 'name', 'ko': '이름'}
    description: Dict[str, str]
    exits: Dict[str, str]  # {'north': 'room_id', 'south': 'room_id'}
    created_at: datetime
    updated_at: datetime

@dataclass
class GameObject:
    id: str
    name: Dict[str, str]
    description: Dict[str, str]
    object_type: str
    location_type: str
    location_id: Optional[str]
    properties: Dict[str, Any]
    created_at: datetime

@dataclass
class Session:
    id: str
    player_id: str
    character_id: str
    websocket: web.WebSocketResponse
    current_room_id: str
    locale: str
    connected_at: datetime
```

## 오류 처리

### 오류 계층 구조

```python
class MudEngineError(Exception):
    """기본 MUD 엔진 오류"""
    pass

class AuthenticationError(MudEngineError):
    """인증 관련 오류"""
    pass

class CommandError(MudEngineError):
    """명령어 처리 오류"""
    pass

class WorldError(MudEngineError):
    """게임 세계 관련 오류"""
    pass

class DatabaseError(MudEngineError):
    """데이터베이스 관련 오류"""
    pass
```

### 오류 처리 전략

1. **WebSocket 연결 오류**: 자동 재연결 시도, 세션 정리
2. **데이터베이스 오류**: 트랜잭션 롤백, 로깅, 사용자 알림
3. **명령어 오류**: 사용자에게 친화적인 오류 메시지 표시
4. **세계 데이터 오류**: 기본값으로 복구, 관리자 알림

## 테스트 전략

### 테스트 레벨

1. **단위 테스트**: 개별 컴포넌트 테스트

   - 명령어 처리기
   - 데이터 모델
   - 다국어 매니저

2. **통합 테스트**: 컴포넌트 간 상호작용 테스트

   - 데이터베이스 연동
   - WebSocket 통신
   - 게임 엔진 워크플로우

3. **시스템 테스트**: 전체 시스템 테스트
   - 다중 사용자 시나리오
   - 실시간 세계 편집
   - 성능 테스트

### 테스트 도구

- **pytest**: 단위 및 통합 테스트
- **pytest-asyncio**: 비동기 코드 테스트
- **aiohttp.test_utils**: WebSocket 테스트
- **sqlite3**: 인메모리 데이터베이스 테스트

### 테스트 데이터

```python
# 테스트용 샘플 데이터
TEST_ROOMS = {
    'room_001': {
        'name': {'en': 'Town Square', 'ko': '마을 광장'},
        'description': {
            'en': 'A bustling town square with a fountain in the center.',
            'ko': '중앙에 분수가 있는 번화한 마을 광장입니다.'
        },
        'exits': {'north': 'room_002', 'east': 'room_003'}
    }
}

TEST_PLAYERS = {
    'player_001': {
        'username': 'testuser',
        'password_hash': 'hashed_password',
        'preferred_locale': 'ko'
    }
}
```

## 성능 고려사항

### 확장성 설계

1. **비동기 처리**: asyncio를 통한 동시성
2. **연결 풀링**: SQLite 연결 관리
3. **메모리 관리**: WeakSet을 사용한 WebSocket 연결 추적
4. **캐싱**: 자주 접근하는 방 데이터 캐싱

### 성능 최적화

1. **데이터베이스 인덱싱**: 자주 조회되는 컬럼에 인덱스 생성
2. **배치 처리**: 여러 플레이어에게 동시 메시지 전송 최적화
3. **지연 로딩**: 필요시에만 데이터 로드
4. **압축**: WebSocket 메시지 압축 활용 (aiohttp 내장 기능 사용, 메시지 타입별 압축 레벨 조정)

### 모니터링

```python
# 성능 메트릭 수집
class PerformanceMonitor:
    def __init__(self):
        self.active_connections = 0
        self.commands_per_second = 0
        self.database_query_time = []

    async def log_command_execution(self, duration: float):
        # 명령어 실행 시간 로깅
        pass

    async def log_database_query(self, query: str, duration: float):
        # 데이터베이스 쿼리 성능 로깅
        pass
```

이 설계는 요구사항에서 정의한 모든 기능을 지원하면서도 확장 가능하고 유지보수가 용이한 구조를 제공합니다. aiohttp의 비동기 특성을 활용하여 다중 사용자 환경에서 효율적으로 동작하며, SQLite를 통한 안정적인 데이터 저장과 실시간 세계 편집 기능을 지원합

# 게임 세계관

오래 전, 대륙은 **“황금의 시대”**라 불릴 만큼 번영했으나, 신과 인간, 마법과 기계가 뒤섞이며 균형이 무너졌다.
결국 **“몰락(崩壞)”**이라 불리는 대격변이 일어나고 제국은 불타 무너졌다.

수 세기가 지난 지금, 세상은 잿빛 폐허와 괴물의 소굴로 변했으며, 사람들은 작은 도시 국가나 종파 단위로 흩어져 살아간다.
그러나 옛 시대의 유산(고대 마법, 금단의 무기, 잊힌 신전 등)이 여전히 곳곳에 잠들어 있어, 탐험가와 전사, 마법사, 이단자들이 그것을 찾아 다툰다.

플레이어는 바로 그 혼란 속에서 살아가는 **“몰락의 시대를 걷는 자”**다.

🔥 주요 갈등 구도

옛 제국의 잔해 – 몰락 전의 제국은 “황금의 탑”이라는 심장부에서 사라졌다. 그 탑에 무엇이 있었는지, 누가 몰락을 불러왔는지는 여전히 수수께끼.

새로운 질서의 모색 – 기사단, 이교 종파, 도적 연맹, 잿빛 마법사 길드 등은 각자의 방식으로 새로운 질서를 세우려 한다.

재앙의 재등장 – 몰락 당시 봉인되었던 “재앙(Oblivion Spawn)”들이 봉인을 뚫고 다시 나타나며, 대륙은 또다시 종말의 기운에 휩싸인다.

플레이어의 선택 – 플레이어는 단순한 생존자가 아니라, 과거의 메아리와 연결된 운명을 가진 자. 선택에 따라 대륙의 미래가 달라진다.

🏰 주요 세력 예시

잿빛 기사단 : 몰락 이후 남은 유일한 기사단. 정의를 내세우지만 잔혹한 질서도 강요.

황혼의 교단 : 옛 신의 부활을 꿈꾸는 광신 집단. 몰락의 비밀을 가장 많이 알고 있음.

황금 도적 연맹 : 무너진 도시의 보물을 약탈하며 살아가는 자들. 혼돈을 힘으로 여김.

침묵의 학자들 : 몰락 전 문헌을 수집하는 집단. 기술과 마법의 재건을 추구.

🎭 테마 & 분위기

세기말: 어둡고 황폐한 폐허, 종말론적 신앙, 끝없는 전쟁

중세 판타지: 검과 마법, 기사단, 왕좌를 둘러싼 음모, 고대의 전설

플레이어 경험: 선택에 따라 “새로운 제국의 창건자”, “혼돈의 사도”, “몰락한 신의 대리자” 등 다양한 길로 흘러갈 수 있음

🌒 세계관 확장 설정
🌍 배경

몰락의 대륙, 카르나스(Karnas)
황금 제국이 불타 무너진 뒤 수백 년. 폐허와 황량한 들판, 고대의 잔해가 산재한 땅.

탐험의 동기
각 플레이어는 잊혀진 유산(고대 무기, 잊힌 신의 지식, 불사의 비밀 등)을 찾기 위해 떠난다.

탐험의 방식
세계는 크게 도시(거점) → 황무지(위험지역) → 폐허/던전(탐험) 구조로 이어지며, 도시에서 정보를 수집하고 준비하여 던전에 도전하는 사이클.

🏰 주요 스타팅 지역

마을 광장 - 처음 세계로 진입 했을 때 마주하는 평화로운 곳.

잿빛 항구(Greyhaven Port) – 무너진 제국의 마지막 항구도시. 난민과 용병이 모여들어 기회의 땅으로 불림.

황혼의 요새(Fort Duskfall) – 기사단이 점거한 군사 거점. 규율과 질서를 앞세우며 탐험가들을 고용함.

몰락의 도서관(The Fallen Archive) – 무너진 수도에 남은 폐허 도서관. 지식 추구자와 미치광이 마법사들이 모여듦.


