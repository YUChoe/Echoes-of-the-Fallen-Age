---
inclusion: always
---

# Git 사용 규칙

## 기본 원칙

### 1. 명령어 단계적 실행
- **절대 금지**: `git add -A && git commit -m "message"` 형태의 체이닝
- **올바른 방법**: 각 명령어를 개별적으로 실행

```bash
# ❌ 잘못된 방법
git add -A && git commit -m "message"
git add file.py && git commit -m "message"

# ✅ 올바른 방법
git add -A
git commit -m "message"

# 또는
git add file.py
git commit -m "message"
```

### 2. 이유
- 각 단계에서 오류 발생 시 명확한 파악 가능
- 사용자가 중간에 개입할 수 있는 기회 제공
- 예상치 못한 파일이 추가되는 것을 방지

## 커밋 전 체크리스트

### 1. 변경사항 확인
```bash
git status
```

### 2. 파일 추가
```bash
# 특정 파일만 추가 (권장)
git add file1.py file2.py

# 또는 모든 변경사항 추가
git add -A
```

### 3. 커밋
```bash
git commit -m "type: 간결한 제목

- 상세 설명 1
- 상세 설명 2"
```

## 커밋 메시지 규칙

### 1. 커밋 타입
- `feat`: 새로운 기능 추가
- `fix`: 버그 수정
- `refactor`: 코드 리팩토링
- `docs`: 문서 수정
- `style`: 코드 포맷팅, 세미콜론 누락 등
- `test`: 테스트 코드 추가/수정
- `chore`: 빌드 업무, 패키지 매니저 설정 등
- `perf`: 성능 개선

### 2. 메시지 형식
```
type: 50자 이내의 간결한 제목

- 변경사항 1
- 변경사항 2
- 변경사항 3
```

### 3. 예시
```bash
git commit -m "feat: 글로벌 몬스터 스폰 제한 시스템 추가

- WorldManager에 set_global_spawn_limit() 메서드 추가
- cleanup_excess_monsters()로 초과 몬스터 자동 삭제
- 몬스터 설정 파일에 global_max_count 필드 추가"
```

## 금지 사항

### 1. 와일드카드 커밋 금지
```bash
# ❌ 절대 금지
git add *
git add * && git commit -m "message"
```

### 2. 이유
- 의도하지 않은 파일이 포함될 수 있음
- .gitignore에 있는 파일도 강제로 추가될 수 있음
- 변경사항을 정확히 파악하기 어려움

### 3. 대안
```bash
# ✅ 올바른 방법
git add -A  # 모든 변경사항 (추적 중인 파일만)
git add .   # 현재 디렉토리 이하
git add file1.py file2.py  # 특정 파일만 (가장 권장)
```

## 커밋 전 필수 확인

### 1. 사용자 허락
- **최종 커밋 전 반드시 사용자에게 확인 요청**
- 커밋 메시지 내용 확인
- 포함될 파일 목록 확인

### 2. 확인 절차
```bash
# 1단계: 상태 확인
git status

# 2단계: 변경사항 확인
git diff

# 3단계: 사용자 승인 후 진행
git add [files]
git commit -m "message"
```

## 특수 상황 처리

### 1. 커밋 수정
```bash
# 마지막 커밋 메시지 수정
git commit --amend -m "new message"

# 마지막 커밋에 파일 추가
git add forgotten_file.py
git commit --amend --no-edit
```

### 2. 변경사항 취소
```bash
# 스테이징 취소
git restore --staged file.py

# 작업 디렉토리 변경사항 취소
git restore file.py
```

### 3. 커밋 되돌리기
```bash
# 마지막 커밋 취소 (변경사항 유지)
git reset --soft HEAD~1

# 마지막 커밋 취소 (변경사항 삭제)
git reset --hard HEAD~1
```

## 브랜치 작업

### 1. 브랜치 생성 및 전환
```bash
# 브랜치 생성
git branch feature-name

# 브랜치 전환
git checkout feature-name

# 생성과 전환 동시에 (사용자 확인 후)
git checkout -b feature-name
```

### 2. 브랜치 병합
```bash
# 현재 브랜치에 다른 브랜치 병합
git merge feature-name
```

## 원격 저장소

### 1. Push
```bash
# 현재 브랜치 push
git push

# 특정 브랜치 push
git push origin branch-name

# 강제 push (매우 주의!)
git push -f  # 사용자 명시적 승인 필요
```

### 2. Pull
```bash
# 현재 브랜치 pull
git pull

# 특정 브랜치 pull
git pull origin branch-name
```

## 로그 확인

### 1. 커밋 히스토리
```bash
# 간단한 로그
git log --oneline -10

# 상세 로그
git log -5

# 그래프 형태
git log --graph --oneline -10
```

### 2. 특정 파일 히스토리
```bash
git log --follow file.py
```

## 주의사항

### 1. 민감한 정보
- 비밀번호, API 키, 토큰 등은 절대 커밋하지 않음
- .env 파일은 .gitignore에 포함
- 실수로 커밋한 경우 즉시 히스토리에서 제거

### 2. 대용량 파일
- 데이터베이스 파일 (.db, .sqlite)
- 로그 파일 (.log)
- 백업 파일 (.tar.gz, .zip)
- 이진 파일 (이미지, 동영상 등)

### 3. 임시 파일
- `*_backup.py`, `*_original.py`
- `test_*.py`, `*_test.py`
- `*.tmp`, `*.temp`

## 체크리스트

커밋 전 반드시 확인:
- [ ] `git status`로 변경사항 확인
- [ ] 의도하지 않은 파일이 포함되지 않았는지 확인
- [ ] 민감한 정보가 포함되지 않았는지 확인
- [ ] 커밋 메시지가 명확한지 확인
- [ ] 사용자 승인을 받았는지 확인
- [ ] 각 명령어를 개별적으로 실행
- [ ] `&&` 연산자를 사용하지 않음

## 요약

**핵심 규칙 3가지:**
1. Git 명령어는 절대 `&&`로 체이닝하지 않음
2. 커밋 전 반드시 사용자 승인 받음
3. `git add *` 절대 사용 금지
