# 요구사항 문서

## 소개

Python MUD Engine("카르나스 연대기: 분할된 지배권")은 asyncio 기반 비동기 텍스트 MUD 게임 서버입니다. Telnet(포트 4000)을 주 클라이언트로 사용하며, SQLite 데이터 지속성, 영어/한국어 다국어 지원, D&D 5e 기반 전투 시스템, 좌표 기반 월드 시스템을 포함합니다. 세력(잿빛 기사단, 고블린, 동물) 간 관계 시스템이 NPC/몬스터 상호작용에 영향을 줍니다.

## 용어집

- **MUD_Server**: asyncio 기반 Telnet 서버 (TelnetServer). 포트 4000에서 TCP 연결을 수신하고 클라이언트 세션을 관리하는 서버 컴포넌트
- **Session_Manager**: 플레이어 세션의 생명주기를 관리하는 컴포넌트 (SessionManager). 인증, 중복 로그인 감지, 세션 정리 담당
- **Game_Engine**: 게임 로직 중앙 조정자 (GameEngine). 모든 매니저를 초기화하고 통합하는 핵심 컴포넌트
- **World_Manager**: RoomManager, ObjectManager, MonsterManager를 통합하는 파사드 인터페이스 (WorldManager)
- **Combat_Handler**: D&D 5e 기반 인스턴스 턴제 전투를 처리하는 컴포넌트 (CombatHandler)
- **Combat_Manager**: 전투 인스턴스의 생성, 참가자 관리, 턴 순서를 관리하는 컴포넌트 (CombatManager)
- **DnD_Engine**: D&D 5e 규칙 기반 주사위 굴림, 공격 판정, 데미지 계산을 수행하는 엔진 (DnDCombatEngine)
- **Command_Processor**: 명령어 파싱, 라우팅, 실행을 담당하는 컴포넌트 (CommandProcessor)
- **Event_Bus**: 비동기 이벤트 발행/구독 시스템 (EventBus)
- **Monster_Manager**: 몬스터 스폰, 로밍, 리스폰을 관리하는 컴포넌트 (MonsterManager)
- **Player_Manager**: 플레이어 인증, 데이터 로드/저장을 관리하는 컴포넌트 (PlayerManager)
- **Global_Tick_Manager**: 3초 간격으로 전투 턴 처리 및 선공 몬스터 감지를 수행하는 타이머 (GlobalTickManager)
- **Spawn_Scheduler**: 30초 간격으로 몬스터 리스폰, 초기 스폰, 로밍을 처리하는 스케줄러
- **Telnet_Session**: 개별 Telnet 클라이언트 세션 (TelnetSession). Telnet 프로토콜 처리, 메시지 포맷팅, ANSI 색상 렌더링 담당
- **Room**: 좌표 기반(x, y) 게임 월드의 방. 다국어 설명, 출구 정보 포함
- **Monster**: D&D 스탯 기반 몬스터 엔티티. 타입(AGGRESSIVE/PASSIVE/NEUTRAL), 행동(STATIONARY/ROAMING/TERRITORIAL), 세력 포함
- **GameObject**: 게임 내 오브젝트(아이템, 장비, 컨테이너). 위치 타입(ROOM/INVENTORY/EQUIPPED/CONTAINER), 무게, 스택, 장비 슬롯 포함
- **Player**: 플레이어 엔티티. D&D 6스탯, 좌표 기반 위치, 세력, 퀘스트 진행 포함
- **CombatInstance**: 전투 인스턴스. 참가자 목록, DEX 기반 턴 순서, 타임아웃 관리 포함
- **Combatant**: 전투 참가자(플레이어 또는 몬스터). HP, 공격력, 방어력, 방어 상태 포함
- **Faction**: 세력(종족). 세력 간 관계(-100~100)로 적대/중립/우호 결정
- **PlayerStats**: D&D 기반 1차 능력치(STR/DEX/INT/WIS/CON/CHA)와 파생 스탯(HP/MP/ATK/DEF/SPD)
- **Localization_Manager**: JSON 파일 기반 다국어 메시지 관리자 (LocalizationManager). 영어/한국어 메��지 로드 및 변수 치환 담당
- **Quest_Manager**: 퀘스트 정의, 진행도 추적, 보상 지급을 관리하는 컴포넌트 (QuestManager)
- **Item_Template_Manager**: JSON 설정 파일 기반 아이템 템플릿 관리자 (ItemTemplateManager). 아이템 인스턴스 생성 담당
- **Scheduler_Manager**: 15초 간격 글로벌 스케줄러. 전투 타임아웃 tick 등 주기적 작업 관리
- **Time_Manager**: 게임 내 시간(낮/밤) 시스템 관리자
- **ANSI_Colors**: Telnet 클라이언트용 ANSI 색상 코드 유틸리티 클래스

## 요구사항

### 요구사항 1: Telnet 서버 및 세션 관리

**사용자 스토리:** 게임 관리자로서, 나는 안정적인 Telnet 서버를 시작하고 중지할 수 있기를 원한다. 그래야 다수의 플레이어가 동시에 접속하여 게임을 즐길 수 있다.

#### 승인 기준

1. WHEN 관리자가 서버 시작 명령을 실행하면 THEN MUD_Server는 포트 4000에서 TCP 연결을 수신하고 Game_Engine, Event_Bus, Spawn_Scheduler, Global_Tick_Manager를 초기화해야 한다
2. WHEN 클라이언트가 TCP 연결을 수립하면 THEN MUD_Server는 고유 session_id를 가진 Telnet_Session을 생성하고 환영 메시지와 메뉴(로그인/회원가입/종료)를 전송해야 한다
3. WHEN 관리자가 서버 중지 명령을 실행하면 THEN MUD_Server는 모든 활성 세션에 종료 알림을 전송하고, 플레이어 데이터를 저장한 후, 모든 연결을 안전하게 종료해야 한다
4. WHILE 서버가 실행 중인 동안 THEN MUD_Server는 60초 간격으로 비활성 세션을 감지하고 정리해야 한다
5. WHEN 플레이어가 예기치 않게 연결을 끊으면 THEN Session_Manager는 해당 세션을 정리하고, 전투 중이었다면 Combat_Manager에 연결 해제 상태를 표시하며, 다른 플레이어에게 영향을 주지 않아야 한다
6. WHILE 다수의 플레이어가 동시에 연결된 동안 THEN MUD_Server는 asyncio 기반 비동기 I/O로 성능 저하 없이 모든 연결을 처리해야 한다

### 요구사항 2: 인증 시스템

**사용자 스토리:** 플레이어로서, 나는 Telnet 서버에 접속하여 계정을 생성하거나 로그인할 수 있기를 원한다. 그래야 게임에 참여할 수 있다.

#### 승인 기준

1. WHEN 플레이어가 메뉴에서 로그인을 선택하면 THEN MUD_Server는 사용자명과 비밀번호를 순차적으로 요구하고, 비밀번호 입력 시 Telnet ECHO를 비활성화해야 한다
2. WHEN 플레이어가 올바른 자격 증명을 제공하면 THEN Player_Manager는 bcrypt 해시로 비밀번호를 검증하고, Player 객체를 로드하여 마지막 위치(last_room_x, last_room_y) 좌표의 방에 배치해야 한다
3. WHEN 플레이어가 메뉴에서 회원가입을 선택하면 THEN MUD_Server는 사용자명(3-20자, 영문/숫자/언더스코어)과 비밀번호(최소 6자, 확인 입력 포함)를 요구하고, bcrypt로 해싱하여 SQLite에 저장해야 한다
4. IF 잘못된 자격 증명이 제공되면 THEN MUD_Server는 오류 메시지를 표시하고 재시도를 허용하되, 3회 실패 시 연결을 종료해야 한다
5. WHEN 동일 계정으로 다른 세션에서 로그인하면 THEN Session_Manager는 기존 세션에 "다른 곳에서 로그인" 메시지를 전송한 후 기존 연결을 종료하고, 새 세션으로 정상 로그인을 진행해야 한다
6. WHEN 플레이어가 로그인에 성공하면 THEN Game_Engine은 Event_Bus를 통해 PLAYER_CONNECTED 및 PLAYER_LOGIN 이벤트를 발행하고, 같은 방의 다른 플레이어에게 로그인 알림을 전송해야 한다
7. WHEN 재접속한 플레이어가 이전에 전투 중이었다면 THEN Game_Engine은 try_rejoin_combat()을 호출하여 기존 CombatInstance에 복귀시키고 Combatant 데이터를 갱신해야 한다

### 요구사항 3: 좌표 기반 월드 이동 시스템

**사용자 스토리:** 플레이어로서, 나는 게임 세계에서 방향 명령으로 이동하고 환경을 탐색할 수 있기를 원한다. 그래야 게임 세계를 즐길 수 있다.

#### 승인 기준

1. WHEN 플레이어가 방향 명령(north/south/east/west 또는 n/s/e/w)을 입력하면 THEN Game_Engine은 현재 좌표에서 해당 방향의 인접 좌표(north: y+1, south: y-1, east: x+1, west: x-1)에 방이 존재하는지 확인하고, 존재하면 플레이어를 이동시켜야 한다
2. WHEN 플레이어가 새로운 방에 들어가면 THEN Game_Engine은 방의 다국어 설명, 출구 목록, 방 내 몬스터(세력 기반 분류), 오브젝트, 다른 플레이어 목록을 표시해야 한다
3. WHEN 플레이어가 look(별칭: l) 명령을 사용하면 THEN Command_Processor는 현재 방의 상세 정보를 엔티티 번호 매핑과 함께 표시해야 한다
4. IF 플레이어가 존재하지 않는 방향으로 이동하려 하면 THEN Game_Engine은 해당 방향으로 이동할 수 없다는 오류 메시지를 표시해야 한다
5. WHEN 플레이어가 enter 명령을 사용하면 THEN Game_Engine은 room_connections 테이블에서 현재 좌표의 특별 연결을 조회하고, 연결된 방으로 이동시켜야 한다
6. WHEN 플레이어가 방을 이동하면 THEN Game_Engine은 Event_Bus를 통해 ROOM_LEFT 및 ROOM_ENTERED 이벤트를 발행하고, 이전 방과 새 방의 플레이어에게 이동 알림을 브로드캐스트해야 한다

### 요구사항 4: D&D 5e 기반 전투 시스템

**사용자 스토리:** 플레이어로서, 나는 D&D 5e 규칙 기반의 턴제 전투를 통해 몬스터와 싸울 수 있기를 원한다. 그래야 전략적인 전투 경험을 즐길 수 있다.

#### 승인 기준

1. WHEN 플레이어가 attack(별칭: att, kill, fight) 명령과 대상 번호를 입력하면 THEN Combat_Handler는 해당 몬스터와의 CombatInstance를 생성하고, DEX 기반으로 턴 순서를 결정하며, 전투 시작 메시지를 전송해야 한다
2. WHEN 플레이어 턴에 공격 행동을 선택하면 THEN DnD_Engine은 d20 + attack_bonus로 공격 굴림을 수행하고, 결과가 대상의 armor_class 이상이면 명중으로 판정해야 한다
3. WHEN 공격이 명중하면 THEN DnD_Engine은 damage_dice(무기 장착 시 무기 dice, 미장착 시 1d1)로 데미지를 계산하고, 방어 중인 대상은 데미지를 50% 감소시키며, 실제 데미지는 max(1, damage - target.defense)로 적용해야 한다
4. WHEN d20 굴림 결과가 20이면 THEN DnD_Engine은 크리티컬 히트로 판정하여 주사위를 2회 굴려야 하고, d20 결과가 1이면 자동 실패(0, False)를 반환해야 한다
5. WHEN 몬스터 턴이 되면 THEN Global_Tick_Manager는 3초 간격 틱에서 Combat_Handler의 process_monster_turn()을 호출하여 랜덤 플레이어를 타겟으로 공격을 수행해야 한다
6. WHEN 플레이어가 defend(별칭: def, guard, block) 명령을 사용하면 THEN Combat_Handler는 해당 Combatant의 is_defending 상태를 True로 설정해야 한다
7. WHEN 플레이어가 flee(별칭: run, escape, retreat) 명령을 사용하면 THEN Combat_Handler는 50% 확률로 도주 성공 여부를 판정하고, 성공 시 랜덤 출구 방향으로 이동시켜야 한다
8. WHEN 전투에서 몬스터의 HP가 0 이하가 되면 THEN Combat_Handler는 원래 방에 corpse 컨테이너 오브젝트를 생성하고, 몬스터 DB의 is_alive를 False로 처리해야 한다
9. WHEN 전투 중 플레이어가 연결을 끊으면 THEN Combat_Manager는 mark_player_disconnected()로 연결 해제 상태를 표시하고, 연결된 플레이어가 없는 전투는 15초 간격 tick으로 8회(2분) 후 자동 종료해야 한다
10. WHEN 같은 방에서 다른 플레이어가 동일 몬스터를 공격하면 THEN Combat_Handler는 기존 CombatInstance에 해당 플레이어를 추가해야 한다
11. WHEN 플레이어가 endturn 명령을 사용하면 THEN Combat_Handler는 현재 턴을 종료하고 다음 참가자에게 턴을 넘겨야 한다
12. WHEN 전투 중 플레이어가 item 명령을 사용하면 THEN Command_Processor는 전투 중 아이템 사용 인터페이스를 제공해야 한다

### 요구사항 5: 몬스터 스폰, 로밍, 리스폰 시스템

**사용자 스토리:** 게임 관리자로서, 나는 몬스터가 자동으로 스폰되고, 월드를 돌아다니며, 사망 후 리스폰되기를 원한다. 그래야 플레이어에게 지속적인 전투 콘텐츠를 제공할 수 있다.

#### 승인 기준

1. WHILE Spawn_Scheduler가 실행 중인 동안 THEN Monster_Manager는 30초 간격으로 _process_respawns(), _process_initial_spawns(), _process_monster_roaming()을 순서대로 실행해야 한다
2. WHEN 사망한 몬스터의 respawn_time이 경과하면 THEN Monster_Manager는 해당 몬스터를 리스폰(is_alive=True, HP 복원)해야 한다
3. WHEN 초기 스폰을 처리할 때 THEN Monster_Manager는 spawn_points를 순회하며, 글로벌 제한(template_id별 전체 서버 최대 수)과 방별 제한(spawn_point의 max_count)을 확인한 후, spawn_chance 확률로 템플릿 기반 몬스터를 생성해야 한다
4. WHEN 로밍 가능한 몬스터(behavior가 ROAMING 또는 TERRITORIAL)의 로밍을 처리할 때 THEN Monster_Manager는 roam_chance 확률로 roaming_area 범위 내 인접 4방향 중 방이 존재하는 좌표로 이동시키고, 이전 방과 새 방의 플레이어에게 이동 메시지를 브로드캐스트해야 한다
5. WHILE Global_Tick_Manager가 3초 간격으로 실행 중인 동안 WHEN 비전투 플레이어가 있는 방에 AGGRESSIVE 타입 몬스터가 존재하면 THEN Global_Tick_Manager는 해당 플레이어와 몬스터 간 자동 전투를 시작해야 한다

### 요구사항 6: 세력(Faction) 시스템

**사용자 스토리:** 플레이어로서, 나는 세력 간 관계에 따라 몬스터와 NPC의 반응이 달라지기를 원한다. 그래야 세계관에 몰입할 수 있다.

#### 승인 기준

1. THE Game_Engine은 factions 테이블에서 세력 정보(id, 다국어 이름, 기본 태도)를 로드하고, faction_relations 테이블에서 세력 간 관계 값(-100~100)을 로드해야 한다
2. WHEN 플레이어가 방에 입장하면 THEN Telnet_Session은 몬스터를 플레이어 세력과의 관계에 따라 분류(우호적 몬스터는 NPC로, 중립 몬스터는 동물로, 적대적 몬스터는 몬스터로)하여 표시해야 한다
3. THE Player 모델은 기본 세력으로 ash_knights(잿빛 기사단)를 가져야 한다
4. WHEN 몬스터의 세력이 플레이어 세력과 적대 관계이고 monster_type이 AGGRESSIVE이면 THEN Global_Tick_Manager는 해당 몬스터가 플레이어를 자동 공격하도록 처리해야 한다

### 요구사항 7: 아이템, 장비, 컨테이너 시스템

**사용자 스토리:** 플레이어로서, 나는 아이템을 획득하고, 장비를 장착하며, 컨테이너를 사용할 수 있기를 원한다. 그래야 캐릭터를 강화하고 전리품을 관리할 수 있다.

#### 승인 기준

1. WHEN 플레이어가 get 명령과 대상 번호를 입력하면 THEN World_Manager는 해당 GameObject의 location_type을 INVENTORY로, location_id를 player_id로 변경하고, 플레이어의 소지 무게가 max_carry_weight를 초과하지 않는지 확인해야 한다
2. WHEN 플레이어가 drop 명령을 사용하면 THEN World_Manager는 해당 GameObject의 location_type을 ROOM으로, location_id를 현재 room_id로 변경해야 한다
3. WHEN 플레이어가 inventory(별칭: inv, i) 명령을 사용하면 THEN Command_Processor는 플레이어의 INVENTORY 및 EQUIPPED 상태의 모든 GameObject를 표시해야 한다
4. WHEN 플레이어가 equip 명령을 사용하면 THEN World_Manager는 해당 GameObject의 equipment_slot에 맞는 슬롯(HEAD, BODY, WEAPON, right_hand 등)에 장착하고, is_equipped를 True로, location_type을 EQUIPPED로 변경해야 한다
5. WHEN 플레이어가 unequip 명령을 사용하면 THEN World_Manager는 해당 장비의 is_equipped를 False로, location_type을 INVENTORY로 변경해야 한다
6. WHEN 플레이어가 unequipall 명령을 사용하면 THEN World_Manager는 플레이어의 모든 장착 장비를 해제하고 INVENTORY로 이동시켜야 한다
7. WHEN 플레이어가 open 명령으로 컨테이너를 열면 THEN World_Manager는 해당 컨테이너(properties.is_container=True)의 내용물 목록을 표시해야 한다
8. WHEN 플레이어가 put 명령을 사용하면 THEN World_Manager는 지정된 아이템의 location_type을 CONTAINER로, location_id를 컨테이너 ID로 변경해야 한다
9. WHEN 스택 가능한 아이템(max_stack > 1)을 획득하면 THEN World_Manager는 인벤토리에 동일 아이템이 있고 스택 수가 max_stack 미만이면 기존 스택에 추가해야 한다
10. WHEN 장비를 장착하면 THEN PlayerStats는 해당 장비의 보너스를 equipment_bonuses에 반영하여 파생 스탯(ATK, DEF 등)을 재계산해야 한다
11. WHEN 플레이어가 use 명령을 사용하면 THEN Command_Processor는 해당 아이템의 사용 효과를 적용해야 한다

### 요구사항 8: 능력치 시스템

**사용자 스토리:** 플레이어로서, 나는 D&D 기반 능력치 시스템을 통해 캐릭터의 성장을 확인할 수 있기를 원한다. 그래야 전투와 탐험에서 전략적 선택을 할 수 있다.

#### 승인 기준

1. THE Player 모델은 6개의 1차 능력치(strength, dexterity, intelligence, wisdom, constitution, charisma)를 1-100 범위로 저장해야 한다
2. WHEN 플레이어가 stats 명령을 사용하면 THEN Command_Processor는 1차 능력치와 파생 스탯(HP, MP, ATK, DEF, SPD, max_carry_weight)을 계산하여 표시해야 한다
3. THE PlayerStats는 파생 스탯을 다음 공식으로 계산해야 한다: HP = 10 + (CON × 5) + (level × 2), MP = 50 + (INT × 3) + (WIS × 2) + (level × 5), ATK = 10 + (STR × 2) + level + 장비보너스, DEF = 2 + (CON × 0.3) + (level × 0.2) + 장비보너스, SPD = 10 + (DEX × 1.5), max_carry_weight = 50 + (STR × 5)
4. WHEN 장비를 장착하거나 해제하면 THEN PlayerStats는 equipment_bonuses를 갱신하고 파생 스탯을 재계산해야 한다
5. THE DnD_Engine은 ability_modifier를 (ability_score - 10) // 2 공식으로 계산해야 한다

### 요구사항 9: 채팅 시스템

**사용자 스토리:** 플레이어로서, 나는 다른 플레이어와 대화하고 소통할 수 있기를 원한다. 그래야 멀티플레이어 경험을 즐길 수 있다.

#### 승인 기준

1. WHEN 플레이어가 say 명령을 사용하면 THEN Command_Processor는 같은 방에 있는 모든 플레이어에게 메시지를 브로드캐스트해야 한다
2. WHEN 플레이어가 whisper 명령과 대상 플레이어 이름을 사용하면 THEN Command_Processor는 지정된 플레이어에게만 개인 메시지를 전송해야 한다
3. WHEN 플레이어가 who 명령을 사용하면 THEN Command_Processor는 현재 온라인인 모든 플레이어 목록을 표시해야 한다

### 요구사항 10: 명령어 시스템

**사용자 스토리:** 플레이어로서, 나는 텍스트 명령어를 입력하여 게임 세계와 상호작용할 수 있기를 원한다. 그래야 전통적인 MUD 경험을 즐길 수 있다.

#### 승인 기준

1. WHEN 플레이어가 명령어를 입력하면 THEN Command_Processor는 shlex 기반으로 명령어 이름과 인자를 파싱하고, 등록된 명령어 또는 별칭에서 해당 명령어를 조회하여 실행해야 한다
2. WHEN 전투 중 플레이어가 숫자를 입력하면 THEN Command_Processor는 해당 숫자를 명령어로 변환(1→attack, 2→defend, 3→flee, 4→item, 9→endturn)하여 처리해야 한다
3. WHEN 플레이어가 "." 을 입력하면 THEN Command_Processor는 이전에 실행한 명령어를 반복 실행해야 한다
4. IF 플레이어가 등록되지 않은 명령어를 입력하면 THEN Command_Processor는 플레이어의 locale에 맞는 도움말 메시지를 제공해야 한다
5. WHEN 관리자 전용 명령어가 실행되면 THEN Command_Processor는 session.player.is_admin 플래그를 확인하고, 관리자가 아니면 권한 부족 오류를 반환해야 한다
6. WHEN 전투 전용 명령어(defend, flee, item, endturn)가 전투 외 상황에서 실행되면 THEN Command_Processor는 전투 중에만 사용 가능하다는 오류를 반환해야 한다
7. WHEN 플레이어가 help 명령을 사용하면 THEN Command_Processor는 사용 가능한 명령어 목록을 관리자 여부에 따라 필터링하여 표시해야 한다
8. WHEN 플레이어가 quit(별칭: exit, logout) 명령을 사용하면 THEN Game_Engine은 플레이어 데이터를 저장하고, Event_Bus를 통해 PLAYER_LOGOUT 이벤트를 발행하며, 세션을 종료해야 한다

### 요구사항 11: 플레이어 상호작용 시스템

**사용자 스토리:** 플레이어로서, 나는 다른 플레이어에게 아이템을 주거나 따라갈 수 있기를 원한다. 그래야 협동 플레이를 즐길 수 있다.

#### 승인 기준

1. WHEN 플레이어가 give 명령을 사용하면 THEN Command_Processor는 같은 방의 다른 플레이어에게 아이템을 전달하고, Event_Bus를 통해 PLAYER_GIVE 이벤트를 발행해야 한다
2. WHEN 플레이어가 follow 명령을 사용하면 THEN Command_Processor는 대상 플레이어의 이동을 자동으로 따라가도록 설정하고, Event_Bus를 통해 PLAYER_FOLLOW 이벤트를 발행해야 한다
3. WHEN 따라가기 중인 플레이어가 연결을 끊으면 THEN Game_Engine은 따라가기 관련 정리 작업을 수행해야 한다
4. WHEN 플레이어가 players 명령을 사용하면 THEN Command_Processor는 같은 방에 있는 플레이어 목록을 표시해야 한다

### 요구사항 12: 관리자 도구

**사용자 스토리:** 게임 관리자로서, 나는 서버 재시작 없이 게임 세계를 실시간으로 구성하고 수정할 수 있기를 원한다. 그래야 게임 중단 없이 콘텐츠를 관리할 수 있다.

#### 승인 기준

1. WHEN 관리자가 createroom 명령을 사용하면 THEN World_Manager는 서버 재시작 없이 새 방을 생성하고 SQLite에 즉시 저장해야 한다
2. WHEN 관리자가 editroom 명령을 사용하면 THEN World_Manager는 방의 속성을 수정하고, 해당 방에 있는 모든 플레이어에게 변경사항을 실시간으로 반영해야 한다
3. WHEN 관리자가 createexit 명령을 사용하면 THEN World_Manager는 방 간 출구를 생성해야 한다
4. WHEN 관리자가 createobject 명령을 사용하면 THEN World_Manager는 지정된 위치에 새 GameObject를 즉시 생성해야 한다
5. WHEN 관리자가 goto 명령과 좌표(x, y)를 입력하면 THEN Game_Engine은 관리자를 해당 좌표의 방으로 즉시 이동시켜야 한다
6. WHEN 관리자가 spawn 명령을 사용하면 THEN Monster_Manager는 지정된 템플릿으로 몬스터를 현재 방에 즉시 스폰해야 한다
7. WHEN 관리자가 spawnitem 명령을 사용하면 THEN World_Manager는 지정된 아이템 템플릿으로 GameObject를 현재 방에 즉시 생성해야 한다
8. WHEN 관리자가 listtemplates 또는 listitemtemplates 명령을 사용하면 THEN Command_Processor는 사용 가능한 몬스터 또는 아이템 템플릿 목록을 표시해야 한다
9. WHEN 관리자가 roominfo 명령을 사용하면 THEN Command_Processor는 현재 방의 상세 정보(좌표, ID, 연결, 엔티티 목록)를 표시해야 한다
10. WHEN 관리자가 terminate 명령을 사용하면 THEN MUD_Server는 모든 플레이어에게 종료 알림을 전송하고 서버를 안전하게 종료해야 한다
11. WHEN 관리자가 scheduler 명령을 사용하면 THEN Game_Engine은 스케줄러의 상태를 확인하거나 관리할 수 있어야 한다

### 요구사항 13: NPC 및 상점 시스템

**사용자 스토리:** 플레이어로서, 나는 NPC와 대화하고 상점에서 아이템을 거래할 수 있기를 원한다. 그래야 게임 세계와 더 풍부하게 상호작용할 수 있다.

#### 승인 기준

1. WHEN 플레이어가 talk 명령과 NPC 번호를 입력하면 THEN Command_Processor는 해당 NPC의 대화 내용을 플레이어의 locale에 맞게 표시해야 한다
2. WHEN 플레이어가 trade 명령을 사용하면 THEN Command_Processor는 NPC와의 거래 인터페이스를 제공해야 한다
3. WHEN 플레이어가 shop 명령을 사용하면 THEN Command_Processor는 상점 NPC의 판매 아이템 목록과 가격을 표시해야 한다

### 요구사항 14: 퀘스트 시스템

**사용자 스토리:** 플레이어로서, 나는 퀘스트를 수락하고 목표를 달성하여 보상을 받을 수 있기를 원한다. 그래야 게임에 목표 의식을 가질 수 있다.

#### 승인 기준

1. THE Player 모델은 completed_quests(완료된 퀘스트 ID 목록)와 quest_progress(진행 중 퀘스트 상태) 필드를 JSON 형식으로 저장해야 한다
2. THE Quest_Manager는 퀘스트 타입(TUTORIAL, MAIN, SIDE, DAILY)을 지원하고, 각 퀘스트는 다국어 이름/설명, 레벨 요구사항, 선행 퀘스트, 목표 목록, 보상을 포함해야 한다
3. WHEN 퀘스트 목표가 달성되면 THEN Quest_Manager는 해당 objective의 current_count를 증가시키고, 모든 objective가 완료되면 퀘스트를 completed_quests에 추가해야 한다
4. WHEN 플레이어가 퀘스트 관련 행동(몬스터 처치, 아이템 수집, NPC 대화, 장소 방문)을 수행하면 THEN Quest_Manager는 해당 행동이 진행 중인 퀘스트의 목표와 일치하는지 확인하고 진행도를 갱신해야 한다
5. WHEN 퀘스트가 완료되면 THEN Quest_Manager는 보상(경험치, 골드, 아이템, 장비)을 플레이어에게 지급해야 한다
6. THE Quest_Manager는 퀘스트 시작 가능 여부를 레벨 요구사항과 선행 퀘스트 완료 여부로 판단해야 한다

### 요구사항 15: 다국어 지원 시스템

**사용자 스토리:** 플레이어로서, 나는 내가 선호하는 언어(영어 또는 한국어)로 게임을 플레이할 수 있기를 원한다. 그래야 더 편안하게 게임을 즐길 수 있다.

#### 승인 기준

1. WHEN 플레이어가 로그인하면 THEN Telnet_Session은 Player의 preferred_locale("en" 또는 "ko")을 로드하여 세션 언어를 설정해야 한다
2. WHEN 플레이어가 language 명령을 사용하면 THEN Command_Processor는 preferred_locale을 변경하고 즉시 새로운 언어로 인터페이스를 업데이트해야 한다
3. WHEN 방 정보를 표시할 때 THEN Telnet_Session은 Room의 description 딕셔너리에서 현재 locale에 해당하는 설명을 선택하여 표시해야 한다
4. WHEN 몬스터 또는 오브젝트 정보를 표시할 때 THEN Telnet_Session은 해당 엔티티의 name/description 딕셔너리에서 현재 locale에 해당하는 텍스트를 선택하여 표시해야 한다
5. THE Localization_Manager는 JSON 파일(data/translations/)에서 카테고리별(auth, combat, command, item, moving, status, system) 메시지를 로드하고, 변수 치환({variable} 형식)을 지원해야 한다
6. THE 데이터베이스의 모든 다국어 텍스트 필드는 name_en/name_ko, description_en/description_ko 형식으로 저장되어야 한다

### 요구사항 16: 이벤트 시스템

**사용자 스토리:** 시스템 개발자로서, 나는 컴포넌트 간 결합도를 최소화하는 이벤트 기반 아키텍처를 원한다. 그래야 시스템을 유지보수하고 확장할 수 있다.

#### 승인 기준

1. THE Event_Bus는 비동기 큐 기반으로 이벤트를 발행하고, 구독된 콜백을 실행해야 한다
2. WHEN 이벤트가 발행되면 THEN Event_Bus는 해당 EventType에 구독된 모든 콜백을 비동기적으로 실행해야 한다
3. THE Event_Bus는 다음 이벤트 타입을 지원해야 한다: PLAYER_CONNECTED, PLAYER_DISCONNECTED, PLAYER_LOGIN, PLAYER_LOGOUT, PLAYER_MOVED, PLAYER_COMMAND, ROOM_ENTERED, ROOM_LEFT, ROOM_MESSAGE, ROOM_BROADCAST, WORLD_UPDATED, OBJECT_CREATED, OBJECT_DESTROYED, OBJECT_MOVED, OBJECT_INTERACTED, OBJECT_PICKED_UP, OBJECT_DROPPED, PLAYER_ACTION, PLAYER_EMOTE, PLAYER_GIVE, PLAYER_TRADE, PLAYER_FOLLOW, PLAYER_STATUS_CHANGED, SERVER_STARTED, SERVER_STOPPING, SERVER_STOPPED
4. WHEN 서버가 시작되면 THEN Event_Bus는 start()를 통해 이벤트 처리 루프를 시작해야 하고, 서버 종료 시 stop()을 통해 안전하게 종료해야 한다
5. THE Event_Bus는 이벤트 히스토리를 최대 1000개까지 보관하고, 통계 정보(구독자 수, 이벤트 타입별 카운트, 큐 크기)를 제공해야 한다

### 요구사항 17: 데이터 지속성 (SQLite)

**사용자 스토리:** 시스템 관리자로서, 나는 모든 게임 데이터가 SQLite 데이터베이스에 안전하게 저장되기를 원한다. 그래야 데이터 무결성을 보장하고 쉽게 백업할 수 있다.

#### 승인 기준

1. WHEN 시스템이 시작되면 THEN Game_Engine은 SQLite 데이터베이스 파일(data/mud_engine.db)을 로드하거나, 존재하지 않으면 스키마에 따라 테이블(players, rooms, monsters, game_objects, room_connections, factions, faction_relations)을 생성해야 한다
2. WHEN 플레이어 데이터가 변경되면(위치 이동, 능력치 변경, 장비 변경, 퀘스트 진행) THEN Player_Manager는 변경사항을 SQLite에 즉시 저장해야 한다
3. WHEN 게임 세계 데이터가 변경되면(방 생성, 오브젝트 이동, 몬스터 상태 변경) THEN World_Manager는 변경사항을 SQLite에 트랜잭션으로 안전하게 저장해야 한다
4. WHEN 시스템이 종료되면 THEN Game_Engine은 모든 활성 플레이어의 데이터를 SQLite에 저장하고 데이터베이스 연결을 안전하게 종료해야 한다
5. IF 데이터베이스 오류가 발생하면 THEN Game_Engine은 오류를 로그에 기록하고 데이터 손실을 방지해야 한다
6. THE 데이터베이스는 SQLite WAL 모드를 사용하여 읽기/쓰기 동시성을 향상시켜야 한다
7. THE 모든 데이터베이스 접근은 리포지토리 패턴(RoomRepository, GameObjectRepository, MonsterRepository, PlayerRepository)을 통해 추상화되어야 한다

### 요구사항 18: Telnet 프로토콜 및 ANSI 색상 UI 렌더링

**사용자 스토리:** 플레이어로서, 나는 ANSI 색상이 적용된 가독성 높은 텍스트 인터페이스로 게임을 플레이할 수 있기를 원한다. 그래야 전통적인 MUD 경험을 즐길 수 있다.

#### 승인 기준

1. WHEN Telnet_Session이 메시지를 전송할 때 THEN Telnet_Session은 메시지 딕셔너리를 ANSI 색상 코드가 적용된 텍스트로 포맷팅해야 한다
2. WHEN 방 정보를 렌더링할 때 THEN Telnet_Session은 엔티티 번호 매핑(몬스터, 오브젝트, 플레이어에 순차 번호 부여)을 포함하고, 시간대(낮/밤) 정보를 표시해야 한다
3. WHEN 비밀번호 입력을 요구할 때 THEN Telnet_Session은 IAC WILL ECHO Telnet 명령으로 에코를 비활성화하고, 입력 완료 후 IAC WONT ECHO로 에코를 복원해야 한다
4. WHEN 플레이어가 바이트 단위 입력을 할 때 THEN Telnet_Session은 백스페이스 처리, Telnet IAC 명령어 필터링, CR/LF 줄바꿈 처리를 수행해야 한다
5. WHEN 플레이어가 300초 동안 비활성 상태이면 THEN Telnet_Session은 세션 타임아웃으로 연결을 종료해야 한다
6. THE ANSI_Colors 유틸리티는 오류(빨간색), 성공(녹색), 정보(청록색), 아이템(노란색), 플레이어(파란색), 몬스터(빨간색), NPC(녹색), 중립(노란색), 출구 방향 등 엔티티 타입별 색상을 제공해야 한다

### 요구사항 19: 플레이어 표시 이름 시스템

**사용자 스토리:** 플레이어로서, 나는 게임 내 표시 이름을 변경할 수 있기를 원한다. 그래야 원하는 이름으로 다른 플레이어에게 보여질 수 있다.

#### 승인 기준

1. WHEN 플레이어가 changename 명령과 새 이름을 입력하면 THEN Command_Processor는 이름 형식(한글/영문/숫자, 3-20자, 공백 불가)을 검증하고, 유효하면 display_name을 변경해야 한다
2. WHEN 플레이어가 24시간 이내에 이름을 재변경하려 하면 THEN Command_Processor는 다음 변경까지 남은 시간을 안내하고 변경을 거부해야 한다
3. WHEN 관리자가 adminchangename 명령을 사용하면 THEN Command_Processor는 24시간 제한 없이 대상 플레이어의 이름을 즉시 변경해야 한다
4. WHEN display_name이 설정되지 않은 플레이어의 이름을 표시할 때 THEN Player 모델은 username을 기본 표시 이름으로 반환해야 한다

### 요구사항 20: 보안

**사용자 스토리:** 시스템 관리자로서, 나는 플레이어 계정과 서버가 안전하게 보호되기를 원한다. 그래야 악의적인 접근을 방지할 수 있다.

#### 승인 기준

1. THE Player_Manager는 모든 비밀번호를 bcrypt로 해싱하여 저장해야 한다
2. THE MUD_Server는 사용자명을 정규식(^[a-zA-Z0-9_]+$, 3-20자)으로 검증하여 인젝션을 방지해야 한다
3. WHEN 로그인 시도가 3회 연속 실패하면 THEN MUD_Server는 해당 연결을 종료해야 한다
4. THE Command_Processor는 관리자 전용 명령어 실행 시 session.player.is_admin 플래그를 검증해야 한다
5. WHEN Telnet_Session이 비밀번호 입력을 처리할 때 THEN Telnet_Session은 IAC WILL ECHO로 클라이언트 에코를 비활성화하여 비밀번호가 화면에 표시되지 않도록 해야 한다

### 요구사항 21: 로깅 및 모니터링

**사용자 스토리:** 시스템 관리자로서, 나는 서버의 동작 상태를 구조화된 로그로 모니터링할 수 있기를 원한다. 그래야 문제를 신속하게 진단하고 해결할 수 있다.

#### 승인 기준

1. THE 모든 모듈은 Python 표준 logging 모듈을 사용하고, 로그 포맷은 `{시분초.ms} {LEVEL} [{filename.py:line}] {logstring}` 형식을 따라야 한다
2. THE 로그 파일은 `logs/mud_engine-{YYYYMMDD}-{no}.log` 형식으로 생성되고, 200MB 크기 제한 또는 날짜 변경 시 로테이션되어야 한다
3. WHEN 플레이어가 로그인/로그아웃하면 THEN Game_Engine은 INFO 레벨로 해당 이벤트를 기록해야 한다
4. WHEN 명령어 실행 중 오류가 발생하면 THEN Command_Processor는 ERROR 레벨로 오류 내용과 스택 트레이스를 기록해야 한다
5. WHEN 데이터베이스 오류가 발생하면 THEN 리포지토리 계층은 ERROR 레벨로 쿼리 정보와 오류 내용을 기록해야 한다
6. THE 로그에는 민감한 정보(비밀번호, 토큰)가 포함되지 않아야 한다
7. THE 로테이트된 과거 로그 파일은 gzip으로 압축되어야 한다
