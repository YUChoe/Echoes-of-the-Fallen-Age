# 구현 계획: WorldView 기반 NPC 배치

## 개요

잿빛 항구(Greyhaven Port) 세계관에 기반하여 14개 NPC를 게임에 배치한다. 코드 변경 없이 데이터(DB INSERT + Lua 대화 스크립트)만 추가하는 방식이다. NPC_Init_Script(Python)로 monsters/game_objects 테이블에 INSERT하고, 각 NPC별 Lua 대화 스크립트를 configs/dialogues/{uuid}.lua에 생성한다.

## Tasks

- [x] 1. NPC_Init_Script 작성 (scripts/init_worldview_npcs.py)
  - [x] 1.1 14개 NPC의 UUID 상수 정의 및 NPC 데이터 목록 작성
    - 각 NPC별 사전 생성된 UUID를 상수로 정의
    - NPC별 name_en, name_ko, description_en, description_ko, monster_type, behavior, stats, faction_id, x, y, properties 데이터 정의
    - 모든 NPC의 faction_id는 ash_knights
    - 모든 비전투 NPC: respawn_time=0, aggro_range=0, roaming_range=0, is_alive=TRUE, drop_items=[]
    - 영어 텍스트는 영국 영어(British English) 사용
    - _요구사항: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 5.1, 5.2, 6.1, 6.2, 7.1, 7.2, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_
  - [x] 1.2 monsters 테이블 INSERT 로직 구현 (멱등성 보장)
    - 각 NPC에 대해 SELECT로 존재 여부 확인 후 INSERT
    - 이미 존재하면 SKIP 로그 출력
    - INSERT 실패 시 에러 로그 출력 후 다음 NPC 진행
    - DB 연결 실패 시 exit(1)
    - _요구사항: 8.7_
  - [x] 1.3 거래 NPC(Smuggler) 전용 game_objects INSERT 로직 구현
    - Smuggler의 properties에 exchange_config 블록 포함 (initial_silver: 300, buy_margin: 0.4)
    - game_objects 테이블에 silver_coin 스택 INSERT (location_type=INVENTORY, location_id=smuggler_uuid)
    - game_objects 테이블에 판매 아이템(rope, torch 등) INSERT
    - 멱등성 보장: 이미 존재하면 SKIP
    - _요구사항: 7.5, 10.2_
  - [x] 1.4 스크립트 실행 및 멱등성 검증
    - `./script_test.sh init_worldview_npcs` 로 첫 실행 → 14개 NPC INSERT 확인
    - 두 번째 실행 → 14개 NPC 모두 SKIP 확인
    - _요구사항: 8.7_

- [x] 2. 잿빛 기사단 구역 Lua 대화 스크립트 작성 (2개)
  - [x] 2.1 Knight Lieutenant (기사단 부관) 대화 스크립트 작성
    - configs/dialogues/{knight_lieutenant_uuid}.lua 생성
    - get_dialogue(ctx), on_choice(choice_number, ctx) 구현
    - 대화 내용: 기사단 조직, 고블린 위협, 성벽 안 수풀의 고블린 소탕 계획
    - text/choices에 en/ko Locale_Dict 형식 사용, en은 영국 영어
    - 대화 종료 시 on_choice에서 nil 반환
    - 3914fbe8...lua (Veteran Guard) 패턴 준수
    - _요구사항: 1.3, 1.5, 9.1, 9.2, 9.3, 9.4, 9.5, 11.1_
  - [x] 2.2 Knight Recruiter (기사단 모병관) 대화 스크립트 작성
    - configs/dialogues/{knight_recruiter_uuid}.lua 생성
    - 대화 내용: 기사단 입단 권유, 성벽 안팎 상황, 기사단의 정의와 잔혹한 질서
    - _요구사항: 1.4, 1.6, 9.1, 9.2, 9.3, 9.4, 9.5, 11.1_

- [x] 3. 술집 구역 Lua 대화 스크립트 작성 (2개)
  - [x] 3.1 Drunken Refugee (술에 취한 난민) 대화 스크립트 작성
    - configs/dialogues/{drunken_refugee_uuid}.lua 생성
    - 대화 내용: 대마법사 소문, 원정 패배, 가족 그리움, 밝고 거대한 빛
    - 마법을 믿지 않는 세계관 반영
    - _요구사항: 2.3, 2.5, 9.1, 9.2, 9.3, 9.4, 9.5, 11.2, 11.7_
  - [x] 3.2 Wandering Bard (떠돌이 음유시인) 대화 스크립트 작성
    - configs/dialogues/{wandering_bard_uuid}.lua 생성
    - 대화 내용: 황금의 시대, 제국 몰락, 현재 상황, 대마법사 출현 이후 변화
    - _요구사항: 2.4, 2.6, 9.1, 9.2, 9.3, 9.4, 9.5, 11.2_

- [x] 4. 교회 구역 Lua 대화 스크립트 작성 (2개)
  - [x] 4.1 Priest (사제) 대화 스크립트 작성
    - configs/dialogues/{priest_uuid}.lua 생성
    - 대화 내용: 잊혀진 신들, 네크로폴리스 경고, 교회 지하의 위험
    - _요구사항: 3.3, 3.5, 9.1, 9.2, 9.3, 9.4, 9.5, 11.3_
  - [x] 4.2 Crypt Guard Monk (교회 지하 입구 경비 수도사) 대화 스크립트 작성
    - configs/dialogues/{crypt_guard_monk_uuid}.lua 생성
    - 대화 내용: 지하 위험 경고, 접근 제한, 네크로폴리스
    - _요구사항: 3.4, 3.6, 9.1, 9.2, 9.3, 9.4, 9.5, 11.3_

- [x] 5. 성문 구역 Lua 대화 스크립트 작성 (2개)
  - [x] 5.1 Gate Warden (성문 관리인) 대화 스크립트 작성
    - configs/dialogues/{gate_warden_uuid}.lua 생성
    - 대화 내용: 성벽 너머 상황, 이주 명령, 괴물 출몰
    - _요구사항: 4.3, 4.5, 9.1, 9.2, 9.3, 9.4, 9.5, 11.4_
  - [x] 5.2 Refugee (난민) 대화 스크립트 작성
    - configs/dialogues/{refugee_uuid}.lua 생성
    - 대화 내용: 가족 생사 불명, 절박한 분위기, 성 안으로 들어가고 싶은 심정
    - _요구사항: 4.4, 4.6, 9.1, 9.2, 9.3, 9.4, 9.5, 11.4_

- [x] 6. 성벽 밖 구역 Lua 대화 스크립트 작성 (2개)
  - [x] 6.1 Disgruntled Farmer (불만 가득한 농부) 대화 스크립트 작성
    - configs/dialogues/{disgruntled_farmer_uuid}.lua 생성
    - 대화 내용: 이주 명령 분노, 성 안 사람들에 대한 적대감, 농작물 피해
    - _요구사항: 5.3, 5.5, 9.1, 9.2, 9.3, 9.4, 9.5, 11.4_
  - [x] 6.2 Former Merchant (전직 상인) 대화 스크립트 작성
    - configs/dialogues/{former_merchant_uuid}.lua 생성
    - 대화 내용: 약탈 경험, 상인에서 도적으로 변해가는 세상, 사회 질서 붕괴
    - _요구사항: 5.4, 5.6, 9.1, 9.2, 9.3, 9.4, 9.5, 11.4_

- [x] 7. 성(Castle) 구역 Lua 대화 스크립트 작성 (2개)
  - [x] 7.1 Royal Adviser (왕의 조언자) 대화 스크립트 작성
    - configs/dialogues/{royal_adviser_uuid}.lua 생성
    - 대화 내용: 정치 상황, 왕위 계승 위기, 동생과 아들 행방불명
    - _요구사항: 6.3, 6.5, 9.1, 9.2, 9.3, 9.4, 9.5, 11.5_
  - [x] 7.2 Royal Guard (왕실 경비병) 대화 스크립트 작성
    - configs/dialogues/{royal_guard_uuid}.lua 생성
    - 대화 내용: 성 접근 제한, 엄격한 경비, 왕실 보호
    - _요구사항: 6.4, 6.6, 9.1, 9.2, 9.3, 9.4, 9.5, 11.5_

- [x] 8. 항구 구역 Lua 대화 스크립트 작성 (2개)
  - [x] 8.1 Fisherman (어부) 대화 스크립트 작성
    - configs/dialogues/{fisherman_uuid}.lua 생성
    - 대화 내용: 바다, 북쪽 절벽, 좁은 선착장, 남쪽 폐허 잔교
    - _요구사항: 7.3, 7.6, 9.1, 9.2, 9.3, 9.4, 9.5, 11.6_
  - [x] 8.2 Smuggler (밀수업자) 거래 대화 스크립트 작성
    - configs/dialogues/{smuggler_uuid}.lua 생성
    - merchant_sample.lua 패턴 사용: get_dialogue, on_choice, show_buy_menu, show_sell_menu, handle_buy, handle_sell
    - 선택지 번호 규칙: 1-99 메뉴 탐색, 101-199 구매, 201-299 판매
    - exchange.buy_from_npc(), exchange.sell_to_npc() API 사용
    - 거래 실패 시 Locale_Dict 형식 에러 메시지 (insufficient_silver, weight_exceeded, npc_insufficient_silver)
    - 숨겨진 거래 분위기의 대화 텍스트
    - _요구사항: 7.4, 7.7, 9.1, 9.2, 9.3, 9.4, 9.5, 10.1, 10.2, 10.3, 10.4, 10.5, 11.6_

- [x] 9. 체크포인트 - NPC_Init_Script 실행 및 Lua 스크립트 확인
  - `./script_test.sh init_worldview_npcs` 실행하여 14개 NPC DB 등록 확인
  - 14개 Lua 파일이 configs/dialogues/ 에 모두 존재하는지 확인
  - 모든 테스트 통과 확인, 문제 발생 시 사용자에게 질문

- [ ] 10. 검증 스크립트 작성 (scripts/verify_worldview_npcs.py)
  - [ ] 10.1 데이터 정합성 검증 로직 구현
    - 14개 NPC가 monsters 테이블에 모두 존재하는지 확인
    - 각 NPC의 필수 컬럼(name_en, name_ko, description_en, description_ko, x, y, faction_id) 검증
    - 각 NPC UUID에 대응하는 Lua 파일이 configs/dialogues/ 에 존재하는지 확인
    - Smuggler의 exchange_config가 properties에 포함되어 있는지 확인
    - Smuggler의 game_objects(silver_coin, 판매 아이템)가 존재하는지 확인
    - 검증 결과를 요약 출력 (통과/실패 건수)
    - _요구사항: 8.1, 8.2, 8.3, 8.4, 7.5_
  - [ ] 10.2 검증 스크립트 실행 및 결과 확인
    - `./script_test.sh verify_worldview_npcs` 실행
    - 모든 검증 항목 통과 확인
    - _요구사항: 8.1, 8.2, 8.3, 8.4_

- [ ] 11. Telnet E2E 테스트
  - [ ] 11.1 일반 NPC 대화 테스트 (Telnet MCP 사용)
    - 서버 실행 후 관리자 계정(player5426)으로 로그인
    - goto 명령어로 각 NPC 위치 이동
    - look 명령어로 NPC 존재 확인
    - talk {npc_name} 명령어로 대화 시작
    - 대화 선택지 탐색 및 응답 확인 (en/ko 모두)
    - 구역별 최소 1개 NPC 대화 테스트
    - _요구사항: 1.3, 1.4, 2.3, 2.4, 3.3, 3.4, 4.3, 4.4, 5.3, 5.4, 6.3, 6.4, 7.3, 11.1~11.7_
  - [ ] 11.2 거래 NPC(Smuggler) 대화 및 거래 테스트
    - goto 명령어로 항구(0,7) 이동
    - talk smuggler로 대화 시작
    - 구매/판매 메뉴 진입 확인
    - 거래 시도 및 에러 메시지 확인
    - _요구사항: 7.4, 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ] 12. 최종 체크포인트
  - 모든 테스트 통과 확인, 문제 발생 시 사용자에게 질문

## 참고사항

- 이 기능은 코드 변경 없이 데이터(DB INSERT + config 파일)만 추가하는 작업이므로 Property-Based Testing은 적용하지 않음
- 각 태스크는 이전 태스크의 결과물에 의존함 (특히 태스크 1의 UUID 상수를 태스크 2~8에서 참조)
- Lua 파일명은 반드시 NPC의 UUID와 일치해야 함 (configs/dialogues/{uuid}.lua)
- 모든 영어 텍스트는 영국 영어(British English) 사용
- 체크포인트에서 문제 발생 시 사용자에게 질문
