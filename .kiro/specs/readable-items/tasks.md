# 구현 계획: 읽을 수 있는 아이템 시스템

## 개요

`read` 명령어와 readable 아이템 시스템을 구현한다. 기존 `BaseCommand` 패턴과 아이템 검색 로직(`use_command.py`)을 재사용하며, `properties.readable` 객체를 통해 텍스트 내용을 정의한다. I18N 메시지, 샘플 아이템 템플릿 4종, 단위 테스트 및 속성 기반 테스트를 포함한다.

## 태스크

- [x] 1. I18N 메시지 및 아이템 템플릿 준비
  - [x] 1.1 `data/translations/item.json`에 read 관련 I18N 메시지 추가
    - `read.usage`, `read.not_found`, `read.not_readable`, `read.header`, `read.page_info`, `read.page_hint`, `read.invalid_page`, `read.error` 키를 en/ko로 추가
    - 영어 텍스트는 영국 영어(British English)로 작성
    - _요구사항: 7.1, 7.2, 7.3_

  - [x] 1.2 샘플 readable 아이템 템플릿 4종 생성
    - `configs/items/ash_knights_proclamation.json` (note, 단일 페이지)
    - `configs/items/merchant_journal.json` (book, 2페이지 이상)
    - `configs/items/forgotten_scripture.json` (scroll, 단일 페이지)
    - `configs/items/personal_letter.json` (letter, 단일 페이지)
    - 모든 영어 텍스트는 영국 영어(British English)로 작성
    - 카르나스 세계관(몰락한 제국, 대마법사, 잿빛 항구, 잊혀진 신의 교회)과 일관성 유지
    - `category`를 `"readable"`로 설정, `properties.readable` 구조 준수
    - _요구사항: 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 2. ReadCommand 핵심 구현
  - [x] 2.1 `src/mud_engine/commands/read_command.py` 생성
    - `BaseCommand`를 상속하여 `ReadCommand` 클래스 구현
    - `name="read"`, `aliases=[]`, `usage="read <아이템명> [페이지번호]"`
    - `execute()` 메서드: 인자 검증, 인증 확인, 아이템 검색, readable 판별, 텍스트 표시
    - `_find_item_by_entity_number()`: 인벤토리 엔티티 번호로 아이템 검색
    - `_find_item_by_name()`: 이름으로 인벤토리 → 방 순서 검색 (대소문자 무시 부분 일치, en/ko 모두)
    - `_is_readable()`: `properties.readable` 존재 여부 확인
    - `_get_readable_text()`: 단일 페이지/여러 페이지 분기, 로케일 폴백 처리
    - `_get_localized_content()`: 로케일 폴백 체인 (요청 로케일 → en → ko)
    - 인자 없이 `read`만 입력 시 사용법 안내 메시지 반환
    - 미인증 세션 시 인증 오류 메시지 반환
    - 아이템 미발견 시 오류 메시지 반환
    - non-readable 아이템 시 오류 메시지 반환
    - 여러 페이지 아이템: 페이지 번호 없으면 첫 페이지 + 전체 페이지 수 안내
    - 여러 페이지 아이템: 유효하지 않은 페이지 번호 시 범위 안내 오류
    - 출력에 아이템 이름 헤더 포함
    - 아이템 유형별 아이콘 표시 (📖 book, 📜 note/scroll, ✉️ letter)
    - 모든 메시지는 I18N 시스템 사용
    - _요구사항: 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4, 7.1_

  - [x] 2.2 `CommandProcessor`에 `ReadCommand` 등록
    - 기존 명령어 등록 패턴을 따라 게임 엔진 초기화 시 `ReadCommand`를 `"read"` 이름으로 등록
    - `src/mud_engine/commands/__init__.py`에 import 추가
    - _요구사항: 1.1_

- [x] 3. 체크포인트 - 정적 검사 및 기본 동작 확인
  - mypy + ruff 정적 검사 통과 확인
  - 모든 테스트 통과 확인, 문제 발생 시 사용자에게 질문

- [ ] 4. 단위 테스트 및 속성 기반 테스트
  - [ ]* 4.1 ReadCommand 단위 테스트 작성
    - `tests/test_read_command.py` 생성
    - ReadCommand 등록 확인 (SMOKE)
    - 빈 인자 시 사용법 반환 (요구사항 1.3)
    - 미인증 세션 오류 (요구사항 1.4)
    - 샘플 템플릿 4종의 JSON 구조 검증 (요구사항 5.1~5.5)
    - 번역 파일에 read 관련 키 존재 확인 (요구사항 7.2, 7.3)
    - _요구사항: 1.1, 1.3, 1.4, 5.1, 5.2, 5.3, 5.4, 5.5, 7.2, 7.3_

  - [ ]* 4.2 Property 1 속성 기반 테스트: 이름 검색 대소문자 무시 부분 일치
    - `tests/test_read_properties.py` 생성
    - hypothesis 라이브러리 사용, 최소 100회 반복
    - 임의의 readable 아이템과 해당 이름의 부분 문자열(대소문자 변환 포함)에 대해 검색 함수가 항상 해당 아이템을 찾는지 검증
    - **Property 1: 이름 검색은 대소문자 무시 부분 일치를 지원한다**
    - **Validates: 요구사항 1.2, 2.5**

  - [ ]* 4.3 Property 2 속성 기반 테스트: 아이템 검색 인벤토리 우선
    - 인벤토리와 방 모두에 동일 이름의 readable 아이템이 존재할 때, 검색 결과가 항상 인벤토리 아이템인지 검증
    - **Property 2: 아이템 검색은 인벤토리를 방보다 우선한다**
    - **Validates: 요구사항 2.1, 2.2**

  - [ ]* 4.4 Property 3 속성 기반 테스트: 존재하지 않는 아이템 검색 오류
    - 인벤토리와 방 모두에 해당 이름의 아이템이 없으면 항상 오류 결과를 반환하는지 검증
    - **Property 3: 존재하지 않는 아이템 검색은 오류를 반환한다**
    - **Validates: 요구사항 2.3**

  - [ ]* 4.5 Property 4 속성 기반 테스트: non-readable 아이템 읽기 오류
    - readable 속성이 없는 아이템에 대해 항상 "읽을 수 없는 아이템" 오류를 반환하는지 검증
    - **Property 4: non-readable 아이템은 읽기 오류를 반환한다**
    - **Validates: 요구사항 2.4**

  - [ ]* 4.6 Property 5 속성 기반 테스트: 로케일 폴백 체인
    - 다양한 로케일 조합의 content 딕셔너리에 대해 폴백 우선순위(요청 로케일 → en → ko)가 올바르게 동작하는지 검증
    - **Property 5: 로케일 폴백 체인이 올바르게 동작한다**
    - **Validates: 요구사항 3.1, 3.3, 3.4**

  - [ ]* 4.7 Property 6 속성 기반 테스트: 유효한 페이지 번호 접근
    - 임의의 여러 페이지 readable 아이템과 유효 페이지 번호에 대해 올바른 페이지 내용이 반환되는지 검증
    - **Property 6: 유효한 페이지 번호는 올바른 페이지 내용을 반환한다**
    - **Validates: 요구사항 4.1, 4.2, 4.4**

  - [ ]* 4.8 Property 7 속성 기반 테스트: 범위 밖 페이지 번호 오류
    - 유효 범위(1~전체 페이지 수) 밖의 페이지 번호에 대해 항상 범위 안내 오류를 반환하는지 검증
    - **Property 7: 범위 밖 페이지 번호는 오류를 반환한다**
    - **Validates: 요구사항 4.3**

  - [ ]* 4.9 Property 8 속성 기반 테스트: Readable 템플릿 JSON 라운드트립
    - 임의의 유효한 readable 아이템 템플릿에 대해 `json.dumps` 후 `json.loads`를 수행하면 원본과 동일한 구조가 생성되는지 검증
    - **Property 8: Readable 템플릿 JSON 라운드트립**
    - **Validates: 요구사항 5.6**

  - [ ]* 4.10 Property 9 속성 기반 테스트: 출력 헤더에 아이템 이름 포함
    - 임의의 readable 아이템에 대해 read 명령어의 성공 출력에 항상 해당 아이템의 로케일별 이름이 포함되는지 검증
    - **Property 9: 출력에는 항상 아이템 이름이 헤더로 포함된다**
    - **Validates: 요구사항 3.2**

- [x] 5. 최종 체크포인트 - 전체 검증
  - mypy + ruff 정적 검사 통과 확인
  - 모든 테스트 통과 확인, 문제 발생 시 사용자에게 질문

## 참고사항

- `*` 표시된 태스크는 선택사항이며 빠른 MVP를 위해 건너뛸 수 있음
- 각 태스크는 특정 요구사항을 참조하여 추적 가능
- 체크포인트에서 점진적 검증 수행
- 속성 기반 테스트는 hypothesis 라이브러리 사용, 최소 100회 반복
- 정적 검사(mypy + ruff) 통과 필수
- 모든 코드 주석은 한국어로 작성
- 영어 텍스트는 영국 영어(British English) 사용
