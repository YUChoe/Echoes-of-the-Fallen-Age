# Task 22 베스트 프랙티스: CSS와 JavaScript 상태 관리

## 발생한 문제 분석

### 1. CSS 우선순위와 인라인 스타일 충돌
**문제**: JavaScript에서 `element.style.display = 'none'`으로 인라인 스타일을 설정하면 CSS 클래스 규칙이 무시됨
**원인**: 인라인 스타일이 CSS 클래스보다 높은 우선순위를 가짐
**해결**: 인라인 스타일을 제거하고 CSS 클래스만으로 제어

```javascript
// ❌ 잘못된 방법 - 인라인 스타일 사용
element.style.display = 'none';

// ✅ 올바른 방법 - 인라인 스타일 제거
element.style.display = '';
```

### 2. CSS 클래스 기반 상태 관리 패턴
**문제**: 개별 요소의 표시/숨김을 JavaScript로 직접 제어
**해결**: body 클래스를 통한 전역 상태 관리

```css
/* CSS에서 상태별 규칙 정의 */
#commandBuilder {
    display: none !important;
}

.command-builder-active #commandBuilder {
    display: block !important;
}

.normal-mode-active #commandBuilder {
    display: none !important;
}
```

```javascript
// JavaScript에서는 body 클래스만 변경
document.body.className = 'command-builder-active';
```

## 베스트 프랙티스 규칙

### 1. CSS 우선순위 관리
- **인라인 스타일 최소화**: 가능한 한 CSS 클래스로 스타일 제어
- **!important 신중 사용**: 필요한 경우에만 사용하고 문서화
- **CSS 특이성 이해**: 선택자 우선순위를 고려한 설계

### 2. 상태 관리 패턴
- **중앙집중식 상태**: body 클래스를 통한 전역 상태 관리
- **선언적 CSS**: 모든 상태를 CSS에서 미리 정의
- **JavaScript 역할 최소화**: 상태 변경만 담당, 스타일링은 CSS에 위임

### 3. 초기화 순서
- **CSS 우선 적용**: 인라인 스타일 제거 후 클래스 적용
- **지연 없는 초기화**: setTimeout 대신 즉시 상태 설정
- **일관된 초기 상태**: 기본값을 명확히 정의

### 4. 디버깅 전략
- **CSS 검사 도구 활용**: 브라우저 개발자 도구로 스타일 충돌 확인
- **단계별 검증**: 각 수정 후 즉시 테스트
- **상태 로깅**: 상태 변경 시점과 값을 콘솔에 출력

## 구현 체크리스트

### CSS 설계 시
- [ ] 모든 상태를 CSS 클래스로 정의
- [ ] 기본 상태와 활성 상태 명확히 구분
- [ ] !important 사용 시 주석으로 이유 명시
- [ ] 선택자 특이성 고려한 구조 설계

### JavaScript 구현 시
- [ ] 인라인 스타일 사용 최소화
- [ ] 상태 변경은 클래스 조작으로만
- [ ] 초기화 시 기존 인라인 스타일 제거
- [ ] 상태 변경 후 즉시 검증

### 테스트 시
- [ ] 브라우저 개발자 도구로 CSS 적용 상태 확인
- [ ] 각 상태 전환이 올바르게 작동하는지 검증
- [ ] 페이지 새로고침 후 초기 상태 확인
- [ ] 다양한 브라우저에서 동작 확인

## 코드 예시

### 올바른 초기화 패턴
```javascript
initializeGameUI() {
    // 1. 인라인 스타일 제거 (CSS 클래스가 제어하도록)
    const elements = ['commandBuilder', 'dynamicButtons', 'inputContainer'];
    elements.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.style.display = ''; // 인라인 스타일 제거
        }
    });

    // 2. 즉시 올바른 모드 활성화
    if (this.isCommandBuilderMode) {
        this.activateCommandBuilderMode();
    } else {
        this.activateNormalMode();
    }
}
```

### 상태 관리 패턴
```javascript
activateCommandBuilderMode() {
    // body 클래스로 전역 상태 제어
    document.body.className = 'command-builder-active';

    // UI 요소 업데이트
    this.updateToggleButton();
    this.updateCommandBuilderContext();
}

activateNormalMode() {
    // body 클래스로 전역 상태 제어
    document.body.className = 'normal-mode-active';

    // UI 요소 업데이트
    this.updateToggleButton();
}
```

## 주의사항

### 피해야 할 패턴
- 인라인 스타일과 CSS 클래스 혼용
- setTimeout을 통한 불필요한 지연
- 개별 요소의 직접적인 스타일 조작
- 상태 불일치 가능성이 있는 복잡한 로직

### 권장 패턴
- CSS 클래스 기반 상태 관리
- 선언적 스타일 정의
- 중앙집중식 상태 제어
- 명확한 초기화 순서

## 결론

CSS와 JavaScript의 역할을 명확히 분리하고, CSS 우선순위를 이해한 상태 관리 패턴을 사용하면 예측 가능하고 유지보수하기 쉬운 UI를 구현할 수 있습니다. 특히 복잡한 상태를 가진 UI에서는 body 클래스를 통한 전역 상태 관리가 효과적입니다.