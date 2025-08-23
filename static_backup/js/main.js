// Echoes of the Fallen Age - MUD 게임 클라이언트

class MUDClient {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.isAuthenticated = false;
        this.currentPlayer = null;
        this.commandHistory = [];
        this.historyIndex = -1;
        this.sessionStartTime = null;
        this.sessionTimer = null;

        this.initializeElements();
        this.setupEventListeners();
        this.showLoginScreen();
        // 서버 연결은 백그라운드에서 시도하되, UI는 즉시 활성화
        this.connect();
    }

    initializeElements() {
        // 화면 요소들
        this.loginScreen = document.getElementById('loginScreen');
        this.gameScreen = document.getElementById('gameScreen');
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.toastContainer = document.getElementById('toastContainer');

        // 로그인 관련 요소들
        this.loginForm = document.getElementById('loginForm');
        this.registerForm = document.getElementById('registerForm');
        this.loginFormElement = document.getElementById('loginFormElement');
        this.registerFormElement = document.getElementById('registerFormElement');
        this.connectionStatus = document.getElementById('connectionStatus');

        // 게임 화면 요소들
        this.gameOutput = document.getElementById('gameOutput');
        this.commandInput = document.getElementById('commandInput');
        this.sendButton = document.getElementById('sendButton');
        this.playerName = document.getElementById('playerName');
        this.currentLocation = document.getElementById('currentLocation');
        this.sessionTime = document.getElementById('sessionTime');
        this.onlinePlayers = document.getElementById('onlinePlayers');
        this.gameConnectionStatus = document.getElementById('gameConnectionStatus');
        this.logoutBtn = document.getElementById('logoutBtn');
        this.clearOutputBtn = document.getElementById('clearOutput');
        this.scrollToBottomBtn = document.getElementById('scrollToBottom');

        // 빠른 명령어 버튼들
        this.quickCommands = document.querySelectorAll('.quick-cmd');

        // 탭 버튼들
        this.loginTab = document.getElementById('loginTab');
        this.registerTab = document.getElementById('registerTab');
    }

    setupEventListeners() {
        // 탭 전환
        if (this.loginTab) {
            this.loginTab.addEventListener('click', (e) => {
                e.preventDefault();
                this.showLoginForm();
            });
        }

        if (this.registerTab) {
            this.registerTab.addEventListener('click', (e) => {
                e.preventDefault();
                this.showRegisterForm();
            });
        }

        // 폼 제출
        if (this.loginFormElement) {
            this.loginFormElement.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleLogin();
            });
        }

        if (this.registerFormElement) {
            this.registerFormElement.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleRegister();
            });
        }

        // 게임 명령어 입력
        if (this.sendButton) {
            this.sendButton.addEventListener('click', () => {
                this.sendCommand();
            });
        }

        if (this.commandInput) {
            this.commandInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.sendCommand();
                }
            });

            // 명령어 히스토리
            this.commandInput.addEventListener('keydown', (e) => {
                if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    this.navigateHistory(-1);
                } else if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    this.navigateHistory(1);
                }
            });
        }

        // 로그아웃
        if (this.logoutBtn) {
            this.logoutBtn.addEventListener('click', () => {
                this.handleLogout();
            });
        }

        // 출력 제어 버튼들
        if (this.clearOutputBtn) {
            this.clearOutputBtn.addEventListener('click', () => {
                this.clearOutput();
            });
        }

        if (this.scrollToBottomBtn) {
            this.scrollToBottomBtn.addEventListener('click', () => {
                this.scrollToBottom();
            });
        }

        // 빠른 명령어 버튼들
        this.quickCommands.forEach(btn => {
            btn.addEventListener('click', () => {
                const command = btn.dataset.cmd;
                if (this.commandInput) {
                    this.commandInput.value = command;
                    this.sendCommand();
                }
            });
        });
    }

    showLoginScreen() {
        if (this.loginScreen) this.loginScreen.style.display = 'block';
        if (this.gameScreen) this.gameScreen.style.display = 'none';

        // 로그인 폼을 즉시 활성화 (서버 연결 상태와 무관하게)
        this.enableLoginForm();
    }

    showGameScreen() {
        if (this.loginScreen) this.loginScreen.style.display = 'none';
        if (this.gameScreen) this.gameScreen.style.display = 'block';
        if (this.commandInput) {
            this.commandInput.disabled = false;
            this.commandInput.focus();
        }
        if (this.sendButton) this.sendButton.disabled = false;
        this.startSessionTimer();
    }

    enableLoginForm() {
        // 로그인 폼의 모든 입력 요소를 활성화
        const loginInputs = this.loginFormElement?.querySelectorAll('input, button');
        if (loginInputs) {
            loginInputs.forEach(input => {
                input.disabled = false;
            });
        }

        const registerInputs = this.registerFormElement?.querySelectorAll('input, button, select');
        if (registerInputs) {
            registerInputs.forEach(input => {
                input.disabled = false;
            });
        }

        // 첫 번째 입력 필드에 포커스
        const firstInput = document.getElementById('loginUsername');
        if (firstInput) {
            firstInput.focus();
        }
    }

    showLoginForm() {
        if (this.loginForm) {
            this.loginForm.style.display = 'block';
            this.loginForm.classList.add('active');
        }
        if (this.registerForm) {
            this.registerForm.style.display = 'none';
            this.registerForm.classList.remove('active');
        }
    }

    showRegisterForm() {
        if (this.registerForm) {
            this.registerForm.style.display = 'block';
            this.registerForm.classList.add('active');
        }
        if (this.loginForm) {
            this.loginForm.style.display = 'none';
            this.loginForm.classList.remove('active');
        }
    }

    showLoading(show = true) {
        if (this.loadingOverlay) {
            this.loadingOverlay.style.display = show ? 'flex' : 'none';
        }
    }

    showToast(message, type = 'info', duration = 5000) {
        if (!this.toastContainer) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                ${this.getToastIcon(type)} ${message}
            </div>
        `;

        this.toastContainer.appendChild(toast);

        // 자동 제거
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, duration);

        // 클릭으로 제거
        toast.addEventListener('click', () => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        });
    }

    getToastIcon(type) {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        return icons[type] || 'ℹ️';
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.updateConnectionStatus('서버 연결 중...', false);

        try {
            this.socket = new WebSocket(wsUrl);

            this.socket.onopen = () => {
                this.isConnected = true;
                this.updateConnectionStatus('서버 연결됨', true);
            };

            this.socket.onmessage = (event) => {
                this.handleMessage(event.data);
            };

            this.socket.onclose = () => {
                this.isConnected = false;
                this.updateConnectionStatus('연결 끊김', false);

                if (this.isAuthenticated) {
                    this.showToast('서버 연결이 끊어졌습니다. 재연결을 시도합니다...', 'error');
                    setTimeout(() => {
                        this.connect();
                    }, 3000);
                }
            };

            this.socket.onerror = (error) => {
                console.error('WebSocket 오류:', error);
                this.updateConnectionStatus('연결 오류', false);
            };

        } catch (error) {
            console.error('WebSocket 연결 실패:', error);
            this.updateConnectionStatus('연결 실패', false);
        }
    }

    handleMessage(data) {
        try {
            const message = JSON.parse(data);

            switch (message.type) {
                case 'auth_success':
                    this.handleAuthSuccess(message);
                    break;
                case 'auth_error':
                    this.handleAuthError(message);
                    break;
                case 'message':
                    this.addGameMessage(message.content, message.message_type || 'info');
                    break;
                case 'player_list':
                    this.updateOnlinePlayers(message.players);
                    break;
                case 'location_update':
                    this.updateLocation(message.location);
                    break;
                default:
                    this.addGameMessage(message.content || data, 'info');
            }
        } catch (error) {
            // JSON이 아닌 경우 일반 텍스트로 처리
            this.addGameMessage(data, 'info');
        }
    }

    handleLogin() {
        if (!this.loginFormElement) {
            console.error('loginFormElement를 찾을 수 없습니다');
            return;
        }

        const usernameInput = document.getElementById('loginUsername');
        const passwordInput = document.getElementById('loginPassword');

        if (!usernameInput || !passwordInput) {
            console.error('입력 필드를 찾을 수 없습니다');
            this.showToast('입력 필드를 찾을 수 없습니다.', 'error');
            return;
        }

        const username = usernameInput.value.trim();
        const password = passwordInput.value.trim();

        if (!username || !password) {
            this.showToast('사용자명과 비밀번호를 입력해주세요.', 'error');
            return;
        }

        if (!this.isConnected) {
            this.showToast('서버에 연결되지 않았습니다. 잠시 후 다시 시도해주세요.', 'error');
            return;
        }

        const loginData = {
            type: 'login',
            username: username,
            password: password
        };

        this.showLoading(true);
        this.sendMessage(loginData);
    }

    handleRegister() {
        if (!this.registerFormElement) {
            console.error('registerFormElement를 찾을 수 없습니다');
            return;
        }

        const formData = new FormData(this.registerFormElement);
        const password = formData.get('password');
        const passwordConfirm = formData.get('passwordConfirm');

        if (password !== passwordConfirm) {
            this.showToast('비밀번호가 일치하지 않습니다.', 'error');
            return;
        }

        if (!this.isConnected) {
            this.showToast('서버에 연결되지 않았습니다. 잠시 후 다시 시도해주세요.', 'error');
            return;
        }

        const registerData = {
            type: 'register',
            username: formData.get('username'),
            email: formData.get('email'),
            password: password,
            locale: formData.get('locale')
        };

        this.showLoading(true);
        this.sendMessage(registerData);
    }

    handleAuthSuccess(message) {
        this.showLoading(false);
        this.isAuthenticated = true;
        this.currentPlayer = message.player;

        if (this.playerName) this.playerName.textContent = this.currentPlayer.username;

        this.showGameScreen();
        this.showToast(`환영합니다, ${this.currentPlayer.username}님!`, 'success');

        // 환영 메시지 추가
        this.addGameMessage(`🌟 ${this.currentPlayer.username}님, Echoes of the Fallen Age에 오신 것을 환영합니다!`, 'system');
    }

    handleAuthError(message) {
        this.showLoading(false);
        this.showToast(message.content || '인증에 실패했습니다.', 'error');
    }

    handleLogout() {
        if (this.isAuthenticated) {
            this.sendMessage({ type: 'logout' });
        }

        this.isAuthenticated = false;
        this.currentPlayer = null;
        this.stopSessionTimer();

        if (this.socket) {
            this.socket.close();
        }

        this.showLoginScreen();
        this.showToast('로그아웃되었습니다.', 'info');
    }

    sendCommand() {
        if (!this.commandInput) return;

        const command = this.commandInput.value.trim();

        if (!command) {
            return;
        }

        if (!this.isConnected || !this.isAuthenticated) {
            this.showToast('서버에 연결되지 않았거나 로그인이 필요합니다.', 'error');
            return;
        }

        // 명령어 히스토리에 추가
        this.commandHistory.unshift(command);
        if (this.commandHistory.length > 50) {
            this.commandHistory.pop();
        }
        this.historyIndex = -1;

        // 사용자 입력 표시
        this.addGameMessage(`> ${command}`, 'player');

        // 서버로 전송
        this.sendMessage({
            type: 'command',
            content: command
        });

        // 입력창 초기화
        this.commandInput.value = '';
    }

    sendMessage(data) {
        if (this.socket && this.isConnected) {
            this.socket.send(JSON.stringify(data));
        }
    }

    navigateHistory(direction) {
        if (this.commandHistory.length === 0 || !this.commandInput) {
            return;
        }

        this.historyIndex += direction;

        if (this.historyIndex < -1) {
            this.historyIndex = -1;
        } else if (this.historyIndex >= this.commandHistory.length) {
            this.historyIndex = this.commandHistory.length - 1;
        }

        if (this.historyIndex === -1) {
            this.commandInput.value = '';
        } else {
            this.commandInput.value = this.commandHistory[this.historyIndex];
        }
    }

    addGameMessage(content, type = 'info') {
        if (!this.gameOutput) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${type}`;

        // 타임스탬프 추가
        const timestamp = new Date().toLocaleTimeString('ko-KR', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });

        messageDiv.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${this.formatMessage(content)}`;

        this.gameOutput.appendChild(messageDiv);
        this.scrollToBottom();

        // 메시지가 너무 많으면 오래된 것 제거
        const messages = this.gameOutput.querySelectorAll('.message');
        if (messages.length > 1000) {
            messages[0].remove();
        }
    }

    formatMessage(content) {
        // 기본적인 텍스트 포맷팅
        return content
            .replace(/\n/g, '<br>')
            .replace(/\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    updateConnectionStatus(text, isConnected) {
        if (this.connectionStatus) {
            this.connectionStatus.textContent = text;
            this.connectionStatus.className = `badge ${isConnected ? 'connected' : 'disconnected'}`;
        }

        if (this.gameConnectionStatus) {
            this.gameConnectionStatus.textContent = isConnected ? '연결됨' : '연결 끊김';
            this.gameConnectionStatus.className = `badge ${isConnected ? 'connected' : 'disconnected'}`;
        }
    }

    updateOnlinePlayers(players) {
        if (!this.onlinePlayers) return;

        if (!players || !Array.isArray(players)) {
            this.onlinePlayers.innerHTML = '<div class="loading">플레이어 정보를 불러올 수 없습니다.</div>';
            return;
        }

        if (players.length === 0) {
            this.onlinePlayers.innerHTML = '<div class="loading">접속한 플레이어가 없습니다.</div>';
            return;
        }

        const playersHtml = players.map(player => `
            <div class="player-item">
                <span class="player-name">${player.username}</span>
                <span class="player-status">${player.status || '온라인'}</span>
            </div>
        `).join('');

        this.onlinePlayers.innerHTML = playersHtml;
    }

    updateLocation(location) {
        if (this.currentLocation) {
            this.currentLocation.textContent = location || '-';
        }
    }

    startSessionTimer() {
        this.sessionStartTime = new Date();
        this.sessionTimer = setInterval(() => {
            this.updateSessionTime();
        }, 1000);
    }

    stopSessionTimer() {
        if (this.sessionTimer) {
            clearInterval(this.sessionTimer);
            this.sessionTimer = null;
        }
    }

    updateSessionTime() {
        if (!this.sessionStartTime || !this.sessionTime) return;

        const now = new Date();
        const diff = Math.floor((now - this.sessionStartTime) / 1000);

        const hours = Math.floor(diff / 3600);
        const minutes = Math.floor((diff % 3600) / 60);
        const seconds = diff % 60;

        const timeString = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

        this.sessionTime.textContent = timeString;
    }

    clearOutput() {
        if (this.gameOutput) {
            this.gameOutput.innerHTML = '';
            this.addGameMessage('화면이 지워졌습니다.', 'system');
        }
    }

    scrollToBottom() {
        if (this.gameOutput) {
            this.gameOutput.scrollTop = this.gameOutput.scrollHeight;
        }
    }
}

// 전역 함수들
function sendCommand(command) {
    if (window.mudClient && window.mudClient.isAuthenticated) {
        if (window.mudClient.commandInput) {
            window.mudClient.commandInput.value = command;
            window.mudClient.sendCommand();
        }
    }
}

function closeModal() {
    const modal = document.getElementById('help-modal');
    if (modal) {
        modal.close();
    }
}

// 테마 토글 기능
function setupThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    const helpBtn = document.getElementById('help-btn');

    if (themeToggle) {
        // 저장된 테마 복원
        const savedTheme = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
        themeToggle.textContent = savedTheme === 'dark' ? '🌙' : '☀️';

        themeToggle.addEventListener('click', (e) => {
            e.preventDefault();
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

            document.documentElement.setAttribute('data-theme', newTheme);
            themeToggle.textContent = newTheme === 'dark' ? '🌙' : '☀️';
            localStorage.setItem('theme', newTheme);
        });
    }

    if (helpBtn) {
        helpBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const modal = document.getElementById('help-modal');
            if (modal) {
                modal.showModal();
            }
        });
    }
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    setupThemeToggle();
    window.mudClient = new MUDClient();
});