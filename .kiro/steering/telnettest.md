---
inclusion: always
---

# Telnet 테스트 베스트 프랙티스

## 개요
Python MUD 엔진의 Telnet 서버 기능을 테스트하기 위한 표준 방법론입니다.
Python 3.13+에서는 telnetlib이 제거되었으므로 socket 모듈을 사용합니다.

## 기본 원칙

### 1. Python 3.13+ 호환성
- `telnetlib` 모듈은 사용 불가 (제거됨)
- `socket` 모듈을 사용한 직접 TCP 연결
- 비동기 응답 처리를 위한 timeout 설정

### 2. 테스트 계정
- **일반 사용자**: player5426 / test1234
- **관리자**: aa / aaaabbbb (is_admin=1)
- 테스트 전 계정 존재 여부 확인 필요

### 3. 서버 연결 정보
- **호스트**: 127.0.0.1 (localhost)
- **포트**: 4000
- **프로토콜**: TCP (Telnet)

## 표준 테스트 스크립트 구조

### 기본 템플릿

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Telnet 테스트 스크립트"""

import socket
import time
import sys

def send_and_wait(sock, command, wait_time=0.5):
    """명령어를 전송하고 응답을 기다림"""
    print(f"\n>>> 전송: {command}")
    sock.sendall(command.encode('utf-8') + b'\n')
    time.sleep(wait_time)
    
    # 응답 읽기
    try:
        sock.settimeout(0.5)
        response = b""
        while True:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            except socket.timeout:
                break
        
        if response:
            decoded = response.decode('utf-8', errors='ignore')
            print(decoded)
            return decoded
        return ""
    except Exception as e:
        print(f"응답 읽기 오류: {e}")
        return ""

def main():
    """메인 테스트 함수"""
    host = '127.0.0.1'
    port = 4000
    
    print(f"=== Telnet 접속 테스트 시작 ===")
    print(f"서버: {host}:{port}")
    
    try:
        # 1. Telnet 연결
        print("\n1. Telnet 연결 중...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        time.sleep(1)
        
        # 2. 초기 메시지 읽기
        sock.settimeout(1)
        initial = b""
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                initial += chunk
        except socket.timeout:
            pass
        print(initial.decode('utf-8', errors='ignore'))
        
        # 3. 메뉴에서 1번 선택 (로그인)
        print("\n2. 메뉴에서 1번 선택 (로그인)")
        send_and_wait(sock, "1", 1)
        
        # 4. 사용자명 입력
        print("\n3. 사용자명 입력")
        send_and_wait(sock, "player5426", 1)
        
        # 5. 비밀번호 입력
        print("\n4. 비밀번호 입력")
        send_and_wait(sock, "test1234", 1.5)
        
        # 6. 테스트 명령어 실행
        # ... 여기에 테스트할 명령어 추가 ...
        
        # 7. 종료
        print("\n종료")
        send_and_wait(sock, "quit", 1)
        
        sock.close()
        print("\n=== 테스트 완료 ===")
        
    except ConnectionRefusedError:
        print(f"❌ 연결 실패: 서버가 {host}:{port}에서 실행 중이지 않습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## 로그인 절차

### 1. 초기 메뉴
서버 접속 시 다음 메뉴가 표시됩니다:
```
1. 로그인 (login)
2. 회원가입 (register)
3. 종료 (quit)
```

### 2. 로그인 순서
1. 메뉴에서 `1` 입력 (로그인 선택)
2. 사용자명 입력 (예: `player5426`)
3. 비밀번호 입력 (예: `test1234`)
4. 로그인 성공 시 Town Square에 스폰

### 3. 로그인 성공 확인
```
✅ 'player5426'님, 환영합니다!
게임에 입장했습니다!
```

## 명령어 테스트 패턴

### 기본 명령어 테스트
```python
# 현재 위치 확인
send_and_wait(sock, "look", 1)

# 이동 명령어
send_and_wait(sock, "north", 1)
send_and_wait(sock, "go east", 1)

# 능력치 확인
send_and_wait(sock, "stats", 1)

# 도움말
send_and_wait(sock, "help", 1)
```

### 관리자 명령어 테스트
```python
# 좌표 기반 이동 (admin 전용)
send_and_wait(sock, "goto 5 7", 1.5)

# 방 생성 (admin 전용)
send_and_wait(sock, "createroom test_room 테스트방", 1)

# 출구 생성 (admin 전용)
send_and_wait(sock, "createexit room1 north room2", 1)
```

### 전투 명령어 테스트
```python
# 몬스터 공격
send_and_wait(sock, "attack goblin", 1.5)

# 전투 중 행동
send_and_wait(sock, "attack", 1)
send_and_wait(sock, "defend", 1)
send_and_wait(sock, "flee", 1)

# 전투 상태 확인
send_and_wait(sock, "combat", 1)
```

## 응답 처리 가이드

### 1. Timeout 설정
- **초기 연결**: 1초
- **일반 명령어**: 0.5초
- **로그인/이동**: 1~1.5초
- **전투 명령어**: 1.5초

### 2. 버퍼 크기
- **recv 버퍼**: 4096 바이트
- 큰 응답(방 정보, 도움말 등)을 위해 충분한 크기 설정

### 3. 인코딩
- **전송**: UTF-8
- **수신**: UTF-8 (errors='ignore'로 안전 처리)

## 에러 처리

### 연결 실패
```python
except ConnectionRefusedError:
    print(f"❌ 연결 실패: 서버가 {host}:{port}에서 실행 중이지 않습니다.")
    sys.exit(1)
```

### 타임아웃
```python
except socket.timeout:
    # 정상적인 응답 종료로 처리
    pass
```

### 일반 예외
```python
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

## 서버 실행 확인

### 백그라운드 실행
```bash
# 서버 시작
bash -c "source mud_engine_env/Scripts/activate && PYTHONPATH=. python -m src.mud_engine.main" &

# 프로세스 확인
ps aux | grep python

# 서버 로그 확인
tail -f logs/mud_engine-*.log
```

### 포트 확인
```bash
# Windows (Git Bash)
netstat -an | grep 4000

# 또는
ss -tuln | grep 4000
```

## 테스트 체크리스트

### 테스트 전
- [ ] 서버가 실행 중인지 확인
- [ ] 테스트 계정이 존재하는지 확인
- [ ] 포트 4000이 사용 가능한지 확인

### 테스트 중
- [ ] 초기 메뉴가 정상 표시되는지 확인
- [ ] 로그인이 성공하는지 확인
- [ ] 명령어 응답이 정상적으로 수신되는지 확인
- [ ] 에러 메시지가 적절하게 표시되는지 확인

### 테스트 후
- [ ] 연결이 정상적으로 종료되는지 확인
- [ ] 서버 로그에서 오류가 없는지 확인
- [ ] 테스트 결과를 문서화

## 실제 사용 예시

### goto 명령어 테스트 (test_goto_command.py)
```python
# 좌표로 이동 테스트
send_and_wait(sock, "goto 5 7", 1.5)
send_and_wait(sock, "look", 1)

# 다른 좌표로 이동
send_and_wait(sock, "goto 0 0", 1.5)
send_and_wait(sock, "look", 1)

# 잘못된 좌표 테스트
send_and_wait(sock, "goto 99 99", 1)

# 잘못된 입력 테스트
send_and_wait(sock, "goto abc def", 1)
```

### 전투 시스템 테스트
```python
# 몬스터가 있는 위치로 이동
send_and_wait(sock, "goto 7 7", 1.5)
send_and_wait(sock, "look", 1)

# 전투 시작
send_and_wait(sock, "attack goblin", 1.5)

# 전투 진행
send_and_wait(sock, "attack", 1)
send_and_wait(sock, "look", 1)
```

## 주의사항

### 1. Python 버전
- Python 3.13+에서는 반드시 socket 모듈 사용
- telnetlib 사용 시 ModuleNotFoundError 발생

### 2. 타이밍
- 명령어 전송 후 충분한 대기 시간 필요
- 너무 짧으면 응답을 놓칠 수 있음
- 너무 길면 테스트 시간이 증가

### 3. 버퍼 관리
- recv()는 블로킹 호출이므로 timeout 필수
- 응답이 없을 때 무한 대기 방지

### 4. 인코딩 문제
- 한글 처리를 위해 UTF-8 사용
- errors='ignore'로 깨진 문자 처리

## 디버깅 팁

### 서버 로그 확인
```bash
# 실시간 로그 모니터링
tail -f logs/mud_engine-*.log | grep -E "(ERROR|WARNING|player5426)"
```

### 네트워크 패킷 확인
```bash
# tcpdump로 패킷 캡처 (Linux/Mac)
sudo tcpdump -i lo -A port 4000

# Wireshark 사용 (Windows)
# 필터: tcp.port == 4000
```

### 상세 로깅 추가
```python
def send_and_wait(sock, command, wait_time=0.5):
    """명령어를 전송하고 응답을 기다림"""
    print(f"\n>>> 전송: {command}")
    print(f">>> 바이트: {command.encode('utf-8')}")
    
    sock.sendall(command.encode('utf-8') + b'\n')
    time.sleep(wait_time)
    
    # ... 응답 처리 ...
    
    print(f">>> 수신 바이트 수: {len(response)}")
    return decoded
```

## 참고 자료

### 관련 파일
- `test_goto_command.py` - goto 명령어 테스트 예제
- `test_telnet_combat.py` - 전투 시스템 테스트 예제
- `test_telnet_password.py` - 비밀번호 변경 테스트 예제
- `docs/telnet_test_guide.md` - Telnet 테스트 가이드

### 서버 코드
- `src/mud_engine/server/telnet_server.py` - Telnet 서버 구현
- `src/mud_engine/server/telnet_session.py` - Telnet 세션 관리
- `src/mud_engine/commands/` - 명령어 구현

## 결론

Telnet 테스트는 MUD 엔진의 핵심 기능을 검증하는 중요한 과정입니다.
이 문서의 패턴을 따라 일관되고 재사용 가능한 테스트 스크립트를 작성하세요.
