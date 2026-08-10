# 어드민 채널

어드민은 게임 세션과 분리된 경로와 인증을 갖는다. 게임에 로그인하지 않고도 접속할 수 있으며, 게임 세션에서 `is_admin`이 참이어도 어드민 기능을 쓸 수 없다.

## 구간 구조

```
Godot 어드민 패널 ──ws /admin──▶ 게이트웨이 ──TCP 4001──▶ MUD 서버
랜딩 백엔드 ─────────────────────────────────TCP 4001──▶ MUD 서버
```

서버는 게임용 4000과 별도로 4001을 연다. 프레이밍 규약(개행 구분 JSON 라인, UTF-8)은 게임 채널과 동일하지만 Telnet IAC 협상은 하지 않는다. 어드민 채널에 사람이 터미널로 붙는 경우를 지원하지 않으므로 협상이 불필요하다.

게이트웨이는 WebSocket `/admin` 경로를 4001로 프록시한다. 게임 경로 `/ws`와 혼용되지 않는다.

4001은 외부에 노출하지 않는다. 방화벽이나 바인드 주소로 접근을 제한하고, 게이트웨이와 랜딩 백엔드만 도달할 수 있게 구성한다.

## 인증

두 종류의 주체가 접속한다.

| 주체 | 인증 방식 | 권한 |
|---|---|---|
| 관리자 | `players` 테이블의 `is_admin` 계정 + 비밀번호 | 전체 |
| 서비스 | 환경변수로 설정한 서비스 계정 + 토큰 | 계정 생성만 |

관리자 인증은 게임 계정을 재사용한다. 계정 체계를 이중화하지 않기 위한 결정이다. 게임 로그인과 별개로 어드민 채널에서 다시 인증해야 하며, 게임 세션의 인증 상태가 어드민 채널로 전이되지 않는다.

비밀번호 비교는 `bcrypt`로 수행한다. 기존 Node 웹어드민은 환경변수 값과 평문을 비교했으나 이 방식은 폐기한다.

세션 유효 기간은 2시간이다. 만료되면 서버가 인증 상태를 해제하고 이후 요청을 `NOT_AUTHENTICATED`로 거절한다.

### admin_login

```json
{
  "type": "admin_login",
  "seq": 1,
  "username": "player5426",
  "password": "test1234"
}
```

```json
{
  "type": "admin_login_result",
  "seq": 1,
  "success": true,
  "admin": {
    "id": "cf65f7f3-...",
    "username": "player5426",
    "display_name": "SUPERADMIN"
  },
  "expires_at": "2026-08-08T18:45:00"
}
```

`is_admin`이 거짓인 계정은 자격이 올바르더라도 `success: false`, `reason_code: PERMISSION_DENIED`로 거절한다.

### service_login

```json
{
  "type": "service_login",
  "seq": 1,
  "service": "landing",
  "token": "<환경변수 LANDING_SERVICE_TOKEN 값>"
}
```

```json
{
  "type": "service_login_result",
  "seq": 1,
  "success": true,
  "service": "landing",
  "expires_at": "2026-08-08T18:45:00"
}
```

랜딩 백엔드가 계정 생성을 위해 사용한다. 인증에 성공하면 `account_create`만 호출할 수 있고 다른 어드민 메시지는 `PERMISSION_DENIED`로 거절된다.

서비스 이름은 서버가 보유한 허용 목록에 있어야 하며, 토큰은 환경변수 `{서비스명 대문자}_SERVICE_TOKEN`에서 읽는다. 토큰이 설정되지 않은 서비스는 어떤 값으로도 인증되지 않는다. 비교는 상수 시간으로 수행한다.

## 접속과 인증 전 상태

어드민 채널은 IAC 협상을 하지 않고 접속 직후 `welcome`을 보낸다.

```json
{
  "type": "welcome",
  "protocol_version": 1,
  "channel": "admin",
  "server_version": "development@dev"
}
```

게임 채널의 `welcome`과 같은 타입이지만 `channel`이 `admin`이고 `supported_locales`와 `title`이 없다. 어드민은 번역을 하지 않고 도구가 소비하므로 표시용 정보를 담지 않는다. 클라이언트는 이 값으로 자신이 붙은 채널을 확인하고, 기대와 다르면 연결을 끊는다.

게임 채널 전용 메시지(`login`, `logout`, `action`, `chat`, `client_info`)를 받으면 `admin_rejected`에 `NOT_APPLICABLE`로 거절하고 `detail`에 두 채널을 모두 밝힌다. 조용히 무시하면 잘못된 포트에 붙은 사실이 드러나지 않는다.

인증 전에 허용되는 메시지는 `admin_login`, `service_login`, `ping`뿐이다. 그 외는 `admin_rejected`에 `NOT_AUTHENTICATED`로 응답하며 연결은 유지한다. 인증 시도 없이 60초가 지나면 연결이 끊어진다.

`ping`은 인증 전후 모두 허용되며 게임 채널과 같은 형식의 `pong`으로 응답한다.

세션 만료 시각은 인증 성공 시각 기준 2시간이다. 만료되면 서버가 `admin_rejected`에 `SESSION_EXPIRED`를 보내고 연결을 끊는다.

### 환경변수

| 변수 | 기본값 | 용도 |
|---|---|---|
| `ADMIN_HOST` | `127.0.0.1` | 어드민 서버 바인드 주소. 루프백이 기본인 것은 의도적이다 |
| `ADMIN_PORT` | `4001` | 어드민 서버 포트 |
| `LANDING_SERVICE_TOKEN` | 없음 | 랜딩 백엔드의 서비스 토큰. 없으면 서비스 인증이 불가능하다 |

## 계정 생성

게임 클라이언트에는 회원가입이 없다. 랜딩 사이트가 이 경로로 계정을 만든다.

```json
{
  "type": "account_create",
  "seq": 2,
  "username": "newplayer",
  "password": "<평문>",
  "email": "user@example.com",
  "preferred_locale": "ko"
}
```

```json
{
  "type": "account_create_result",
  "seq": 2,
  "success": true,
  "player_id": "a1b2c3d4-..."
}
```

서버가 수행하는 검증:

- `username` 중복 여부. 중복이면 `reason_code: USERNAME_TAKEN`
- `username` 길이와 허용 문자
- `password` 최소 길이
- `email` 형식. 선택 항목이므로 비어 있어도 된다

비밀번호는 서버가 `bcrypt`로 해시해 저장한다. 랜딩 백엔드는 평문을 보관하지 않는다.

신규 계정의 기본값은 `players` 테이블의 DEFAULT를 따른다. `preferred_locale`은 저장되지만 서버가 번역에 사용하지 않으며 통계 목적이다. 관리자 여부는 항상 거짓이다.

## 리소스 조회와 변경

기존 Node 웹어드민의 `db-client.ts`가 제공했던 8개 리소스를 서버가 대신 제공한다.

| 리소스 | 대상 테이블 |
|---|---|
| `players` | players |
| `rooms` | rooms |
| `room_connections` | room_connections |
| `monsters` | monsters |
| `objects` | game_objects |
| `item_prices` | item_prices |
| `factions` | factions |
| `faction_relations` | faction_relations |

### admin_list

```json
{
  "type": "admin_list",
  "seq": 10,
  "resource": "monsters",
  "page": 1,
  "page_size": 50,
  "filter": { "is_alive": true },
  "sort": { "field": "level", "order": "desc" }
}
```

```json
{
  "type": "admin_list_result",
  "seq": 10,
  "resource": "monsters",
  "page": 1,
  "page_size": 50,
  "total": 66,
  "rows": []
}
```

`rows`의 각 항목은 DB 컬럼을 그대로 담는다. 게임 채널의 엔티티 스키마와 달리 언어별 dict로 묶지 않고 `name_en`, `name_ko`처럼 원본 컬럼명을 유지한다. 어드민은 데이터를 편집하는 도구이므로 원본 구조가 그대로 보여야 한다.

### admin_get

```json
{
  "type": "admin_get",
  "seq": 11,
  "resource": "players",
  "id": "cf65f7f3-..."
}
```

### admin_create / admin_update / admin_delete

```json
{
  "type": "admin_update",
  "seq": 12,
  "resource": "rooms",
  "id": "0a1b2c3d-...",
  "values": {
    "description_ko": "성문 앞 넓은 광장이다.",
    "blocked_exits": ["west", "north"]
  }
}
```

```json
{
  "type": "admin_mutate_result",
  "seq": 12,
  "resource": "rooms",
  "id": "0a1b2c3d-...",
  "success": true
}
```

`admin_delete`는 참조 무결성을 검사한다. 다른 레코드가 참조하는 행은 `reason_code: REFERENCED`로 거절하고 참조 목록을 함께 돌려준다.

변경이 실행 중인 게임 상태에 영향을 주는 경우 서버는 메모리 캐시를 갱신하고 해당 방의 플레이어에게 `room_info`를 재전송한다. 기존 Node 웹어드민이 DB를 직접 수정해 서버 캐시와 어긋났던 문제를 해소하기 위한 규약이다.

## 통계와 맵

### admin_stats

```json
{
  "type": "admin_stats_result",
  "seq": 20,
  "counts": {
    "rooms": 520,
    "monsters": 66,
    "players": 9,
    "players_online": 1,
    "objects": 101,
    "factions": 3
  },
  "room_statistics": {},
  "object_statistics": {}
}
```

`AdminManager.get_admin_stats()`, `_get_room_statistics()`, `_get_object_statistics()`의 반환값을 그대로 전달한다. 이미 dict를 반환하므로 구조화 전송에 추가 작업이 거의 없다.

### admin_map

```json
{
  "type": "admin_map_result",
  "seq": 21,
  "bounds": { "min_x": -25, "max_x": 12, "min_y": -11, "max_y": 14 },
  "rooms": [
    {
      "id": "0a1b2c3d-...",
      "x": 0,
      "y": 7,
      "room_type": "gate",
      "description_ko": "성문 앞 넓은 광장...",
      "description_en": "A wide plaza...",
      "blocked_exits": ["west"],
      "creature_count": 3,
      "player_count": 1,
      "item_count": 4,
      "factions": { "ash_knights": 2, "wild": 1 }
    }
  ]
}
```

`utils/map_exporter.py`가 생성하던 `world_map_unified.html`을 대체한다. HTML 렌더링을 제거하고 쿼리 결과만 내보내며, 렌더링은 Godot 어드민 패널이 담당한다.

이 데이터는 좌표, 막힌 출구, 종족별 분포를 노출하므로 플레이어에게 제공하지 않는다. 어드민 채널 전용이다.

## 실시간 액션

`AdminManager`가 이미 보유한 기능과 관리자 명령어를 노출한다.

```json
{
  "type": "admin_action",
  "seq": 30,
  "action": "spawn_monster",
  "params": {
    "template_id": "template_small_rat",
    "x": 0,
    "y": 7
  }
}
```

| action | params | 대응 기존 기능 |
|---|---|---|
| `goto` | `target_player`, `x`, `y` | goto 명령어. 대상 플레이어를 좌표로 이동 |
| `kick` | `target_player`, `reason` | `AdminManager.kick_player()` |
| `spawn_monster` | `template_id`, `x`, `y` | spawnmonster |
| `spawn_item` | `template_id`, `x`, `y` | mkitem |
| `terminate` | `target_id`, `reason` | terminate. 객체나 몬스터 완전 삭제 |
| `create_room` | `x`, `y`, `room_type`, 설명 | `create_room_realtime()` |
| `update_room` | `id`, 변경 값 | `update_room_realtime()` |
| `create_exit` | `from_id`, `direction`, `to_id` | createexit |
| `validate_world` | 없음 | `validate_and_repair_world()`. 기존에 명령어로 노출되지 않았음 |
| `list_monster_templates` | 없음 | templates |
| `list_item_templates` | 없음 | itemtemplates |
| `scheduler` | `operation`, `event_name` | scheduler. list/info/enable/disable |
| `change_display_name` | `target_player`, `display_name` | adminchangename |
| `room_info` | `x`, `y` | info |

```json
{
  "type": "admin_action_result",
  "seq": 30,
  "action": "spawn_monster",
  "success": true,
  "data": { "monster_id": "e1f2a3b4-..." }
}
```

`goto`의 `target_player`는 자기 자신도 지정할 수 있다. 어드민 채널이 게임 세션 상태를 변경하는 유일한 경로이므로, 서버는 대상 플레이어의 게임 세션이 활성인지 확인하고 없으면 `reason_code: PLAYER_NOT_ONLINE`으로 거절한다.

## 거절과 오류

게임 채널과 같은 형식을 쓴다.

```json
{
  "type": "admin_rejected",
  "seq": 30,
  "action": "spawn_monster",
  "reason_code": "NOT_FOUND",
  "detail": "template_id not found: template_unknown"
}
```

어드민 채널의 사유 코드에는 게임 채널의 코드에 다음이 추가된다.

| 코드 | 의미 |
|---|---|
| `USERNAME_TAKEN` | 계정 생성 시 사용자명 중복 |
| `REFERENCED` | 삭제 대상이 다른 레코드에서 참조됨 |
| `PLAYER_NOT_ONLINE` | 대상 플레이어의 게임 세션이 없음 |
| `VALIDATION_FAILED` | 입력 값 검증 실패. `detail`에 필드별 사유 |
| `SESSION_EXPIRED` | 어드민 세션 만료 |

어드민 채널은 사람이 직접 읽는 UI가 아니라 도구를 경유하므로 거절 응답에 번역 키를 쓰지 않고 `detail`에 영문 설명을 담는다. Godot 어드민 패널이 코드별 안내 문구를 자체 보유한다.

## 권한 세분화

현재 권한은 `players.is_admin` 단일 boolean이며 역할 구분이 없다. 어드민 인증에 성공한 계정은 위의 모든 기능을 사용할 수 있다.

역할 기반 권한(읽기 전용 GM, 콘텐츠 편집자, 운영자 구분)은 이번 범위에 포함하지 않는다. 도입할 경우 `players` 테이블에 역할 컬럼을 추가하고 메시지 타입별 허용 역할을 정의해야 한다. 향후 확장 지점으로 기록한다.

## 감사 로그

모든 `admin_action`과 `admin_create` / `admin_update` / `admin_delete`는 실행 주체, 대상, 변경 내용, 시각을 로그에 남긴다. 로그 형식은 프로젝트 로깅 규칙을 따른다. 감사 로그를 DB 테이블로 저장할지는 서버 스펙의 설계 단계에서 결정한다.
