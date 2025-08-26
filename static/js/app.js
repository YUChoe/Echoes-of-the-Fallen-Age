/**
 * MUD 클라이언트 애플리케이션 진입점
 * Echoes of the Fallen Age
 */

// 클라이언트 초기화
document.addEventListener('DOMContentLoaded', async () => {
    console.log('MUD 클라이언트 애플리케이션 시작');

    try {
        // 전역 클라이언트 인스턴스 생성
        window.mudClient = new MudClient();
        console.log('MUD 클라이언트 초기화 완료');
    } catch (error) {
        console.error('MUD 클라이언트 초기화 실패:', error);

        // 오류 메시지 표시
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.innerHTML = `
            <h2>클라이언트 초기화 오류</h2>
            <p>애플리케이션을 시작할 수 없습니다.</p>
            <p>페이지를 새로고침하거나 관리자에게 문의하세요.</p>
            <button onclick="location.reload()">새로고침</button>
        `;
        document.body.appendChild(errorDiv);
    }
});