/**
 * 인증 관련 모듈 (로그인/회원가입)
 */

class AuthModule {
    constructor(client) {
        this.client = client;
    }

    setupEventListeners() {
        // 로그인 폼
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleLogin();
            });
        }

        // 회원가입 버튼
        const registerBtn = document.getElementById('registerBtn');
        if (registerBtn) {
            registerBtn.addEventListener('click', () => {
                this.client.showScreen('register');
            });
        }

        // 회원가입 폼
        const registerForm = document.getElementById('registerForm');
        if (registerForm) {
            registerForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleRegister();
            });
        }

        // 로그인으로 돌아가기 버튼
        const loginBtn = document.getElementById('loginBtn');
        if (loginBtn) {
            loginBtn.addEventListener('click', () => {
                this.client.showScreen('login');
            });
        }
    }

    async handleLogin() {
        const username = document.getElementById('username')?.value.trim();
        const password = document.getElementById('password')?.value;

        if (!username || !password) {
            this.client.uiModule.showMessage('사용자명과 비밀번호를 입력해주세요.', 'error', 'login');
            return;
        }

        try {
            if (!this.client.isConnected) {
                await this.client.connectWebSocket();
            }

            this.client.sendMessage({
                type: 'login',
                command: 'login',
                username: username,
                password: password
            });
        } catch (error) {
            this.client.uiModule.showMessage('서버 연결에 실패했습니다.', 'error', 'login');
        }
    }

    async handleRegister() {
        const username = document.getElementById('regUsername')?.value.trim();
        const password = document.getElementById('regPassword')?.value;

        if (!username || !password) {
            this.client.uiModule.showMessage('사용자명과 비밀번호를 입력해주세요.', 'error', 'register');
            return;
        }

        if (username.length < this.client.config.username.min_length || username.length > this.client.config.username.max_length) {
            this.client.uiModule.showMessage(`사용자명은 ${this.client.config.username.min_length}-${this.client.config.username.max_length}자여야 합니다.`, 'error', 'register');
            return;
        }

        if (password.length < this.client.config.password.min_length) {
            this.client.uiModule.showMessage(`비밀번호는 최소 ${this.client.config.password.min_length}자 이상이어야 합니다.`, 'error', 'register');
            return;
        }

        try {
            if (!this.client.isConnected) {
                await this.client.connectWebSocket();
            }

            this.client.sendMessage({
                type: 'register',
                command: 'register',
                username: username,
                password: password
            });
        } catch (error) {
            this.client.uiModule.showMessage('서버 연결에 실패했습니다.', 'error', 'register');
        }
    }

    handleLoginSuccess(data) {
        console.log('로그인 성공:', data);
        this.client.isAuthenticated = true;

        // 서버 응답에서 데이터 추출
        const loginData = data.data || data;
        this.client.isAdmin = loginData.is_admin || false;

        // 관리자 버튼 표시/숨김
        const adminBtn = document.getElementById('adminBtn');
        if (adminBtn) {
            adminBtn.style.display = this.client.isAdmin ? 'inline-block' : 'none';
        }

        // 플레이어 정보 업데이트
        this.client.uiModule.updatePlayerInfo(loginData.username);

        // 게임 화면으로 전환
        this.client.showScreen('game');

        // UI 초기화 (로그인 직후)
        setTimeout(() => {
            this.client.initializeGameUI();
        }, 100);

        // 환영 메시지 표시
        if (data.message) {
            this.client.gameModule.addGameMessage(data.message, 'success');
        }

        // 로그인 후 자동으로 주변 둘러보기
        setTimeout(() => {
            this.client.sendCommand('look');
        }, 500);
    }

    handleRegisterSuccess(data) {
        console.log('회원가입 성공:', data);
        this.client.uiModule.showMessage('회원가입이 완료되었습니다. 로그인해주세요.', 'success', 'register');

        // 3초 후 로그인 화면으로 이동
        setTimeout(() => {
            this.client.showScreen('login');
        }, 3000);
    }
}

// 전역 변수로 export
window.AuthModule = AuthModule;