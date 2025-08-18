# Python MUD Engine

웹 기반 다중 사용자 텍스트 게임 엔진

## 특징

- 🌐 **웹 기반**: 브라우저에서 바로 플레이
- 🔄 **실시간**: WebSocket을 통한 즉시 반응
- 🌍 **다국어**: 영어/한국어 지원
- 🎮 **하이브리드 UI**: 텍스트 명령어 + 버튼 인터페이스
- ⚡ **실시간 편집**: 서버 재시작 없이 세계 수정
- 💾 **SQLite**: 안정적인 데이터 저장

## 설치 및 실행

### 1. 가상 환경 설정

```bash
# 가상 환경 생성
python -m venv mud_engine_env

# 가상 환경 활성화 (Git Bash)
source mud_engine_env/Scripts/activate
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

`.env` 파일을 수정하여 필요한 설정을 변경하세요.

### 4. 서버 실행

```bash
python -m src.mud_engine.main
```

## 개발 환경

### 코드 포맷팅

```bash
black src/
```

### 린팅

```bash
flake8 src/
```

### 타입 체크

```bash
mypy src/
```

### 테스트 실행

```bash
pytest
```

## 프로젝트 구조

```
python-mud-engine/
├── src/mud_engine/          # 메인 소스 코드
│   ├── server/              # 웹 서버 관련
│   ├── game/                # 게임 로직
│   ├── database/            # 데이터베이스
│   ├── i18n/                # 다국어 지원
│   └── utils/               # 유틸리티
├── tests/                   # 테스트 코드
├── static/                  # 웹 클라이언트 파일
├── data/                    # 데이터 파일
└── requirements.txt         # 의존성 목록
```

## 라이선스

MIT License