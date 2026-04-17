# 요구사항 문서: 읽을 수 있는 아이템 시스템

## 소개

플레이어가 게임 세계에서 책, 노트, 쪽지, 두루마리, 편지 등의 읽을 수 있는 아이템을 발견하고 `read` 명령어로 텍스트 내용을 열람할 수 있는 시스템. 아이템은 인벤토리뿐 아니라 현재 방에 놓여 있는 상태에서도 읽을 수 있다. 여러 페이지를 가진 책도 지원하며, 모든 텍스트는 다국어(en/ko)를 지원한다.

## 용어집

- **Read_Command**: `read` 명령어를 처리하는 명령어 핸들러
- **Readable_Item**: category가 "readable"이고 properties에 텍스트 내용을 포함하는 게임 오브젝트
- **Page**: 여러 페이지를 가진 Readable_Item에서 개별 텍스트 단위
- **Item_Template**: `configs/items/` 디렉토리에 위치한 JSON 형식의 아이템 정의 파일
- **Command_Processor**: 플레이어 입력을 파싱하여 적절한 명령어 핸들러로 라우팅하는 모듈
- **Locale**: 플레이어의 선호 언어 설정 (en 또는 ko)
- **Room_Object**: 방(room)에 위치한 게임 오브젝트
- **Inventory_Object**: 플레이어 인벤토리에 위치한 게임 오브젝트

## 요구사항

### 요구사항 1: read 명령어 등록 및 파싱

**사용자 스토리:** 플레이어로서, `read` 명령어를 입력하여 읽을 수 있는 아이템의 내용을 확인하고 싶다.

#### 수락 기준

1. THE Command_Processor SHALL 시작 시 Read_Command를 "read" 이름으로 등록한다.
2. WHEN 플레이어가 `read <아이템명>` 형식으로 입력하면, THE Read_Command SHALL 아이템명 인자를 파싱하여 대상 아이템을 검색한다.
3. WHEN 플레이어가 인자 없이 `read`만 입력하면, THE Read_Command SHALL 사용법 안내 메시지를 반환한다.
4. WHEN 인증되지 않은 세션에서 `read` 명령어가 실행되면, THE Read_Command SHALL 인증 오류 메시지를 반환한다.

### 요구사항 2: 아이템 검색 및 접근

**사용자 스토리:** 플레이어로서, 인벤토리에 있는 아이템뿐 아니라 현재 방에 놓인 아이템도 읽고 싶다.

#### 수락 기준

1. WHEN 플레이어가 `read <아이템명>`을 입력하면, THE Read_Command SHALL 먼저 플레이어 인벤토리에서 아이템명과 일치하는 Readable_Item을 검색한다.
2. WHEN 인벤토리에서 일치하는 아이템이 없으면, THE Read_Command SHALL 현재 방의 Room_Object 목록에서 아이템명과 일치하는 Readable_Item을 검색한다.
3. WHEN 인벤토리와 방 모두에서 일치하는 아이템이 없으면, THE Read_Command SHALL 아이템을 찾을 수 없다는 오류 메시지를 반환한다.
4. WHEN 일치하는 아이템이 Readable_Item이 아니면, THE Read_Command SHALL 읽을 수 없는 아이템이라는 오류 메시지를 반환한다.
5. THE Read_Command SHALL 아이템명 검색 시 영어 이름과 한국어 이름 모두에 대해 대소문자 구분 없이 부분 일치 검색을 수행한다.
6. WHEN 플레이어가 엔티티 번호(숫자)로 `read <번호>`를 입력하면, THE Read_Command SHALL 인벤토리 엔티티 맵에서 해당 번호의 아이템을 검색한다.

### 요구사항 3: 단일 페이지 아이템 읽기

**사용자 스토리:** 플레이어로서, 노트나 쪽지처럼 한 페이지짜리 아이템의 내용을 바로 읽고 싶다.

#### 수락 기준

1. WHEN 플레이어가 단일 페이지 Readable_Item에 대해 `read`를 실행하면, THE Read_Command SHALL 플레이어의 Locale에 맞는 텍스트 내용을 표시한다.
2. THE Read_Command SHALL 텍스트 내용과 함께 아이템 이름을 헤더로 표시한다.
3. WHEN 플레이어의 Locale에 해당하는 텍스트가 없으면, THE Read_Command SHALL 영어(en) 텍스트로 폴백하여 표시한다.
4. WHEN 영어 텍스트도 없으면, THE Read_Command SHALL 한국어(ko) 텍스트로 폴백하여 표시한다.

### 요구사항 4: 여러 페이지 아이템 읽기

**사용자 스토리:** 플레이어로서, 여러 페이지를 가진 책의 특정 페이지를 선택하여 읽고 싶다.

#### 수락 기준

1. WHEN 플레이어가 여러 페이지를 가진 Readable_Item에 대해 페이지 번호 없이 `read <아이템명>`을 실행하면, THE Read_Command SHALL 첫 번째 Page의 내용을 표시하고 전체 페이지 수를 안내한다.
2. WHEN 플레이어가 `read <아이템명> <페이지번호>`를 실행하면, THE Read_Command SHALL 해당 페이지 번호의 내용을 표시한다.
3. WHEN 플레이어가 존재하지 않는 페이지 번호를 지정하면, THE Read_Command SHALL 유효한 페이지 범위를 안내하는 오류 메시지를 반환한다.
4. THE Read_Command SHALL 각 Page 표시 시 현재 페이지 번호와 전체 페이지 수를 함께 표시한다.

### 요구사항 5: Readable_Item 템플릿 구조

**사용자 스토리:** 콘텐츠 제작자로서, JSON 템플릿 파일로 읽을 수 있는 아이템을 정의하고 싶다.

#### 수락 기준

1. THE Item_Template SHALL properties 내에 "readable" 키를 포함하여 텍스트 내용을 정의한다.
2. THE Item_Template SHALL "readable" 객체 내에 "type" 필드로 아이템 유형(book, note, scroll, letter)을 지정한다.
3. WHEN 단일 페이지 아이템인 경우, THE Item_Template SHALL "readable.content" 객체 내에 "en"과 "ko" 키로 다국어 텍스트를 포함한다.
4. WHEN 여러 페이지 아이템인 경우, THE Item_Template SHALL "readable.pages" 배열 내에 각 Page 객체를 포함하고, 각 Page 객체는 "en"과 "ko" 키로 다국어 텍스트를 포함한다.
5. THE Item_Template SHALL category 필드를 "readable"로 설정한다.
6. FOR ALL 유효한 Readable_Item 템플릿에 대해, JSON 파싱 후 다시 직렬화하고 다시 파싱하면 동일한 구조를 생성한다 (라운드트립 속성).

### 요구사항 6: 세계관 기반 샘플 아이템

**사용자 스토리:** 플레이어로서, 카르나스 세계관에 맞는 읽을 수 있는 아이템을 발견하여 세계의 이야기를 탐험하고 싶다.

#### 수락 기준

1. THE Item_Template SHALL 잿빛 기사단의 포고문을 note 유형으로 정의한다.
2. THE Item_Template SHALL 상인의 일지를 book 유형으로 정의하며, 2페이지 이상의 내용을 포함한다.
3. THE Item_Template SHALL 잊혀진 신의 교회 경전을 scroll 유형으로 정의한다.
4. THE Item_Template SHALL 개인 편지를 letter 유형으로 정의한다.
5. THE Item_Template SHALL 모든 샘플 아이템의 영어 텍스트를 영국 영어(British English)로 작성한다.
6. THE Item_Template SHALL 모든 샘플 아이템의 내용이 카르나스 세계관(몰락한 제국, 대마법사, 잿빛 항구)과 일관성을 유지한다.

### 요구사항 7: 다국어 메시지 지원

**사용자 스토리:** 플레이어로서, 내 선호 언어에 맞는 시스템 메시지를 받고 싶다.

#### 수락 기준

1. THE Read_Command SHALL 모든 오류 메시지와 안내 메시지를 I18N 시스템을 통해 플레이어의 Locale에 맞게 표시한다.
2. THE Read_Command SHALL "읽을 수 없는 아이템", "아이템을 찾을 수 없음", "유효하지 않은 페이지 번호" 등의 메시지에 대해 en/ko 번역을 제공한다.
3. THE Read_Command SHALL 페이지 안내 메시지("페이지 X/Y", "다음 페이지를 읽으려면...")에 대해 en/ko 번역을 제공한다.
