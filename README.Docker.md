# 컨테이너 배포 가이드

## 왜 서버만 컨테이너인가

프로덕션은 Oracle Linux 7 이고 파이썬이 3.9 다. 이 서버는 3.9 에서 돌지 않는다.

- `aiohttp` 3.14 가 `Requires-Python: >=3.10` 이다. 설치 자체가 되지 않는다
- 코드가 PEP 604 유니온(`X | None`)을 24곳에서 쓴다. 그중 `game/dialogue.py` 의 dataclass 필드는 모듈을 불러오는 순간 `TypeError` 를 낸다
- 개발과 mypy 대상이 3.14 다. 3.9 로 낮추면 그 격차를 계속 지불해야 한다

게이트웨이는 사정이 다르다. 런타임 의존성이 `ws` 와 `winston` 둘뿐이고 네이티브 모듈이 없다. 프로덕션의 Node 22.22 에서 그대로 돈다. 그래서 서버만 컨테이너에 담고 게이트웨이는 호스트에서 띄운다.

```
호스트 (Oracle Linux 7)
├─ nginx :80                    정적 랜딩과 프록시
├─ 게이트웨이 :3000 (Node 22)   systemd 로 관리
└─ 컨테이너
   └─ MUD 서버  127.0.0.1:4000 게임, 127.0.0.1:4001 어드민
```

두 포트를 `127.0.0.1` 에 묶는다. 플레이어는 게이트웨이를 통해서만 들어오고 게이트웨이는 같은 호스트에 있다. 어드민 포트는 세계 데이터를 직접 고치는 경로이므로 특히 밖으로 열지 않는다.

## 요구 사항

- podman 또는 docker. OL7 에는 podman 이 있다
- podman-compose 를 쓰면 아래 `docker compose` 를 `podman-compose` 로 읽는다

## 빌드와 실행

```bash
export VERSION=$(git describe --tags --always)
export VCS_REF=$(git rev-parse --short HEAD)
export BUILD_DATE=$(date -Iseconds)

docker compose up -d --build
docker compose logs -f
```

`podman` 만 있는 환경에서 compose 없이:

```bash
podman build -t mud-engine \
  --build-arg VERSION="$VERSION" \
  --build-arg VCS_REF="$VCS_REF" \
  --build-arg BUILD_DATE="$BUILD_DATE" .

podman run -d --name mud-engine \
  -p 127.0.0.1:4000:4000 \
  -p 127.0.0.1:4001:4001 \
  -v ./data:/app/data:Z \
  -v ./logs:/app/logs:Z \
  -v ./configs:/app/configs:Z \
  --stop-timeout 30 \
  mud-engine
```

SELinux 가 켜져 있으면 볼륨에 `:Z` 를 붙여야 한다. OL7 기본값이 enforcing 이다.

## 볼륨

| 경로 | 내용 | 비고 |
|---|---|---|
| `/app/data` | SQLite 파일 | 세계 데이터 전부가 여기 있다 |
| `/app/logs` | 서버 로그와 감사 로그 | `admin_audit.log` 가 함께 쌓인다 |
| `/app/configs` | Lua 대사, 아이템·몬스터 템플릿 | 실행 중에 디스크에서 읽는다 |

`configs` 는 이미지에도 담겨 있다. 볼륨을 붙이면 그것이 이미지 사본을 가린다. 대사를 고치고 재시작 없이 반영하려면 볼륨이 필요하고, 이미지만으로 돌리려면 볼륨을 떼면 된다.

컨테이너는 uid 10001(`mud`)로 돈다. 볼륨 디렉터리의 소유자를 맞춰야 한다.

```bash
sudo chown -R 10001:10001 data logs configs
```

## 종료

`SIGTERM` 을 받으면 `ShutdownSignal` 이 처리한다. WAL 체크포인트와 세션 종료 알림까지 끝내고 내려간다. 강제 종료하면 그 절차가 빠진다.

```bash
docker compose stop        # 30초까지 기다린다
```

Windows 개발 환경의 `scripts/run_server.py` 런처는 컨테이너에서 쓰지 않는다. 그 런처는 MSYS 가 신호를 전달하지 못하는 문제를 우회하려고 `CTRL_BREAK_EVENT` 를 보내는 것이고, 리눅스 컨테이너에서는 `SIGTERM` 이 그대로 간다.

## 게이트웨이 쪽 설정

게이트웨이는 호스트에서 돌고 상위 서버로 `127.0.0.1:4000`, `127.0.0.1:4001` 을 본다. 기본값이 그대로 맞는다.

```bash
TELNET_HOST=localhost TELNET_PORT=4000 ADMIN_PORT=4001 \
node dist/server/server/start.js
```

게이트웨이는 WebSocket 을 TCP 로 옮기는 일만 한다. 계정 생성은 게임 채널의 `register` 로 클라이언트가 직접 하므로 게이트웨이에 별도 설정이 필요 없다.

게이트웨이 배포 절차는 클라이언트 저장소의 `DEPLOYMENT.md` 에 있다.

## 확인

```bash
# 컨테이너 상태
docker compose ps

# 게임 채널이 welcome 을 보내는지
printf '' | timeout 2 nc 127.0.0.1 4000 | head -c 200

# 어드민 채널이 열렸는지
printf '' | timeout 2 nc 127.0.0.1 4001 | head -c 200
```

두 포트 모두 접속 직후 `welcome` 한 줄을 보낸다. `channel` 값이 각각 `game` 과 `admin` 이다.

## 이미지에 담기는 것

소스와 `configs` 뿐이다. `.git`, 테스트, 스크립트, 문서는 `.dockerignore` 가 걷어낸다. 버전 정보는 빌드 인자로 받아 `src/mud_engine/version_info.json` 을 만든다. 예전에는 `.git` 을 통째로 복사해 스크립트를 돌렸고 이력이 레이어에 남았다.

의존성은 `--only-binary=:all:` 로 설치한다. `lupa` 와 `bcrypt` 는 컴파일 확장이지만 manylinux 휠이 있다. 휠이 없는 플랫폼에서 조용히 소스 빌드로 넘어가면 빌드 도구가 없어 뒤늦게 실패하므로 그 자리에서 멈추게 한다.
