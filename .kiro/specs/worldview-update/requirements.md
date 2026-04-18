# 요구사항 문서: 세계관 업데이트 반영 (worldview-update)

## 소개

수정된 WorldView.md에 맞춰 기존 NPC/아이템의 대화 및 설명을 수정하고, 신규 NPC/아이템/방을 추가한다. 핵심 변경은 "잊혀진 신" → "알바(Alva) 태양신" 종교 구체화, 네크로폴리스 수도승 침묵화, 성 서쪽 마을/쓰레기장/돌 제단 관련 콘텐츠 추가, 소문 체계 확장이다. 모든 작업은 정적 DB INSERT + Lua 대화 스크립트 + JSON 아이템 템플릿 방식으로 코드 변경 없이 데이터만 수정/추가한다.

## 용어집

- **Init_Script**: scripts/ 디렉토리에 위치하는 일회성 Python DB 초기화 스크립트
- **Lua_Dialogue_Script**: configs/dialogues/{npc_id}.lua 형식의 NPC 대화 스크립트
- **Item_Template**: configs/items/{template_id}.json 형식의 아이템 정의 파일
- **Locale_Dict**: `{en = "...", ko = "..."}` 형식의 다국어 텍스트 테이블
- **Alva**: 카르나스 세계의 태양신. 새벽녘의 온화하고 깨끗한 빛을 상징
- **Necropolis_Monk**: 네크로폴리스 입구에서 말을 하지 않는 수도승. 죽음에서 갓 일어난 자를 인도
- **Stone_Altar**: 평야에 위치한 돌 제단. 30cm 두께 돌바닥 + 작은 상으로 구성된 알바 신에게 재물을 바치는 장소
- **Western_Village**: 성 서쪽에 위치한 이름 없는 작은 마을. 술집, 마구간, 자경단, 공공게시판 보유
- **Junkyard**: (-12, 1) 좌표에 위치한 성문 밖 쓰레기장

## 요구사항

### 요구사항 1: Priest(사제) 대화 수정 — 알바 태양신 반영

**사용자 스토리:** 플레이어로서, 사제와 대화할 때 "잊혀진 신" 대신 "알바(Alva) 태양신"에 대한 구체적인 종교 정보를 얻고 싶다.

#### 승인 기준

1. WHEN 플레이어가 Priest와 대화를 시작하면, THE Lua_Dialogue_Script SHALL "잊혀진 신들" 대신 "알바(Alva) 태양신"을 언급하는 인사말을 반환한다
2. WHEN 플레이어가 알바 신에 대해 질문하면, THE Lua_Dialogue_Script SHALL 알바의 어원(희다/밝다의 고어), 새벽녘의 온화한 빛 상징, 생활 속 가르침 수준의 종교 성격을 설명하는 응답을 반환한다
3. WHEN 플레이어가 예배당에 대해 질문하면, THE Lua_Dialogue_Script SHALL 패잔병 도착 전 수도승 1명과 노숙자 2명이 살던 공간이었음을 설명하는 응답을 반환한다
4. THE Lua_Dialogue_Script SHALL 모든 텍스트를 Locale_Dict 형식(en/ko)으로 제공한다
5. THE Lua_Dialogue_Script SHALL 영어 텍스트를 영국 영어(British English)로 작성한다

### 요구사항 2: Crypt Guard Monk 변경 — 침묵하는 수도승

**사용자 스토리:** 플레이어로서, 네크로폴리스 입구의 수도승이 말 대신 제스처로 소통하는 것을 경험하고 싶다.

#### 승인 기준

1. WHEN 플레이어가 Necropolis_Monk과 대화를 시작하면, THE Lua_Dialogue_Script SHALL 말 대신 침묵과 제스처를 묘사하는 서술형 텍스트를 반환한다
2. THE Lua_Dialogue_Script SHALL 대화 선택지를 제거하고, 수도승의 비언어적 반응만 묘사한다
3. THE Init_Script SHALL Crypt Guard Monk의 name_en을 "Necropolis Monk"으로, name_ko를 "네크로폴리스 수도승"으로, description을 침묵하는 수도승 + 부활 인도자 역할로 UPDATE한다
4. THE Lua_Dialogue_Script SHALL 죽음에서 갓 일어난 자를 인도하는 역할을 암시하는 묘사를 포함한다

### 요구사항 3: Brother Marcus 역할 재정의 — 예배당 수도승

**사용자 스토리:** 플레이어로서, 예배당에서 수도승을 만나 알바 신앙과 예배당의 역사에 대해 들을 수 있다.

#### 승인 기준

1. WHEN 플레이어가 Brother Marcus와 대화를 시작하면, THE Lua_Dialogue_Script SHALL 예배당 수도승으로서의 역할에 맞는 인사말을 반환한다
2. WHEN 플레이어가 예배당에 대해 질문하면, THE Lua_Dialogue_Script SHALL 패잔병 도착 전 수도승 1명 + 노숙자 2명이 살던 공간이었음을 설명한다
3. WHEN 플레이어가 알바 신에 대해 질문하면, THE Lua_Dialogue_Script SHALL 수도승 관점에서 알바 신앙(일상과 떨어져 한적한 곳에서 신을 공부하는 삶)을 설명한다
4. THE Init_Script SHALL Brother Marcus의 description을 예배당 수도승 역할에 맞게 UPDATE한다

### 요구사항 4: Wandering Bard 대화 확장 — 소문 추가

**사용자 스토리:** 플레이어로서, 음유시인에게서 알바 신, 농사/가축 실패, 새로운 소문들을 들을 수 있다.

#### 승인 기준

1. WHEN 플레이어가 Wandering Bard에게 소문에 대해 질문하면, THE Lua_Dialogue_Script SHALL 알바 태양신, 농사/가축 실패(대마법사 전쟁 이후 계속), 대마법사 미래인설 중 하나 이상의 소문을 반환한다
2. THE Lua_Dialogue_Script SHALL 기존 대화(황금의 시대, 제국 몰락)를 유지하면서 새로운 선택지를 추가한다
3. THE Lua_Dialogue_Script SHALL 모든 텍스트를 Locale_Dict 형식(en/ko)으로 제공한다

### 요구사항 5: Drunken Refugee 대화 확장 — 소문 추가

**사용자 스토리:** 플레이어로서, 술에 취한 난민에게서 왕 사망설과 밝은 빛=알바신 소문을 들을 수 있다.

#### 승인 기준

1. WHEN 플레이어가 Drunken Refugee에게 소문에 대해 질문하면, THE Lua_Dialogue_Script SHALL 왕 사망설(대신들이 왕 역할), 밝은 빛의 정체가 알바신이라는 소문 중 하나 이상을 반환한다
2. THE Lua_Dialogue_Script SHALL 기존 대화(원정 경험, 대마법사)를 유지하면서 새로운 선택지를 추가한다
3. THE Lua_Dialogue_Script SHALL 모든 텍스트를 Locale_Dict 형식(en/ko)으로 제공한다

### 요구사항 6: Royal Adviser 대화 확장 — 왕 사망 암시

**사용자 스토리:** 플레이어로서, 왕의 조언자에게서 왕이 사망했을 가능성에 대한 암시를 들을 수 있다.

#### 승인 기준

1. WHEN 플레이어가 Royal Adviser에게 왕의 상태에 대해 질문하면, THE Lua_Dialogue_Script SHALL 왕이 사망했을 가능성을 간접적으로 암시하는 응답을 반환한다
2. THE Lua_Dialogue_Script SHALL 기존 대화(정치 상황, 계승 위기)를 유지하면서 새로운 선택지를 추가한다
3. THE Lua_Dialogue_Script SHALL 모든 텍스트를 Locale_Dict 형식(en/ko)으로 제공한다

### 요구사항 7: forgotten_scripture.json 아이템 수정

**사용자 스토리:** 플레이어로서, 경전 아이템을 읽었을 때 "이름 없는 신" 대신 "알바(Alva) 태양신"에 대한 내용을 볼 수 있다.

#### 승인 기준

1. THE Item_Template SHALL name_en을 "Scripture of Alva"로, name_ko를 "알바 태양신의 경전"으로 변경한다
2. THE Item_Template SHALL description_en/ko를 알바 태양신에 대한 기도문으로 변경한다
3. THE Item_Template SHALL readable.content의 en/ko 텍스트를 알바 태양신(새벽녘의 온화한 빛, 생활 속 가르침)에 맞게 변경한다
4. THE Item_Template SHALL template_id를 "forgotten_scripture"로 유지하여 기존 참조를 보존한다

### 요구사항 8: 신규 NPC — 마을 술집 주인

**사용자 스토리:** 플레이어로서, 성 서쪽 마을 술집에서 술집 주인과 대화하여 마을 상황을 파악하고 싶다.

#### 승인 기준

1. THE Init_Script SHALL 마을 술집 주인 NPC를 monsters 테이블에 고정 UUID로 INSERT한다
2. THE Lua_Dialogue_Script SHALL 이주 명령에 대한 불만, 마을 상황(술집/마구간/자경단), 성 안 사람들에 대한 비호의적 태도를 반영하는 대화를 제공한다
3. THE Lua_Dialogue_Script SHALL 모든 텍스트를 Locale_Dict 형식(en/ko)으로 제공한다
4. THE Lua_Dialogue_Script SHALL 영어 텍스트를 영국 영어(British English)로 작성한다
5. IF 동일 UUID가 이미 존재하면, THEN THE Init_Script SHALL 해당 NPC를 건너뛴다 (멱등성)

### 요구사항 9: 신규 NPC — 자경단원

**사용자 스토리:** 플레이어로서, 성 서쪽 마을에서 자경단원과 대화하여 마을 방어 상황을 파악하고 싶다.

#### 승인 기준

1. THE Init_Script SHALL 자경단원 NPC를 monsters 테이블에 고정 UUID로 INSERT한다
2. THE Lua_Dialogue_Script SHALL 마을 자경단 역할, 이주 명령에 대한 반감, 괴물 위협에 대한 경계를 반영하는 대화를 제공한다
3. THE Lua_Dialogue_Script SHALL 모든 텍스트를 Locale_Dict 형식(en/ko)으로 제공한다
4. THE Lua_Dialogue_Script SHALL 영어 텍스트를 영국 영어(British English)로 작성한다
5. IF 동일 UUID가 이미 존재하면, THEN THE Init_Script SHALL 해당 NPC를 건너뛴다 (멱등성)

### 요구사항 10: 신규 NPC — 쓰레기장 떠돌이

**사용자 스토리:** 플레이어로서, 쓰레기장에서 물건을 뒤지는 떠돌이와 대화하여 쓰레기장 주변 정보를 얻고 싶다.

#### 승인 기준

1. THE Init_Script SHALL 쓰레기장 떠돌이 NPC를 monsters 테이블에 좌표 (-12, 1)로 고정 UUID INSERT한다
2. THE Lua_Dialogue_Script SHALL 쓰레기장에서 쓸만한 물건을 찾는 행위, 주변 동물들이 음식을 먹으러 오는 상황, 북쪽 절벽 바위 틈에 대한 힌트를 반영하는 대화를 제공한다
3. THE Lua_Dialogue_Script SHALL 모든 텍스트를 Locale_Dict 형식(en/ko)으로 제공한다
4. THE Lua_Dialogue_Script SHALL 영어 텍스트를 영국 영어(British English)로 작성한다
5. IF 동일 UUID가 이미 존재하면, THEN THE Init_Script SHALL 해당 NPC를 건너뛴다 (멱등성)

### 요구사항 11: 신규 NPC — 네크로폴리스 수도승 (요구사항 2와 통합)

이 요구사항은 요구사항 2에서 기존 Crypt Guard Monk을 Necropolis Monk으로 변경하는 것으로 통합 처리한다. 별도의 신규 NPC INSERT는 불필요하다.

### 요구사항 12: 신규 아이템 — 이주 명령 공고문

**사용자 스토리:** 플레이어로서, 마을 공공게시판에서 이주 명령 공고문을 읽어 성벽 밖 마을의 상황을 이해하고 싶다.

#### 승인 기준

1. THE Item_Template SHALL "relocation_order" template_id로 이주 명령 공고문 JSON 파일을 생성한다
2. THE Item_Template SHALL category를 "readable"로, readable.type을 "note"로 설정한다
3. THE Item_Template SHALL 잿빛 기사단의 이주 명령 내용(성벽 수비를 위해 마을을 비우고 이주하라는 명령)을 en/ko로 포함한다
4. THE Item_Template SHALL 영어 텍스트를 영국 영어(British English)로 작성한다

### 요구사항 13: 신규 아이템 — 소문 쪽지

**사용자 스토리:** 플레이어로서, 소문 쪽지를 읽어 대마법사/왕 사망설 등 세계의 소문을 파악하고 싶다.

#### 승인 기준

1. THE Item_Template SHALL "rumour_note" template_id로 소문 쪽지 JSON 파일을 생성한다
2. THE Item_Template SHALL category를 "readable"로, readable.type을 "note"로 설정한다
3. THE Item_Template SHALL 대마법사 미래인설, 저주로 인한 농사 실패, 왕 사망설, 밝은 빛=알바신, 전쟁 사망자 생존설 중 복수의 소문을 en/ko로 포함한다
4. THE Item_Template SHALL 영어 텍스트를 영국 영어(British English)로 작성한다

### 요구사항 14: 신규 방 — 돌 제단

**사용자 스토리:** 플레이어로서, 평야에서 알바 신에게 재물을 바치는 돌 제단을 발견하고 탐험하고 싶다.

#### 승인 기준

1. THE Init_Script SHALL 돌 제단 방을 rooms 테이블에 적절한 평야 좌표로 INSERT한다
2. THE Init_Script SHALL 돌 제단 방의 description_en/ko에 30cm 두께 돌바닥 + 작은 상 구조를 묘사한다
3. THE Init_Script SHALL 영어 텍스트를 영국 영어(British English)로 작성한다
4. IF 동일 좌표에 방이 이미 존재하면, THEN THE Init_Script SHALL 해당 방을 건너뛴다 (멱등성)

### 요구사항 15: Init_Script 통합 및 멱등성

**사용자 스토리:** 운영자로서, 단일 스크립트를 실행하여 모든 세계관 업데이트(기존 NPC 수정 + 신규 NPC/방 추가)를 멱등적으로 적용하고 싶다.

#### 승인 기준

1. THE Init_Script SHALL 기존 NPC 수정(Priest, Crypt Guard Monk, Brother Marcus, Wandering Bard, Drunken Refugee, Royal Adviser)과 신규 NPC 추가(마을 술집 주인, 자경단원, 쓰레기장 떠돌이)를 단일 스크립트에서 처리한다
2. THE Init_Script SHALL 기존 NPC 수정 시 UPDATE 문을 사용하고, 신규 NPC 추가 시 INSERT 문을 사용한다
3. WHEN Init_Script를 2회 연속 실행하면, THE Init_Script SHALL 동일한 DB 상태를 유지한다 (멱등성)
4. IF DB 연결에 실패하면, THEN THE Init_Script SHALL 에러 메시지를 출력하고 exit code 1로 종료한다
5. IF 개별 NPC INSERT/UPDATE에 실패하면, THEN THE Init_Script SHALL 에러 로그를 출력하고 다음 NPC로 진행한다
