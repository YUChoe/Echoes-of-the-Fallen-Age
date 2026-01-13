# 버전 관리 시스템

## 개요

MUD Engine은 빌드 시점에 Git 정보를 수집하여 버전 정보를 생성하고, 사용자 접속 시 welcome 메시지에 표시하는 시스템을 제공합니다.

## 구성 요소

### 1. 버전 정보 생성 스크립트

- **파일**: `scripts/generate_version_info.py`
- **기능**: Git 저장소에서 커밋 해시, 브랜치, 태그 등의 정보를 수집하여 JSON 파일로 저장

### 2. 버전 관리자

- **파일**: `src/mud_engine/utils/version_manager.py`
- **기능**: 런타임에 버전 정보를 로드하고 관리

### 3. 버전 정보 파일

- **파일**: `src/mud_engine/version_info.json`
- **생성**: 빌드 시점에 자동 생성
- **내용**: 커밋 해시, 브랜치, 빌드 시간 등

## 사용법

### 개발 환경에서 버전 정보 생성

```bash
# 개발 환경 설정 (버전 정보 생성 + 타입 검사)
bash scripts/dev_setup.sh

# 또는 수동으로 버전 정보만 생성
python scripts/generate_version_info.py

# 생성된 버전 정보 확인
cat src/mud_engine/version_info.json
```

개발 환경에서는 버전 정보 파일이 없으면 기본값("dev")을 사용합니다.

### 빌드 및 배포

```bash
# 전체 빌드 프로세스 실행
bash scripts/build_and_deploy.sh

# Docker 이미지 포함 빌드
bash scripts/build_and_deploy.sh --docker
```

### 코드에서 버전 정보 사용

```python
from src.mud_engine.utils.version_manager import get_version_manager, get_version_string

# 버전 관리자 인스턴스 가져오기
version_manager = get_version_manager()

# 간단한 버전 문자열 가져오기
version = get_version_string()  # 예: "master@8d9e7e1" 또는 "v1.0.0@8d9e7e1"

# 개별 정보 가져오기
commit_hash = version_manager.get_commit_hash()  # 짧은 해시
commit_hash_full = version_manager.get_commit_hash(short=False)  # 전체 해시
branch = version_manager.get_branch()
tag = version_manager.get_tag()
build_date = version_manager.get_build_date()
```

## 버전 정보 형식

### JSON 파일 구조

```json
{
  "commit_hash": "8d9e7e1",
  "commit_hash_full": "8d9e7e1c7d13d0afbd8a2631492261ca5dc2ae4b",
  "branch": "master",
  "commit_date": "2025-12-14 17:26:25 +0900",
  "tag": null,
  "is_dirty": true,
  "build_date": "2025-12-14T17:29:46.162499"
}
```

### 버전 문자열 형식

- **태그가 있는 경우**: `v1.0.0 (8d9e7e1)`
- **태그가 없는 경우**: `master@8d9e7e1`
- **더티 상태**: `master@8d9e7e1-dirty`

## Welcome 메시지에 표시

사용자가 Telnet으로 접속할 때 welcome 메시지에 버전 정보가 자동으로 포함됩니다:

```
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║        The Chronicles of Karnas                                   ║
║                                                               ║
║        Divided Dominion                                       ║
║        분할된 지배권, 카르나스에 오신 것을 환영합니다           ║
║                                                               ║
║        Version: master@8d9e7e1-dirty                          ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

## CI/CD 통합

### GitHub Actions 예시

```yaml
- name: Generate version info
  run: python scripts/generate_version_info.py

- name: Build Docker image
  run: |
    COMMIT_HASH=$(git rev-parse --short HEAD)
    docker build -t mud-engine:$COMMIT_HASH .
    docker tag mud-engine:$COMMIT_HASH mud-engine:latest
```

### Docker 빌드 시

Docker 빌드 시점에 버전 정보가 자동으로 생성됩니다:

```bash
# 기본 Docker 빌드
docker build -t mud-engine:latest .

# 빌드 인자와 함께 빌드
docker build \
  --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
  --build-arg VCS_REF="$(git rev-parse HEAD)" \
  --build-arg VERSION="$(git describe --tags --always --dirty)" \
  -t mud-engine:latest .

# Docker Compose 사용
docker-compose build

# 테스트 빌드 스크립트 사용
bash scripts/docker_build_test.sh
```

빌드된 이미지에는 다음과 같은 메타데이터가 포함됩니다:

```bash
# 이미지 라벨 확인
docker inspect mud-engine:latest --format='{{json .Config.Labels}}' | jq
```

## 장점

1. **추적 가능성**: 프로덕션에서 실행 중인 코드의 정확한 버전 확인 가능
2. **디버깅 지원**: 문제 발생 시 해당 커밋으로 빠른 추적
3. **배포 검증**: 올바른 버전이 배포되었는지 확인
4. **사용자 정보**: 관리자가 현재 서버 버전을 쉽게 확인

## 주의사항

1. **Git 저장소 필요**: Git이 설치되어 있고 Git 저장소여야 함
2. **빌드 시점 생성**: 배포 전에 반드시 버전 정보 생성 필요
3. **더티 상태**: 커밋되지 않은 변경사항이 있으면 "-dirty" 표시
4. **파일 제외**: `version_info.json`은 .gitignore에 포함되어 버전 관리에서 제외

## 문제 해결

### Git 정보를 가져올 수 없는 경우

```python
# 기본값 사용
{
  "commit_hash": "dev",
  "commit_hash_full": "development",
  "branch": "unknown",
  "commit_date": "unknown",
  "tag": null,
  "is_dirty": false,
  "build_date": "2025-12-14T17:29:46.162499"
}
```

### 버전 정보 파일이 없는 경우

VersionManager는 자동으로 기본값을 사용하여 안전하게 동작합니다.
