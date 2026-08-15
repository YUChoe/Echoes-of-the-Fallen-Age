# 클라이언트 → 서버 메시지

클라이언트가 보낼 수 있는 메시지는 6종이다. 게임 상호작용은 전부 `action` 하나로 수렴하고, verb와 params가 세부를 결정한다.

| type | 인증 필요 | 설명 |
|---|---|---|
| `login` | 아니오 | 계정 인증 |
| `logout` | 예 | 인증 해제. 연결은 유지 |
| `action` | 예 | 게임 액션 |
| `chat` | 예 | 채팅 |
| `ping` | 아니오 | 유휴 유지 |
| `client_info` | 아니오 | 클라이언트 정보 통지 |

## login

```json
{
  "type": "login",
  "seq": 1,
  "username": "player5426",
  "password": "test1234"
}
```

비밀번호는 평문으로 전송된다. 전송 구간 보호는 WebSocket의 TLS(wss)에 의존한다. 운영 환경에서 게이트웨이 앞단에 TLS 종단이 반드시 필요하다. 서버는 `bcrypt`로 저장된 해시와 비교한다.

응답은 `login_result`다. 실패 시 서버는 실패 횟수를 기록하고, 같은 연결에서 5회 연속 실패하면 연결을 종료한다.

## logout

```json
{
  "type": "logout",
  "seq": 42
}
```

세션의 인증 상태와 게임 상태를 해제한다. 전투나 대화 중이면 해당 인스턴스를 정리한 뒤 처리한다. 응답은 `logout_result`다. 연결은 유지되므로 클라이언트는 로그인 화면으로 전환한다.

## action

```json
{
  "type": "action",
  "seq": 43,
  "verb": "attack",
  "target": "49a55ff4-a1d9-4449-a72c-c664686e1102",
  "params": {}
}
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `verb` | string | 필수 | 액션 종류 |
| `target` | string(uuid) | verb에 따라 | 대상 엔티티의 uuid |
| `params` | object | verb에 따라 | verb별 부가 인자 |

`target`은 항상 uuid 전체 문자열이다. 축약이나 접두어 매칭을 지원하지 않는다. 클라이언트가 버튼에서 uuid를 그대로 실어 보내기 때문에 축약이 필요하지 않다.

클라이언트는 엔티티 속성으로 버튼을 구성하므로 서버가 허용하지 않는 verb를 보낼 수 있다. 서버는 verb 적용 가능성을 검증하고 `action_rejected`로 사유 코드를 돌려준다. 클라이언트는 이 응답을 근거로 버튼을 비활성화하거나 안내를 표시한다.

### verb 목록

이동과 탐험:

| verb | target | params | 설명 |
|---|---|---|---|
| `move` | 없음 | `{"direction": "north"}` | 방향 이동. 값은 north, south, east, west |
| `enter` | 없음 | 없음 | 현재 방의 통로로 진입. `room_connections` 테이블의 좌표 연결을 사용하므로 대상 엔티티가 없다 |
| `look` | 없음 | 없음 | 현재 방 정보 재요청 |
| `examine` | uuid | 없음 | 대상 상세 조사 |

아이템:

| verb | target | params | 설명 |
|---|---|---|---|
| `get` | uuid | `{"quantity": 3}` | 방에서 줍기. quantity 생략 시 전량 |
| `drop` | uuid | `{"quantity": 1}` | 버리기 |
| `use` | uuid | 없음 | 사용 |
| `equip` | uuid | 없음 | 장착 |
| `unequip` | uuid | 없음 | 해제 |
| `unequip_all` | 없음 | 없음 | 전체 해제 |
| `give` | uuid | `{"to": "<player uuid>", "quantity": 1}` | 다른 플레이어에게 건네기 |
| `read` | uuid | `{"page": 2}` | 읽기. page 생략 시 1 |

컨테이너:

| verb | target | params | 설명 |
|---|---|---|---|
| `open` | uuid | 없음 | 열어 내용 조회. 서버가 열림 상태를 유지하지 않는 조회 동작이므로 대응하는 `close`가 없다 |
| `put` | uuid | `{"container": "<uuid>", "quantity": 1}` | 컨테이너에 넣기 |
| `take_from` | uuid | `{"container": "<uuid>", "quantity": 1}` | 컨테이너에서 꺼내기 |

전투:

| verb | target | params | 설명 |
|---|---|---|---|
| `attack` | uuid | 없음 | 전투 시작 또는 전투 중 공격 |
| `flee` | 없음 | 없음 | 도주 |
| `use_item` | uuid | 없음 | 전투 중 아이템 사용 |
| `end_turn` | 없음 | 없음 | 턴 종료 |

대화:

| verb | target | params | 설명 |
|---|---|---|---|
| `talk` | uuid | 없음 | 대화 시작 |
| `dialogue_choice` | 없음 | `{"choice": 2}` | 선택지 선택. 대화 인스턴스 로컬 번호 |
| `dialogue_end` | 없음 | 없음 | 대화 종료 |

거래는 대화 안에서 이루어진다. 전용 verb 를 두지 않는다. 상인은 선택지로 물건을 늘어놓고 플레이어는 `dialogue_choice` 로 고른다. 상점을 별도 개념으로 두면 같은 재고를 두 경로가 보게 되고 진실의 출처가 갈라진다.

사회:

| verb | target | params | 설명 |
|---|---|---|---|
| `follow` | uuid | 없음 | 대상 따라가기 |
| `unfollow` | 없음 | 없음 | 따라가기 중단 |
| `emote` | 없음 | `{"emote_id": "wave"}` | 감정 표현. 목록에서 선택 |
| `who` | 없음 | 없음 | 접속자 목록 요청 |
| `players_here` | 없음 | 없음 | 같은 방 플레이어 목록 요청 |

상태 조회:

| verb | target | params | 설명 |
|---|---|---|---|
| `request_state` | 없음 | 없음 | `player_state` 재전송 요청 |
| `request_inventory` | 없음 | 없음 | `inventory` 재전송 요청 |
| `request_combat_state` | 없음 | 없음 | `combat_state` 재전송 요청 |

계정:

| verb | target | params | 설명 |
|---|---|---|---|
| `changename` | 없음 | `{"display_name": "새이름"}` | 표시 이름 변경. 하루 1회 제한 |

### 폐기된 명령어

다음은 verb로 이전되지 않고 사라진다.

| 기존 명령어 | 처리 |
|---|---|
| `help` | 폐기. 버튼 UI에서 도움말이 불필요하며 클라이언트가 자체 안내를 제공 |
| `language` | 폐기. locale은 클라이언트가 소유한다 |
| `quit` | `logout` 메시지로 대체 |
| `stats` | `request_state` verb로 대체 |
| `inventory` | `request_inventory` verb로 대체 |
| `combat` | `request_combat_state` verb로 대체 |
| `say` `whisper` | `chat` 메시지로 분리 |
| 방향 별칭 `n` `s` `e` `w` | 폐기. `move` verb의 direction params로 통합 |
| 명령어 별칭 전체 | 폐기. 문자열 파싱이 없으므로 별칭 개념이 성립하지 않음 |

## chat

```json
{
  "type": "chat",
  "seq": 44,
  "channel": "room",
  "message": "안녕하세요",
  "to": null
}
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `channel` | string | 필수 | `room` 또는 `whisper` |
| `message` | string | 필수 | 메시지 본문. 최대 500자 |
| `to` | string(uuid) | channel이 whisper일 때 | 수신 플레이어 uuid |

채팅은 번역 대상이 아니다. 플레이어가 입력한 문장이 그대로 전달된다. 서버는 길이 검증과 제어문자 제거만 수행하고 내용을 변형하지 않는다.

`whisper`의 `to`는 uuid다. 기존에는 사용자명 문자열이었으나 대상 지정 규약을 따라 uuid로 통일한다. 클라이언트는 접속자 목록(`who` 응답)에서 uuid를 확보한다.

## ping

```json
{
  "type": "ping",
  "seq": 45
}
```

응답은 `pong`이다. 인증 전에도 사용할 수 있다. 서버 세션 유휴 타이머를 갱신한다.

## client_info

```json
{
  "type": "client_info",
  "seq": 2,
  "client_version": "0.1.0",
  "platform": "windows",
  "locale": "ko"
}
```

클라이언트가 자신의 정보를 통지한다. 서버는 이를 로그와 세션 메타데이터에 기록하며 동작을 바꾸지 않는다. `locale`은 서버가 번역에 사용하지 않고, 로그 분석과 통계 목적으로만 저장한다. 응답이 없는 단방향 통지이므로 클라이언트는 결과를 기다리지 않는다.
