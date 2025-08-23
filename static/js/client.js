/**
 * 심플한 MUD 클라이언트
 * Echoes of the Fallen Age
 */

class MudClient {
    constructor() {
        this.ws = null;
        this.isConnected = false;
        this.isAuthenticated = false;
        this.commandHistory = [];
        this.historyIndex = -1;
        this.currentScreen = 'login';
        this.config = {
            username: { min_length: 3, max_length: 20 },
            password: { min_length: 6 }
        };

        this.init();
    }

    async init() {
        console.log('클라이언트 초기화 시작');
        await this.loadConfig();
        this.setupEventListeners();
        this.showScreen('login');
        this.updateValidationMessages();
        console.log('클라이언트 초기화 완료');
    }

    async loadConfig() {
        try {
            const response = await fetch('/api/config');
            if (response.ok) {
                this.config = await response.json();
                console.log('서버에서 로드된 설정:', this.config);
            }
        } catch (error) {
            console.warn('설정을 불러올 수 없습니다. 기본값을 사용합니다:', error);
        }
    }

    updateValidationMessages() {
        console.log('updateValidationMessages 호출됨, 현재 설정:', this.config);

        // 사용자명 유효성 검사 메시지 업데이트
        const usernameHelp = document.getElementById('username_help');
        if (usernameHelp) {
            const message = `${this.config.username.min_length}-${this.config.username.max_length}자, 영문자와 숫자만 사용 가능`;
            usernameHelp.textContent = message;
            console.log('사용자명 도움말 업데이트:', message);
        } else {
            console.error('username_help 요소를 찾을 수 없습니다');
        }

        // 비밀번호 유효성 검사 메시지 업데이트
        const passwordHelp = document.getElementById('password_help');
        if (passwordHelp) {
            const message = `최소 ${this.config.password.min_length}자 이상`;
            passwordHelp.textContent = message;
            console.log('비밀번호 도움말 업데이트:', message);
        } else {
            console.error('password_help 요소를 찾을 수 없습니다');
        }
    }

    setupEventListeners() {
        // 로그인 폼
        const loginForm = document.getElementById('login_form');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleLogin();
            });
        }

        // 회원가입 버튼
        const registerBtn = document.getElementById('register_btn');
        if (registerBtn) {
            registerBtn.addEventListener('click', () => {
                this.showScreen('register');
            });
        }

        // 회원가입 폼
        const registerForm = document.getElementById('register_form');
        if (registerForm) {
            registerForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleRegister();
            });
        }

        // 로그인으로 돌아가기 버튼
        const loginBtn = document.getElementById('login_btn');
        if (loginBtn) {
            loginBtn.addEventListener('click', () => {
                this.showScreen('login');
            });
        }

        // 게임 명령어 입력
        const commandInput = document.getElementById('command_input');
        if (commandInput) {
            commandInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    this.sendCommand();
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    this.showPreviousCommand();
                } else if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    this.showNextCommand();
                }
            });
        }

        // 전송 버튼
        const sendBtn = document.getElementById('send_btn');
        if (sendBtn) {
            sendBtn.addEventListener('click', () => {
                this.sendCommand();
            });
        }

        // 빠른 명령어 버튼들
        document.querySelectorAll('.cmd_btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const cmd = btn.dataset.cmd;
                this.sendCommand(cmd);
            });
        });

        // 로그아웃 버튼
        const logoutBtn = document.getElementById('logout_btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                this.logout();
            });
        }
    }

    showScreen(screenName) {
        // 모든 화면 숨기기
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.remove('active');
        });

        // 선택된 화면 표시
        const targetScreen = document.getElementById(screenName + '_screen');
        if (targetScreen) {
            targetScreen.classList.add('active');
            this.currentScreen = screenName;
        }

        // 화면별 초기화
        if (screenName === 'game') {
            const commandInput = document.getElementById('command_input');
            if (commandInput) {
                commandInput.focus();
            }
        }
    }

    async connectWebSocket() {
        return new Promise((resolve, reject) => {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;

            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                this.isConnected = true;
                this.updateConnectionStatus('연결됨', true);
                resolve();
            };

            this.ws.onmessage = (event) => {
                this.handleMessage(JSON.parse(event.data));
            };

            this.ws.onclose = () => {
                this.isConnected = false;
                this.updateConnectionStatus('연결 끊김', false);

                // 인증된 상태에서 연결이 끊어지면 재연결 시도
                if (this.isAuthenticated) {
                    setTimeout(() => this.connectWebSocket(), 3000);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket 오류:', error);
                reject(error);
            };
        });
    }

    async handleLogin() {
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;

        if (!username || !password) {
            this.showMessage('사용자명과 비밀번호를 입력해주세요.', 'error', 'login');
            return;
        }

        try {
            if (!this.isConnected) {
                await this.connectWebSocket();
            }

            this.sendMessage({
                command: 'login',
                username: username,
                password: password
            });

        } catch (error) {
            this.showMessage('서버 연결에 실패했습니다.', 'error', 'login');
        }
    }

    async handleRegister() {
        const username = document.getElementById('reg_username').value.trim();
        const password = document.getElementById('reg_password').value;

        if (!username || !password) {
            this.showMessage('사용자명과 비밀번호를 입력해주세요.', 'error', 'register');
            return;
        }

        if (username.length < this.config.username.min_length || username.length > this.config.username.max_length) {
            this.showMessage(`사용자명은 ${this.config.username.min_length}-${this.config.username.max_length}자여야 합니다.`, 'error', 'register');
            return;
        }

        if (password.length < this.config.password.min_length) {
            this.showMessage(`비밀번호는 최소 ${this.config.password.min_length}자 이상이어야 합니다.`, 'error', 'register');
            return;
        }

        try {
            if (!this.isConnected) {
                await this.connectWebSocket();
            }

            this.sendMessage({
                command: 'register',
                username: username,
                password: password
            });

        } catch (error) {
            this.showMessage('서버 연결에 실패했습니다.', 'error', 'register');
        }
    }

    handleMessage(data) {
        if (data.error) {
            const screen = this.isAuthenticated ? 'game' : this.currentScreen;
            this.showMessage(data.error, 'error', screen);
            return;
        }

        if (data.status === 'success') {
            if (data.action === 'login_success' || data.action === 'register_success') {
                this.isAuthenticated = true;
                this.showScreen('game');
                this.updatePlayerInfo(data.username);
                this.addGameMessage(`${data.username}님, 환영합니다!`, 'success');

                // 초기 명령어 실행
                setTimeout(() => {
                    this.sendCommand('look');
                }, 500);

            } else {
                this.showMessage(data.message, 'success', this.currentScreen);
            }
        } else if (data.response) {
            this.addGameMessage(data.response, data.message_type || 'system');
        }
    }

    sendMessage(data) {
        if (this.ws && this.isConnected) {
            this.ws.send(JSON.stringify(data));
        }
    }

    sendCommand(command = null) {
        const input = document.getElementById('command_input');
        const cmd = command || (input ? input.value.trim() : '');

        if (!cmd) return;

        // 명령어 히스토리에 추가
        if (this.commandHistory[this.commandHistory.length - 1] !== cmd) {
            this.commandHistory.push(cmd);
            if (this.commandHistory.length > 50) {
                this.commandHistory.shift();
            }
        }
        this.historyIndex = this.commandHistory.length;

        // 입력 필드 클리어
        if (!command && input) {
            input.value = '';
        }

        // 서버로 전송
        this.sendMessage({
            command: cmd
        });

        // 게임 출력에 명령어 표시
        this.addGameMessage(`> ${cmd}`, 'player');
    }

    addGameMessage(message, type = 'system') {
        const output = document.getElementById('game_output');
        if (!output) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `game_message ${type}`;

        // 타임스탬프 추가
        const timestamp = new Date().toLocaleTimeString();
        messageDiv.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${this.escapeHtml(message)}`;

        output.appendChild(messageDiv);
        output.scrollTop = output.scrollHeight;

        // 메시지가 너무 많으면 오래된 것 제거
        const messages = output.querySelectorAll('.game_message');
        if (messages.length > 1000) {
            messages[0].remove();
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showPreviousCommand() {
        if (this.historyIndex > 0) {
            this.historyIndex--;
            const input = document.getElementById('command_input');
            if (input) {
                input.value = this.commandHistory[this.historyIndex];
            }
        }
    }

    showNextCommand() {
        const input = document.getElementById('command_input');
        if (!input) return;

        if (this.historyIndex < this.commandHistory.length - 1) {
            this.historyIndex++;
            input.value = this.commandHistory[this.historyIndex];
        } else {
            this.historyIndex = this.commandHistory.length;
            input.value = '';
        }
    }

    updateConnectionStatus(status, isConnected) {
        const statusElement = document.getElementById('connection_status');
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = `status ${isConnected ? 'connected' : 'disconnected'}`;
        }
    }

    updatePlayerInfo(username) {
        const playerInfo = document.getElementById('player_info');
        if (playerInfo) {
            playerInfo.textContent = `플레이어: ${username}`;
        }
    }

    showMessage(message, type, screen) {
        const messageElement = document.getElementById(`${screen}_message`);
        if (messageElement) {
            messageElement.textContent = message;
            messageElement.className = `message ${type}`;
            messageElement.classList.remove('hidden');

            setTimeout(() => {
                messageElement.classList.add('hidden');
            }, 5000);
        }
    }

    logout() {
        if (this.ws) {
            this.sendCommand('quit');
            this.ws.close();
        }

        this.isAuthenticated = false;
        this.showScreen('login');

        // 폼 초기화
        const loginForm = document.getElementById('login_form');
        if (loginForm) {
            loginForm.reset();
        }

        // 게임 출력 초기화
        const gameOutput = document.getElementById('game_output');
        if (gameOutput) {
            gameOutput.innerHTML = '';
        }

        this.commandHistory = [];
        this.historyIndex = -1;
    }
}

// 클라이언트 초기화
document.addEventListener('DOMContentLoaded', async () => {
    window.mudClient = new MudClient();
});