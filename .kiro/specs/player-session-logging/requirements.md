# 요구사항 문서: 플레이어별 세션 로그

## 소개

기존 MUD 엔진의 통합 로그 시스템을 유지하면서, 인증된 각 플레이어의 세션 활동을 개별 로그 파일로 분리 저장하는 기능이다. 플레이어별 로그 파일은 `logs/players/{player_id}.log` 경로에 생성되며, 해당 플레이어의 세션 생명주기(인증~종료) 동안 발생하는 명령어 입력, 시스템 메시지, 에러 등을 기록한다. 기존 통합 로그(`logs/mud_engine-*.log`)는 변경 없이 그대로 유지된다.

## 용어 정의

- **Session_Logger**: 플레이어별 세션 로그 파일에 기록을 담당하는 로깅 컴포넌트
- **Player_Log_File**: `logs/players/{player_id}.log` 경로에 생성되는 플레이어 개별 로그 파일
- **TelnetSession**: Telnet 클라이언트 세션을 관리하는 기존 클래스 (`telnet_session.py`)
- **TelnetServer**: asyncio 기반 Telnet MUD 서버 클래스 (`telnet_server.py`)
- **Global_Logger**: 기존 `logs/mud_engine-*.log`에 기록하는 통합 로깅 시스템
- **Session_Lifecycle**: 플레이어 인증 시점부터 세션 종료 시점까지의 전체 기간
- **MudEngineFormatter**: 기존 로그 포맷터 (`{시분초.ms} {LEVEL} [{module:line}] {message}`)

## 요구사항

### 요구사항 1: 플레이어별 로그 파일 생성

**사용자 스토리:** 서버 운영자로서, 각 플레이어의 활동을 개별 파일로 확인하고 싶다. 이를 통해 특정 플레이어의 행동을 추적하고 문제를 진단할 수 있다.

#### 수용 기준

1. WHEN 플레이어가 인증에 성공하면, THE Session_Logger SHALL `logs/players/` 디렉토리 아래에 `{player_id}.log` 파일을 생성하거나 기존 파일에 추가(append) 모드로 열어야 한다.
2. THE Session_Logger SHALL 로그 파일 인코딩으로 UTF-8을 사용해야 한다.
3. IF `logs/players/` 디렉토리가 존재하지 않으면, THEN THE Session_Logger SHALL 해당 디렉토리를 자동으로 생성해야 한다.
4. THE Player_Log_File SHALL MudEngineFormatter와 동일한 포맷(`{시분초.ms} {LEVEL} [{module:line}] {message}`)을 사용해야 한다.

### 요구사항 2: 세션 생명주기 로깅

**사용자 스토리:** 서버 운영자로서, 플레이어의 접속과 종료 시점을 개별 로그에서 확인하고 싶다. 이를 통해 세션 지속 시간과 접속 패턴을 파악할 수 있다.

#### 수용 기준

1. WHEN 플레이어가 인증에 성공하면, THE Session_Logger SHALL 세션 시작 로그를 기록해야 한다. 로그에는 session_id, player_id, player_username, IP 주소를 포함해야 한다.
2. WHEN 세션이 종료되면, THE Session_Logger SHALL 세션 종료 로그를 기록해야 한다. 로그에는 종료 사유를 포함해야 한다.
3. WHEN 세션 종료 로그를 기록한 후, THE Session_Logger SHALL 해당 플레이어의 로그 파일 핸들러를 정리(close)해야 한다.

### 요구사항 3: 명령어 입력 로깅

**사용자 스토리:** 서버 운영자로서, 플레이어가 입력한 명령어를 개별 로그에서 확인하고 싶다. 이를 통해 부정 행위를 탐지하고 게임 밸런스를 분석할 수 있다.

#### 수용 기준

1. WHEN 인증된 플레이어가 게임 명령어를 입력하면, THE Session_Logger SHALL 해당 명령어를 플레이어 로그 파일에 기록해야 한다.
2. THE Session_Logger SHALL 명령어 로그에 타임스탬프와 원본 명령어 문자열을 포함해야 한다.

### 요구사항 4: 기존 로그 시스템 보존

**사용자 스토리:** 서버 운영자로서, 플레이어별 로그 추가 후에도 기존 통합 로그가 동일하게 동작하길 원한다. 기존 모니터링 및 디버깅 워크플로우가 영향받지 않아야 한다.

#### 수용 기준

1. THE Global_Logger SHALL 플레이어별 로그 기능 추가 후에도 기존과 동일한 로그 출력을 유지해야 한다.
2. THE Session_Logger SHALL Global_Logger의 로그 레벨, 포맷, 로테이션 설정에 영향을 주지 않아야 한다.

### 요구사항 5: 로그 파일 관리

**사용자 스토리:** 서버 운영자로서, 플레이어별 로그 파일이 무한히 커지지 않도록 관리하고 싶다.

#### 수용 기준

1. THE Session_Logger SHALL 플레이어별 로그 파일에 크기 기반 로테이션을 적용해야 한다. 최대 파일 크기는 10MB로 설정한다.
2. THE Session_Logger SHALL 로테이션 시 최대 5개의 백업 파일을 유지해야 한다.
3. WHEN 로테이션이 발생하면, THE Session_Logger SHALL 이전 로그 파일을 gzip 압축해야 한다. 압축 파일명은 `{player_id}.log.{n}.gz` 형식이다.

### 요구사항 6: 리소스 정리

**사용자 스토리:** 서버 운영자로서, 세션 종료 시 로그 관련 리소스가 누수 없이 정리되길 원한다.

#### 수용 기준

1. WHEN 세션이 종료되면, THE Session_Logger SHALL 해당 세션의 파일 핸들러를 로거에서 제거하고 닫아야 한다.
2. WHEN 서버가 종료되면, THE TelnetServer SHALL 모든 활성 세션의 로그 핸들러를 정리해야 한다.
3. IF 로그 파일 생성 또는 기록 중 오류가 발생하면, THEN THE Session_Logger SHALL 오류를 Global_Logger에 기록하고 게임 세션 진행에는 영향을 주지 않아야 한다.

### 요구사항 7: 미인증 세션 처리

**사용자 스토리:** 서버 운영자로서, 인증되지 않은 세션에 대해서는 개별 로그 파일이 생성되지 않아야 한다.

#### 수용 기준

1. WHILE 세션이 미인증 상태인 동안, THE Session_Logger SHALL 플레이어별 로그 파일을 생성하지 않아야 한다.
2. THE Session_Logger SHALL 인증 성공 시점에서만 플레이어별 로그 핸들러를 설정해야 한다.
