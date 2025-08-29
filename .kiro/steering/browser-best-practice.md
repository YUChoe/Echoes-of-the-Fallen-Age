# Browser MCP 베스트 프랙티스 가이드

## 개요
Browser MCP 도구를 사용할 때 발생할 수 있는 문제들과 해결 방법을 정리한 가이드입니다.

## 기본 설정 및 연결

### 1. 브라우저 확장 프로그램 연결
- **필수 단계**: Browser MCP 확장 프로그램이 설치되어 있어야 함
- **연결 방법**: 브라우저 탭에서 확장 프로그램 아이콘 클릭 → 'Connect' 버튼 클릭
- **연결 확인**: `mcp_browsermcp_browser_navigate` 호출 시 연결 오류가 발생하지 않아야 함

```
❌ 연결 실패 시 오류 메시지:
"No connection to browser extension. In order to proceed, you must first connect a tab by clicking the Browser MCP extension icon in the browser toolbar and clicking the 'Connect' button."
```

### 2. 연결 문제 해결 방법
1. **브라우저 확장 프로그램 재연결**
   - 확장 프로그램 아이콘 클릭
   - 'Disconnect' 후 다시 'Connect' 클릭

2. **새 브라우저 탭 사용**
   - 완전히 새로운 탭 열기
   - 확장 프로그램에 연결
   - 그 후 원하는 URL로 이동

3. **브라우저 재시작**
   - 브라우저 완전 종료 후 재시작
   - 확장 프로그램 재연결

## 탭 ID 문제 해결

### 문제 증상
```
❌ 탭 ID 오류:
"No tab with given id [숫자]"
```

### 해결 방법

#### 1. 페이지 새로고침 후 재시도
```javascript
// 새로운 navigate 호출로 탭 ID 갱신
mcp_browsermcp_browser_navigate(url)
// 그 후 상호작용 시도
```

#### 2. 스냅샷 갱신 패턴
```javascript
// 1. 스냅샷 확인으로 새로운 참조 ID 획득
mcp_browsermcp_browser_snapshot()

// 2. 새로운 참조 ID로 상호작용
mcp_browsermcp_browser_click(new_ref_id)
```

#### 3. 대기 시간 추가
```javascript
// 페이지 로딩 완료 대기
mcp_browsermcp_browser_wait(2)

// 그 후 상호작용 시도
```

## 상호작용 베스트 프랙티스

### 1. 클릭 작업
- **성공 패턴**: 먼저 스냅샷으로 요소 확인 → 클릭 실행
- **실패 시**: 페이지 새로고침 후 다시 시도
- **타임아웃 발생 시**: 더 간단한 요소부터 클릭 테스트

### 2. 텍스트 입력
- **필수 매개변수**: `ref`, `text`, `element`, `submit`
- **입력 전 준비**: 필드 클릭으로 포커스 설정
- **기존 텍스트 제거**: `Control+a` 키 입력 후 새 텍스트 입력

```javascript
// ✅ 올바른 텍스트 입력 패턴
1. mcp_browsermcp_browser_click(field_ref)  // 필드 클릭
2. mcp_browsermcp_browser_press_key("Control+a")  // 기존 텍스트 선택
3. mcp_browsermcp_browser_type(field_ref, "new_text", "field_description", false)
```

### 3. 키보드 입력
- **유용한 키**: `Tab`, `Enter`, `Control+a`, `Escape`
- **사용 시기**: 마우스 클릭이 실패할 때 대안으로 활용

## 문제 해결 워크플로우

### 1단계: 기본 연결 확인
```javascript
try {
    mcp_browsermcp_browser_navigate("https://www.google.com")
    // 성공 시 다음 단계 진행
} catch (error) {
    // 연결 문제 → 확장 프로그램 재연결 필요
}
```

### 2단계: 간단한 상호작용 테스트
```javascript
// Google 같은 안정적인 사이트에서 기본 기능 테스트
1. 페이지 로드 확인
2. 검색창 클릭 테스트
3. 텍스트 입력 테스트
4. 버튼 클릭 테스트
```

### 3단계: 대상 사이트 테스트
```javascript
// 실제 목표 사이트에서 단계별 테스트
1. 페이지 접속
2. 스냅샷으로 요소 확인
3. 하나씩 상호작용 테스트
```

## 일반적인 오류와 해결책

### 1. WebSocket 타임아웃
```
❌ "WebSocket response timeout after 30000ms"
```
**해결책**:
- 페이지 새로고침
- 더 간단한 요소부터 시도
- 대기 시간 추가

### 2. 요소를 찾을 수 없음
```
❌ "Timeout exceeded waiting for element to become clickable"
```
**해결책**:
- 스냅샷으로 요소 존재 확인
- 다른 참조 ID 시도
- 페이지 완전 로딩 대기

### 3. 매개변수 유효성 검사 실패
```
❌ "must have required property 'submit'"
```
**해결책**:
- 모든 필수 매개변수 확인
- API 문서의 매개변수 요구사항 준수

## 성공적인 테스트 시나리오

### 웹 애플리케이션 테스트 패턴
```javascript
// 1. 기본 접속
navigate(target_url)

// 2. 회원가입 테스트
click(signup_button)
type(username_field, "testuser123")
type(password_field, "password123")
click(submit_button)

// 3. 로그인 테스트
navigate(login_url)
type(username_field, "testuser123")
type(password_field, "password123")
click(login_button)

// 4. 결과 확인
snapshot() // 성공 페이지 확인
```

## 디버깅 도구

### 1. 스냅샷 활용
- **목적**: 현재 페이지 상태와 요소 참조 ID 확인
- **사용 시점**: 상호작용 실패 시 첫 번째 확인 도구

### 2. 스크린샷 활용
- **목적**: 시각적 페이지 상태 확인
- **사용 시점**: 예상과 다른 페이지 상태일 때

### 3. 콘솔 로그 확인
- **목적**: JavaScript 오류나 애플리케이션 로그 확인
- **사용법**: `mcp_browsermcp_browser_get_console_logs()`

## 주의사항

### 1. 브라우저 호환성
- Chrome/Edge 기반 브라우저에서 가장 안정적
- Firefox에서는 일부 기능 제한 가능성

### 2. 페이지 로딩 시간
- SPA(Single Page Application)는 추가 로딩 시간 필요
- 동적 콘텐츠 로딩 완료까지 대기 필요

### 3. 보안 제한
- HTTPS 사이트에서 더 안정적
- 일부 사이트는 자동화 도구 차단 가능

## 트러블슈팅 체크리스트

### 연결 문제 시
- [ ] 브라우저 확장 프로그램 설치 확인
- [ ] 확장 프로그램 활성화 상태 확인
- [ ] 'Connect' 버튼 클릭 확인
- [ ] 브라우저 재시작 시도

### 상호작용 실패 시
- [ ] 스냅샷으로 요소 존재 확인
- [ ] 참조 ID 정확성 확인
- [ ] 페이지 완전 로딩 대기
- [ ] 더 간단한 요소부터 테스트

### 성능 문제 시
- [ ] 대기 시간 추가
- [ ] 페이지 새로고침
- [ ] 브라우저 탭 정리
- [ ] 시스템 리소스 확인

## 성공 사례 참고

이 가이드는 다음 성공 사례를 바탕으로 작성되었습니다:
- Google 검색 기능 테스트 ✅
- 로컬 웹 애플리케이션 회원가입/로그인 테스트 ✅
- 복잡한 게임 UI 상호작용 테스트 ✅

정기적으로 이 패턴들을 따라하면 Browser MCP 도구를 안정적으로 사용할 수 있습니다.