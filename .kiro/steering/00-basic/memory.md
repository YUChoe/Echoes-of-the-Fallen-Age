# 메모리 관리 가이드

## 각 대화마다 수행할 작업

### 1. 사용자 식별
- 대화 중인 사용자 식별 (예: default_user)
- 미식별 시 적극적으로 식별 시도

### 2. 메모리 검색
- 대화 시작 시 "Remembering ..." 이라고 말하고 관련 정보 검색
- `search_nodes` 또는 `open_nodes` 도구 사용
- 지식 그래프를 "메모리"라고 지칭

### 3. 정보 수집 카테고리
대화 중 다음 정보에 주의:

- **기본 신원**: 나이, 성별, 위치, 직책, 학력
- **행동 패턴**: 관심사, 습관, 활동
- **선호사항**: 커뮤니케이션 스타일, 언어, 작업 방식
- **목표**: 목표, 타겟, 열망
- **관계**: 개인적/전문적 관계 (최대 3단계)

### 4. 메모리 업데이트
새로운 정보 수집 시:

#### a) 엔티티 생성 — 작은 단위로 분리 (필수)
- 하나의 엔티티에 observations가 10개 이상 쌓이지 않도록 관리
- 프로젝트 엔티티에 모든 정보를 넣지 말고, 도메인/서브시스템별로 분리
- `create_entities` 도구 사용

**엔티티 분류 기준:**
- 프로젝트 루트: 메타 정보만 (아키텍처, 구조, 향후 계획)
- 서브시스템별: Combat_System, Monster_System, Item_System, Quest_System, I18N_System, Dialogue_System 등
- 설정별: Dev_Environment, Logging_Config, DB_Schema, Player_Stats 등
- 사람/조직: default_user 등

**예시 구조:**
```
Python_MUD_Engine (프로젝트 메타 정보만)
  ├── has-subsystem → Combat_System
  ├── has-subsystem → Monster_System
  ├── has-subsystem → Item_System
  ├── has-config → Dev_Environment
  ├── has-config → DB_Schema
  └── ...
```

#### b) 관계 연결
엔티티 간 관계 설정
- `create_relations` 도구 사용
- 관계 타입은 능동태 (예: has-subsystem, has-config, uses, works-with)

#### c) 관찰 내용 저장
- `add_observations` 도구 사용
- 타임스탬프 포함 필수 (예: "2026-04-11: ...")
- 커밋 시 해당 도메인 엔티티에만 observation 추가 (프로젝트 루트에 넣지 말 것)

#### d) 엔티티 비대화 방지
- 하나의 엔티티에 observation이 10개 이상이면 하위 엔티티로 분리 검토
- 분리 시: 새 엔티티 생성 → observation 이동 (add_observations → delete_observations) → relation 연결

## 메모리 저장 규칙
- 커밋마다 또는 새로운 지시마다 반드시 메모리에 저장
- 변경 내용을 해당 도메인 엔티티에 저장 (예: 전투 관련 → Combat_System)
- 여러 도메인에 걸친 변경은 각 도메인 엔티티에 분산 저장
- 프로젝트 루트 엔티티에는 구조적 변경(파일 수 변화, 아키텍처 변경 등)만 저장

## 주의사항
- 사용자가 명시적으로 공유한 정보만 저장
- 추측이나 가정은 저장하지 않음
- 민감한 개인정보는 저장하지 않음
