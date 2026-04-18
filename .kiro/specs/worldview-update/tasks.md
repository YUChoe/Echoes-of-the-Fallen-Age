# 구현 계획: 세계관 업데이트 반영 (worldview-update)

## 개요

수정된 WorldView.md에 맞춰 기존 NPC/아이템의 대화 및 설명을 수정하고, 신규 NPC/아이템/방을 추가한다. 모든 작업은 코드 변경 없이 데이터(DB + Lua + JSON)만 수정/추가하는 방식으로 진행한다. Python Init_Script, Lua 대화 스크립트, JSON 아이템 템플릿 세 가지 데이터 레이어를 대상으로 한다.

## Tasks

- [ ] 1. Init_Script 작성 — scripts/update_worldview.py
  - [ ] 1.1 기존 NPC UPDATE 로직 구현
    - Crypt Guard Monk(b2f6d7a8-...)의 name_en/name_ko/description_en/description_ko UPDATE
    - Brother Marcus(3914fbe8-...)의 description_en/description_ko UPDATE (예배당 수도승 역할)
    - 멱등성 보장: UPDATE 문은 동일 값 재실행 시 결과 동일
    - _요구사항: 2.3, 3.4, 15.1, 15.2_

  - [ ] 1.2 신규 NPC INSERT 로직 구현
    - 마을 술집 주인(고정 UUID, 좌표 -16,0, faction_id=ash_knights) INSERT
    - 자경단원(고정 UUID, 좌표 -16,0, faction_id=ash_knights) INSERT
    - 쓰레기장 떠돌이(고정 UUID, 좌표 -12,1, faction_id=ash_knights) INSERT
    - 멱등성 보장: SELECT 존재 여부 확인 후 INSERT (이미 존재하면 SKIP)
    - _요구사항: 8.1, 8.5, 9.1, 9.5, 10.1, 10.5, 15.1, 15.2_

  - [ ] 1.3 신규 방 INSERT 로직 구현
    - 돌 제단 방(고정 UUID, 좌표 -20,0) INSERT
    - description_en/ko에 30cm 두께 돌바닥 + 작은 상 구조 묘사
    - 영어 텍스트는 영국 영어(British English)
    - 멱등성 보장: 동일 좌표 존재 여부 확인 후 INSERT
    - _요구사항: 14.1, 14.2, 14.3, 14.4, 15.1_

  - [ ] 1.4 에러 처리 및 멱등성 검증
    - DB 연결 실패 시 에러 메시지 출력 + exit code 1
    - 개별 UPDATE/INSERT 실패 시 에러 로그 출력 + 다음 작업 진행
    - `./script_test.sh update_worldview` 2회 연속 실행 시 동일 DB 상태 유지 확인
    - _요구사항: 15.3, 15.4, 15.5_

- [ ] 2. 체크포인트 — Init_Script 검증
  - `./script_test.sh update_worldview` 실행하여 모든 UPDATE/INSERT 정상 처리 확인
  - 2회차 실행 시 모든 항목이 SKIP 처리되는지 확인
  - 문제 발생 시 사용자에게 질문

- [ ] 3. Lua 대화 스크립트 수정 — 기존 NPC 5건
  - [ ] 3.1 Priest(a1e5c6f7-...) Lua 스크립트 수정
    - "잊혀진 신들" → "알바(Alva) 태양신" 전면 교체
    - 알바의 어원(희다/밝다의 고어), 새벽녘의 온화한 빛 상징, 생활 속 가르침 수준의 종교 성격 설명 선택지 추가
    - 예배당 역사(패잔병 도착 전 수도승 1명 + 노숙자 2명) 설명 선택지 추가
    - 모든 텍스트 Locale_Dict(en/ko), 영어는 British English
    - 파일: `configs/dialogues/a1e5c6f7-8b9d-0e1f-2a3b-4c5d6e7f8a9b.lua`
    - _요구사항: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ] 3.2 Crypt Guard Monk → Necropolis Monk(b2f6d7a8-...) Lua 스크립트 수정
    - 대화 → 침묵/제스처 서술형 텍스트로 전면 교체
    - 대화 선택지 제거, 수도승의 비언어적 반응만 묘사
    - 죽음에서 갓 일어난 자를 인도하는 역할 암시
    - 파일: `configs/dialogues/b2f6d7a8-9c0e-1f2a-3b4c-5d6e7f8a9b0c.lua`
    - _요구사항: 2.1, 2.2, 2.4_

  - [ ] 3.3 Wandering Bard(f0d4b5e6-...) Lua 스크립트 수정
    - 기존 대화(황금의 시대, 제국 몰락) 유지
    - 소문 선택지 추가: 알바 태양신, 농사/가축 실패, 대마법사 미래인설
    - 모든 텍스트 Locale_Dict(en/ko), 영어는 British English
    - 파일: `configs/dialogues/f0d4b5e6-7a8c-9d0e-1f2a-3b4c5d6e7f8a.lua`
    - _요구사항: 4.1, 4.2, 4.3_

  - [ ] 3.4 Drunken Refugee(e9c3a4d5-...) Lua 스크립트 수정
    - 기존 대화(원정 경험, 대마법사) 유지
    - 소문 선택지 추가: 왕 사망설(대신들이 왕 역할), 밝은 빛=알바신
    - 모든 텍스트 Locale_Dict(en/ko), 영어는 British English
    - 파일: `configs/dialogues/e9c3a4d5-6f7b-8c9d-0e1f-2a3b4c5d6e7f.lua`
    - _요구사항: 5.1, 5.2, 5.3_

  - [ ] 3.5 Royal Adviser(a7e1c2f3-...) Lua 스크립트 수정
    - 기존 대화(정치 상황, 계승 위기) 유지
    - 왕 사망 암시 선택지 추가 (간접적 암시)
    - 모든 텍스트 Locale_Dict(en/ko), 영어는 British English
    - 파일: `configs/dialogues/a7e1c2f3-4b5d-6e7f-8a9b-0c1d2e3f4a5b.lua`
    - _요구사항: 6.1, 6.2, 6.3_

- [ ] 4. Lua 대화 스크립트 생성 — Brother Marcus 및 신규 NPC 3건
  - [ ] 4.1 Brother Marcus(3914fbe8-...) Lua 스크립트 생성
    - 예배당 수도승 역할에 맞는 인사말
    - 예배당 역사(패잔병 도착 전 수도승 1명 + 노숙자 2명) 설명
    - 알바 신앙(일상과 떨어져 한적한 곳에서 신을 공부하는 삶) 설명
    - 모든 텍스트 Locale_Dict(en/ko), 영어는 British English
    - 파일: `configs/dialogues/3914fbe8-c8a9-493a-b451-1084ee4d6d2a.lua` (기존 파일 덮어쓰기)
    - _요구사항: 3.1, 3.2, 3.3_

  - [ ] 4.2 마을 술집 주인 Lua 스크립트 생성
    - 이주 명령에 대한 불만, 마을 상황(술집/마구간/자경단), 성 안 사람들에 대한 비호의적 태도
    - 모든 텍스트 Locale_Dict(en/ko), 영어는 British English
    - 파일: `configs/dialogues/{마을 술집 주인 UUID}.lua`
    - _요구사항: 8.2, 8.3, 8.4_

  - [ ] 4.3 자경단원 Lua 스크립트 생성
    - 마을 자경단 역할, 이주 명령에 대한 반감, 괴물 위협에 대한 경계
    - 모든 텍스트 Locale_Dict(en/ko), 영어는 British English
    - 파일: `configs/dialogues/{자경단원 UUID}.lua`
    - _요구사항: 9.2, 9.3, 9.4_

  - [ ] 4.4 쓰레기장 떠돌이 Lua 스크립트 생성
    - 쓰레기장에서 쓸만한 물건 찾는 행위, 주변 동물들이 음식 먹으러 오는 상황, 북쪽 절벽 바위 틈 힌트
    - 모든 텍스트 Locale_Dict(en/ko), 영어는 British English
    - 파일: `configs/dialogues/{쓰레기장 떠돌이 UUID}.lua`
    - _요구사항: 10.2, 10.3, 10.4_

- [ ] 5. 체크포인트 — Lua 스크립트 구문 확인
  - 모든 Lua 스크립트가 get_dialogue/on_choice 인터페이스를 준수하는지 확인
  - 문제 발생 시 사용자에게 질문

- [ ] 6. JSON 아이템 템플릿 수정/생성
  - [ ] 6.1 forgotten_scripture.json 수정
    - name_en → "Scripture of Alva", name_ko → "알바 태양신의 경전"
    - description_en/ko를 알바 태양신에 대한 기도문으로 변경
    - readable.content의 en/ko 텍스트를 알바 태양신(새벽녘의 온화한 빛, 생활 속 가르침)에 맞게 변경
    - template_id는 "forgotten_scripture" 유지
    - 영어는 British English
    - 파일: `configs/items/forgotten_scripture.json`
    - _요구사항: 7.1, 7.2, 7.3, 7.4_

  - [ ] 6.2 relocation_order.json 생성
    - template_id: "relocation_order", category: "readable", readable.type: "note"
    - 잿빛 기사단의 이주 명령 내용(성벽 수비를 위해 마을을 비우고 이주하라는 명령) en/ko
    - 영어는 British English
    - 파일: `configs/items/relocation_order.json`
    - _요구사항: 12.1, 12.2, 12.3, 12.4_

  - [ ] 6.3 rumour_note.json 생성
    - template_id: "rumour_note", category: "readable", readable.type: "note"
    - 대마법사 미래인설, 저주로 인한 농사 실패, 왕 사망설, 밝은 빛=알바신, 전쟁 사망자 생존설 등 복수의 소문 en/ko
    - 영어는 British English
    - 파일: `configs/items/rumour_note.json`
    - _요구사항: 13.1, 13.2, 13.3, 13.4_

- [ ] 7. 최종 체크포인트 — 전체 검증
  - `./script_test.sh update_worldview` 실행하여 Init_Script 정상 동작 확인
  - 모든 Lua 스크립트 파일이 올바른 위치에 존재하는지 확인
  - 모든 JSON 아이템 파일이 올바른 구조인지 확인
  - 문제 발생 시 사용자에게 질문

## 참고사항

- 모든 작업은 코드 변경 없이 데이터(DB + Lua + JSON)만 수정/추가
- 모든 신규 NPC의 faction_id = ash_knights
- 정적 DB INSERT/UPDATE (UUID 고정)
- 영어 텍스트는 영국 영어(British English)
- PBT 불필요 (코드 변경 없음, 정적 데이터 정확성 검증은 example-based)
- 각 태스크는 requirements.md의 특정 요구사항을 참조
- 체크포인트에서 모든 테스트 통과 확인, 문제 시 사용자에게 질문
