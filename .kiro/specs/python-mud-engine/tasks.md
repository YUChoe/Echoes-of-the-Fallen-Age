# 구현 계획

## 완료된 작업

- [x] 1. Telnet 서버 및 세션 관리 (요구사항 1)
  - [x] 1.1 TelnetServer: asyncio 기반 TCP 서버 (포트 4000)
  - [x] 1.2 TelnetSession: Telnet 프로토콜 처리, ANSI 색상 렌더링
  - [x] 1.3 SessionManager: 세션 생명주기 관리, 중복 로그인 감지
  - [x] 1.4 비활성 세션 60초 간격 정리

- [x] 2. 인증 시스템 (요구사항 2)
  - [x] 2.1 로그인/회원가입 메뉴 시스템
  - [x] 2.2 bcrypt 비밀번호 해싱 및 검증
  - [x] 2.3 Telnet ECHO 비활성화 (비밀번호 입력)
  - [x] 2.4 중복 로그인 감지 및 기존 세션 종료
  - [x] 2.5 로그인 실패 3회 제한
  - [x] 2.6 전투 복귀 (try_rejoin_combat)

- [x] 3. 좌표 기반 월드 이동 시스템 (요구사항 3)
  - [x] 3.1 좌표 기반 방향 이동 (north/south/east/west)
  - [x] 3.2 방 정보 표시 (다국어 설명, 출구, 엔티티)
  - [x] 3.3 look 명령어 (엔티티 번호 매핑)
  - [x] 3.4 enter 명령어 (room_connections 기반 특별 이동)
  - [x] 3.5 이동 이벤트 발행 (ROOM_LEFT, ROOM_ENTERED)

- [x] 4. D&D 5e 기반 전투 시스템 (요구사항 4)
  - [x] 4.1 DnDCombatEngine: d20 굴림, 공격 판정, 데미지 계산
  - [x] 4.2 CombatInstance: 인스턴스 기반 턴제 전투
  - [x] 4.3 CombatManager: 전투 인스턴스 생성/관리
  - [x] 4.4 CombatHandler: 공격/방어/도주/턴종료 처리
  - [x] 4.5 DEX 기반 선공 판정 (턴 순서)
  - [x] 4.6 크리티컬 히트 (d20=20) / 자동 실패 (d20=1)
  - [x] 4.7 GlobalTickManager: 3초 간격 몬스터 턴 처리
  - [x] 4.8 전투 중 연결 끊김/재접속 처리
  - [x] 4.9 전투 타임아웃 (2분, 15초 간격 tick)
  - [x] 4.10 몬스터 사망 시 corpse 컨테이너 생성

- [x] 5. 몬스터 스폰, 로밍, 리스폰 시스템 (요구사항 5)
  - [x] 5.1 SpawnScheduler: 30초 간격 스폰/리스폰/로밍 루프
  - [x] 5.2 템플릿 기반 몬스터 생성
  - [x] 5.3 글로벌 스폰 제한 + 방별 스폰 제한
  - [x] 5.4 로밍 시스템 (roaming_area 범위 내 이동)
  - [x] 5.5 리스폰 시스템 (respawn_time 경과 후)
  - [x] 5.6 선공 몬스터 자동 전투 시작 (GlobalTickManager)

- [x] 6. 세력(Faction) 시스템 (요구사항 6)
  - [x] 6.1 factions/faction_relations 테이블 및 모델
  - [x] 6.2 세력 기반 몬스터 분류 (우호/중립/적대)
  - [x] 6.3 플레이어 기본 세력 (ash_knights)

- [x] 7. 아이템, 장비, 컨테이너 시스템 (요구사항 7)
  - [x] 7.1 get/drop/inventory 명령어
  - [x] 7.2 equip/unequip/unequipall 명령어
  - [x] 7.3 장비 슬롯 시스템 (HEAD, BODY, WEAPON 등)
  - [x] 7.4 스택 시스템 (max_stack)
  - [x] 7.5 무게 시스템 (STR 기반 소지 용량)
  - [x] 7.6 컨테이너 시스템 (open, put)
  - [x] 7.7 아이템 템플릿 시스템 (ItemTemplateManager)
  - [x] 7.8 use 명령어

- [x] 8. 능력치 시스템 (요구사항 8)
  - [x] 8.1 D&D 6스탯 (STR/DEX/INT/WIS/CON/CHA)
  - [x] 8.2 파생 스탯 계산 (HP, MP, ATK, DEF, SPD)
  - [x] 8.3 장비 보너스 반영
  - [x] 8.4 stats 명령어

- [x] 9. 채팅 시스템 (요구사항 9)
  - [x] 9.1 say 명령어 (같은 방 브로드캐스트)
  - [x] 9.2 whisper 명령어 (개인 메시지)
  - [x] 9.3 who 명령어 (온라인 플레이어 목록)

- [x] 10. 명령어 시스템 (요구사항 10)
  - [x] 10.1 CommandProcessor: shlex 기반 파싱
  - [x] 10.2 명령어 별칭 시스템
  - [x] 10.3 전투 중 숫자 입력 변환
  - [x] 10.4 "." 이전 명령어 반복
  - [x] 10.5 관리자 권한 검증
  - [x] 10.6 전투 전용 명령어 동적 생성
  - [x] 10.7 help 명령어

- [x] 11. 플레이어 상호작용 시스템 (요구사항 11)
  - [x] 11.1 give 명령어
  - [x] 11.2 follow 명령어
  - [x] 11.3 players 명령어

- [x] 12. 관리자 도구 (요구사항 12)
  - [x] 12.1 createroom/editroom/createexit/createobject
  - [x] 12.2 goto (좌표 이동)
  - [x] 12.3 spawn/spawnitem
  - [x] 12.4 listtemplates/listitemtemplates
  - [x] 12.5 roominfo
  - [x] 12.6 terminate
  - [x] 12.7 scheduler

- [x] 13. NPC 및 상점 시스템 (요구사항 13)
  - [x] 13.1 talk 명령어
  - [x] 13.2 trade 명령어
  - [x] 13.3 shop 명령어

- [x] 14. 퀘스트 시스템 (요구사항 14)
  - [x] 14.1 QuestManager: 퀘스트 정의 및 관리
  - [x] 14.2 퀘스트 타입 (TUTORIAL, MAIN, SIDE, DAILY)
  - [x] 14.3 목표 추적 (collect, kill, talk, visit)
  - [x] 14.4 보상 시스템 (경험치, 골드, 아이템)

- [x] 15. 다국어 지원 시스템 (요구사항 15)
  - [x] 15.1 영어/한국어 지원 (en/ko)
  - [x] 15.2 language 명령어
  - [x] 15.3 LocalizationManager: JSON 기반 메시지 관리
  - [x] 15.4 DB 다국어 필드 (name_en/name_ko)

- [x] 16. 이벤트 시스템 (요구사항 16)
  - [x] 16.1 EventBus: 비동기 이벤트 발행/구독
  - [x] 16.2 EventHandler: 이벤트 콜백 처리
  - [x] 16.3 이벤트 타입 정의

- [x] 17. 데이터 지속성 (요구사항 17)
  - [x] 17.1 SQLite WAL 모드
  - [x] 17.2 리포지토리 패턴 (Room/GameObject/Monster/Player)
  - [x] 17.3 스키마 정의 및 마이그레이션
  - [x] 17.4 트랜잭션 기반 데이터 저장

- [x] 18. Telnet 프로토콜 및 ANSI 색상 (요구사항 18)
  - [x] 18.1 ANSI 색상 코드 유틸리티
  - [x] 18.2 엔티티 번호 매핑 렌더링
  - [x] 18.3 Telnet IAC 명령어 처리
  - [x] 18.4 바이트 단위 입력 처리
  - [x] 18.5 세션 타임아웃 (300초)

- [x] 19. 플레이어 표시 이름 시스템 (요구사항 19)
  - [x] 19.1 changename 명령어 (24시간 제한)
  - [x] 19.2 adminchangename 명령어
  - [x] 19.3 display_name 기본값 (username)

- [x] 20. 보안 (요구사항 20)
  - [x] 20.1 bcrypt 비밀번호 해싱
  - [x] 20.2 사용자명 정규식 검증
  - [x] 20.3 로그인 3회 실패 제한
  - [x] 20.4 관리자 권한 검증
  - [x] 20.5 비밀번호 에코 비활성화

- [x] 21. 로깅 및 모니터링 (요구사항 21)
  - [x] 21.1 구조화된 로그 포맷
  - [x] 21.2 로그 파일 로테이션 (200MB/날짜)
  - [x] 21.3 이벤트 로깅 (로그인/로그아웃)
  - [x] 21.4 오류 로깅 (스택 트레이스)

## 향후 작업

- [-] 25. 다국어 시스템 고도화
  - [x] 25.1 전투/컨테이너 locale TODO 해결 (combat.py, combat_commands.py, container_commands.py)
  - [x] 25.2 관리자 명령어 응답 다국어화 (admin_commands.py → admin.json 70키)
  - [x] 25.3 object_commands.py 한국어 하드코딩 → i18n 키 전환 (item.json 20키 추가)
  - [x] 25.4 npc/talk_command.py i18n 전환 (퀘스트 대화/안내 메시지 약 40곳)
  - [x] 25.5 npc/trade_command.py i18n 전환 (거래 메시지 약 15곳)
  - [x] 25.6 npc/shop_command.py i18n 전환 (상점 메시지 약 30곳)
  - [x] 25.7 combat_handler.py 공격 결과 메시지 i18n 전환 (명중/빗나감/데미지/사망/시체 생성 약 10곳)
  - [x] 25.8 telnet_session.py 방 정보 렌더링 폴백 텍스트 i18n 전환 (약 7곳)
  - [ ] 25.9 전투 broadcast를 참가자별 locale로 개별 전송 (combat_handler._execute_attack 등)

- [ ] 26. 품질 개선
  - [ ] 26.1 단위 테스트 작성 (PlayerStats, DnDCombatEngine, CommandProcessor)
  - [ ] 26.2 속성 기반 테스트 (hypothesis 라이브러리)
  - [ ] 26.3 통합 테스트 (Telnet 연결 → 로그인 → 전투 → 로그아웃)

- [ ] 27. 성능 최적화
  - [ ] 27.1 자주 접근하는 방 데이터 캐싱
  - [ ] 27.2 전투 인스턴스 메모리 관리 최적화
  - [ ] 27.3 대규모 동시 접속 부하 테스트

- [ ] 28. 배포 준비
  - [ ] 28.1 Docker 컨테이너화
  - [ ] 28.2 설정 파일 외부화 (포트, DB 경로 등)
  - [ ] 28.3 운영 문서 작성

- [ ] 29. 파일 분리 리팩토링 (한 파일 한 클래스 원칙)
  - [x] 29.1 admin_commands.py → 클래스별 파일 분리 (14 클래스)
  - [x] 29.2 combat_commands.py → 클래스별 파일 분리 (5 클래스)
  - [x] 29.3 interaction_commands.py → 클래스별 파일 분리 (4 클래스)
  - [x] 29.4 npc_commands.py → 클래스별 파일 분리 (3 클래스)
  - [x] 29.5 combat.py → CombatManager 분리 (enum/dataclass는 유지)
  - [x] 29.6 repositories.py → 리포지토리별 파일 분리 (5 클래스)
