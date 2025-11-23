# 설계 문서

## 개요

Python MUD 엔진은 고전적인 telnet 기반 CLI 인터페이스를 제공하는 비동기 텍스트 게임 서버입니다. 전통적인 MUD의 순수한 텍스트 명령어 시스템을 따르며, SQLite 데이터 지속성과 영어/한국어 다국어 지원을 포함합니다.

**클라이언트 지원:**
- **주 클라이언트**: Telnet CLI (고전적인 shell 인터페이스)
- **레거시 클라이언트**: 웹 브라우저 (개발 중단, 현재 상태 유지)

## 아키텍처

### 레이어 구조

1. **프레젠테이션**: Telnet CLI 클라이언트 (주) / 웹 클라이언트 (레거시)
2. **네트워크**: Telnet 서버 (주) / aiohttp 서버 (레거시)
3. **애플리케이션**: 게임 엔진 코어
4. **비즈니스 로직**: 게임 매니저들
5. **데이터**: SQLite 데이터베이스

## 핵심 컴포넌트

### 1. Telnet 서버 (주 개발 대상)
- `TelnetServer`: 메인 Telnet 서버
- `TelnetHandler`: Telnet 연결 관리
- `TelnetSession`: Telnet 세션 관리

### 1-1. 웹 서버 (레거시, 개발 중단)
- `MudServer`: 메인 웹 서버
- `WebSocketHandler`: WebSocket 연결 관리
- `StaticHandler`: 정적 파일 서빙

### 2. 게임 엔진 코어
- `GameEngine`: 게임 로직 중앙 조정자
- `Session`: 플레이어 세션 관리
- `EventBus`: 이벤트 발행/구독

### 3. 플레이어 매니저
- `PlayerManager`: 플레이어 관리
- `AuthService`: 인증 서비스
- `Character`: 캐릭터 모델

### 4. 세계 매니저
- `WorldManager`: 게임 세계, 방, 객체 관리
- `Room`: 방 모델
- `GameObject`: 게임 객체 모델

### 5. 명령어 처리기
- `CommandProcessor`: 명령어 파싱 및 실행
- `CommandRegistry`: 명령어 등록 관리
- `Command`: 개별 명령어 클래스들

### 6. 다국어 매니저
- `I18nManager`: 영어/한국어 지원
- `LocaleService`: 로케일 서비스

## 데이터베이스 스키마 (SQLite)

```sql
-- 플레이어
CREATE TABLE players (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    preferred_locale TEXT DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 방
CREATE TABLE rooms (
    id TEXT PRIMARY KEY,
    name_en TEXT NOT NULL,
    name_ko TEXT NOT NULL,
    description_en TEXT,
    description_ko TEXT,
    exits TEXT, -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 게임 객체
CREATE TABLE game_objects (
    id TEXT PRIMARY KEY,
    name_en TEXT NOT NULL,
    name_ko TEXT NOT NULL,
    description_en TEXT,
    description_ko TEXT,
    object_type TEXT NOT NULL,
    location_type TEXT NOT NULL,
    location_id TEXT,
    properties TEXT, -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 몬스터
CREATE TABLE monsters (
    id TEXT PRIMARY KEY,
    name_en TEXT NOT NULL,
    name_ko TEXT NOT NULL,
    level INTEGER DEFAULT 1,
    max_hp INTEGER DEFAULT 20,
    current_hp INTEGER DEFAULT 20,
    properties TEXT DEFAULT '{}',
    drop_items TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 게임 세계관

### 배경: 몰락의 대륙, 카르나스(Karnas)

황금 제국이 무너진 뒤 수백 년. 폐허와 괴물의 소굴로 변한 세상에서 사람들은 작은 도시 국가로 흩어져 살아간다. 옛 시대의 유산(고대 마법, 금단의 무기, 잊힌 신전)이 곳곳에 잠들어 있어, 탐험가들이 그것을 찾아 다툰다.

### 주요 세력

- **잿빛 기사단**: 정의를 내세우지만 잔혹한 질서 강요
- **황혼의 교단**: 옛 신의 부활을 꿈꾸는 광신 집단
- **황금 도적 연맹**: 무너진 도시의 보물 약탈
- **침묵의 학자들**: 몰락 전 문헌 수집, 기술과 마법 재건

### 주요 지역

- **마을 광장**: 평화로운 시작 지점
- **잿빛 항구**: 난민과 용병이 모이는 기회의 땅
- **황혼의 요새**: 기사단 군사 거점
- **몰락의 도서관**: 폐허 도서관, 지식 추구자들의 집결지
- **숲 지역 (8x8)**: 몬스터가 서식하는 탐험 지역

## 성능 고려사항

- **비동기 처리**: asyncio 동시성
- **연결 풀링**: SQLite 연결 관리
- **메모리 관리**: WeakSet 사용
- **캐싱**: 자주 접근하는 방 데이터 캐싱
