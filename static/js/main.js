// MUD 게임 클라이언트 JavaScript (Pico.css 인터페이스용)
class MudClient {
    constructor() {
        this.socket = null;
        this.isAuthenticated = false;
        this.currentPlayer = null;

        // DOM 요소들
        this.authSection = document.getElementById('auth-section');
        this.gameSection = document.getElementById('game-section');
        this.gameOutput = document.getElementById('game-output');
        this.commandInput = document.getElementById('command-input');
        this.sendBtn = document.getElementById('send-btn');
        this.connectionStatus = document.getElementById('connection-status');
        this.playerName = document.getElementById('player-name');
        this.playerLocation = document.getElementById('player-location');
        this.playerLevel = document.getElementById('player-level');
        this.serverStatus = document.querySelector('#server-status .status-indicator');

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.updateServerStatus('offline');
        this.addWelcomeMessage();
    }

    setupEventListeners() {
        // 로그인 폼
        document.getElementById('login-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });

        // 회원가입 폼
        document.getElementById('register-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleRegister();
        });

        // 명령어 입력
        this.commandInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendGameCommand();
            }
        });

        // 전송 버튼
        this.sendBtn.addEventListener('click', () => {
            this.sendGameCommand();
        });

        // 테마 토글
        document.getElementById('theme-toggle').addEventListener('click', (e) => {
            e.preventDefault();
            this.toggleTheme();
        });

        // 도움말 버튼
        document.getElementById('help-btn').addEventListener('click', (e) => {
            e.preventDefault();
            this.showHelpModal();
        });
    }

    addWelcomeMessage() {
        this.addMessage('🎮 Echoes of the Fallen Age에 오신 것을 환영합니다!', 'system');
        this.addMessage('🏰 고대 문명의 잔해가 남은 신비로운 세계를 탐험하세요.', 'system');
        this.addMessage('📝 먼저 로그인하거나 새 계정을 만들어주세요.', 'info');
    }

    async handleLogin() {
        const username = document.getElementById('login-username').value.trim();
        const password = document.getElementById('login-password').value.trim();

        if (!username || !password) {
            this.showNotification('사용자명과 비밀번호를 입력해주세요.', 'error');
            return;
        }

        this.setLoading(true);
        await this.connect();

        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            const message = {
                command: 'login',
                username: username,
                password: password
            };
            this.socket.send(JSON.stringify(message));
        }
    }

    async handleRegister() {
        const username = document.getElementById('register-username').value.trim();
        const password = document.getElementById('register-password').value.trim();

        if (!username || !password) {
            this.showNotification('사용자명과 비밀번호를 입력해주세요.', 'error');
            return;
        }

        if (password.length < 4) {
            this.showNotification('비밀번호는 최소 4자 이상이어야 합니다.', 'error');
            return;
        }

        this.setLoading(true);
        await this.connect();

        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            const message = {
                command: 'register',
                username: username,
                password: password
            };
            this.socket.send(JSON.stringify(message));
        }
    }

    async connect() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            return;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        try {
            this.socket = new WebSocket(wsUrl);

            this.socket.onopen = () => {
                this.updateServerStatus('online');
                this.updateConnectionStatus('연결됨', 'connected');
            };

            this.socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            };

            this.socket.onclose = () => {
                this.updateServerStatus('offline');
                this.updateConnectionStatus('연결 끊김', 'disconnected');
                if (this.isAuthenticated) {
                    this.addMessage('❌ 서버 연결이 끊어졌습니다.', 'error');
                }
            };

            this.socket.onerror = () => {
                this.updateServerStatus('offline');
                this.showNotification('서버 연결에 실패했습니다.', 'error');
                this.setLoading(false);
            };

        } catch (error) {
            this.showNotification('연결 오류가 발생했습니다.', 'error');
            this.setLoading(false);
        }
    }

    handleMessage(data) {
        this.setLoading(false);

        if (data.error) {
            this.addMessage(`❌ 오류: ${data.error}`, 'error');
            this.showNotification(data.error, 'error');
        } else if (data.status === 'success') {
            this.addMessage(`✅ ${data.message}`, 'success');

            if (data.message.includes('환영합니다')) {
                this.handleSuccessfulLogin(data);
            } else if (data.message.includes('생성되었습니다')) {
                this.showNotification('계정이 생성되었습니다. 로그인해주세요.', 'success');
            }
        } else if (data.response) {
            this.addMessage(data.response, 'info');
        }
    }

    handleSuccessfulLogin(data) {
        this.isAuthenticated = true;
        const username = document.getElementById('login-username').value.trim();
        this.currentPlayer = username;

        // UI 전환
        this.authSection.style.display = 'none';
        this.gameSection.style.display = 'block';
        this.gameSection.classList.add('fade-in');

        // 플레이어 정보 업데이트
        this.playerName.textContent = username;
        this.playerLocation.textContent = '시작 지역';

        // 명령어 입력 활성화
        this.commandInput.disabled = false;
        this.sendBtn.disabled = false;
        this.commandInput.focus();

        // 환영 메시지
        this.addMessage('🎮 게임에 입장했습니다!', 'success');
        this.addMessage('💡 "look" 명령어로 주변을 둘러보거나 빠른 명령어 버튼을 사용하세요.', 'info');

        this.showNotification(`${username}님, 환영합니다!`, 'success');
    }

    sendGameCommand() {
        const command = this.commandInput.value.trim();
        if (!command || !this.isAuthenticated) return;

        this.addMessage(`> ${command}`, 'player');
        this.commandInput.value = '';

        const message = { command: command };
        this.socket.send(JSON.stringify(message));
    }

    addMessage(message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString('ko-KR', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });

        const messageElement = document.createElement('div');
        messageElement.className = `message-${type}`;
        messageElement.innerHTML = `<span class="timestamp">[${timestamp}]</span>${message}`;

        this.gameOutput.appendChild(messageElement);
        this.gameOutput.scrollTop = this.gameOutput.scrollHeight;
    }

    updateServerStatus(status) {
        this.serverStatus.className = `status-indicator ${status}`;
        this.serverStatus.textContent = status === 'online' ? '●' : '●';
    }

    updateConnectionStatus(text, className) {
        this.connectionStatus.textContent = text;
        this.connectionStatus.className = `badge ${className}`;
    }

    setLoading(loading) {
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            if (loading) {
                form.classList.add('loading');
            } else {
                form.classList.remove('loading');
            }
        });
    }

    showNotification(message, type) {
        // 간단한 알림 (실제로는 toast 라이브러리를 사용할 수 있음)
        console.log(`${type.toUpperCase()}: ${message}`);
    }

    toggleTheme() {
        const html = document.documentElement;
        const currentTheme = html.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        const themeToggle = document.getElementById('theme-toggle');

        html.setAttribute('data-theme', newTheme);
        themeToggle.textContent = newTheme === 'dark' ? '🌙' : '☀️';

        localStorage.setItem('theme', newTheme);
    }

    showHelpModal() {
        const modal = document.getElementById('help-modal');
        modal.showModal();
    }
}

// 전역 함수들
function sendCommand(command) {
    if (window.mudClient && window.mudClient.isAuthenticated) {
        window.mudClient.commandInput.value = command;
        window.mudClient.sendGameCommand();
    }
}

function closeModal() {
    const modal = document.getElementById('help-modal');
    modal.close();
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    // 저장된 테마 복원
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    document.getElementById('theme-toggle').textContent = savedTheme === 'dark' ? '🌙' : '☀️';

    // 클라이언트 초기화
    window.mudClient = new MudClient();
});