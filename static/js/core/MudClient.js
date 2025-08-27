/**
 * MUD 클라이언트 메인 클래스
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

        // 하이브리드 인터페이스 관련
        this.currentRoomId = null;

        // 관리자 관련
        this.isAdmin = false;

        // 로그아웃 플래그
        this.isLoggingOut = false;

        // 모듈 인스턴스들
        this.authModule = null;
        this.gameModule = null;
        this.adminModule = null;
        this.statsModule = null;
        this.uiModule = null;
        this.messageHandler = null;

        this.init();
    }

    async init() {
        console.log('클라이언트 초기화 시작');

        // 설정 로드
        await this.loadConfig();

        // 모듈 초기화
        this.initializeModules();

        // 이벤트 리스너 설정
        this.setupEventListeners();

        // 초기 화면 표시
        this.showScreen('login');
        this.updateValidationMessages();

        console.log('클라이언트 초기화 완료');
    }

    initializeModules() {
        // 모듈들 초기화
        this.authModule = new AuthModule(this);
        this.gameModule = new GameModule(this);
        this.adminModule = new AdminModule(this);
        this.statsModule = new StatsModule(this);
        this.npcModule = new NPCModule(this);
        this.uiModule = new UIModule(this);
        this.messageHandler = new MessageHandler(this);
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
        const usernameHelp = document.getElementById('usernameHelp');
        if (usernameHelp) {
            const message = `${this.config.username.min_length}-${this.config.username.max_length}자, 영문자와 숫자만 사용 가능`;
            usernameHelp.textContent = message;
            console.log('사용자명 도움말 업데이트:', message);
        } else {
            console.error('usernameHelp 요소를 찾을 수 없습니다');
        }

        // 비밀번호 유효성 검사 메시지 업데이트
        const passwordHelp = document.getElementById('passwordHelp');
        if (passwordHelp) {
            const message = `최소 ${this.config.password.min_length}자 이상`;
            passwordHelp.textContent = message;
            console.log('비밀번호 도움말 업데이트:', message);
        } else {
            console.error('passwordHelp 요소를 찾을 수 없습니다');
        }
    }

    setupEventListeners() {
        // 기본 이벤트 리스너들
        this.authModule.setupEventListeners();
        this.gameModule.setupEventListeners();
        this.adminModule.setupEventListeners();
        this.statsModule.setupEventListeners();
    }

    showScreen(screenName) {
        // 모든 화면 숨기기
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.remove('active');
        });

        // 대상 화면 표시
        const targetScreen = document.getElementById(screenName + 'Screen');
        if (targetScreen) {
            targetScreen.classList.add('active');
            this.currentScreen = screenName;
        }

        // 화면별 초기화
        if (screenName === 'game') {
            const commandInput = document.getElementById('commandInput');
            if (commandInput) {
                commandInput.focus();
            }
        }
    }

    async connectWebSocket() {
        return new Promise((resolve, reject) => {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;

            console.log('WebSocket 연결 시도:', wsUrl);
            this.uiModule.updateConnectionStatus('연결 중...', false);

            this.ws = new WebSocket(wsUrl);

            // 연결 타임아웃 설정 (5초)
            const connectionTimeout = setTimeout(() => {
                if (this.ws.readyState === WebSocket.CONNECTING) {
                    this.ws.close();
                    reject(new Error('연결 시간 초과'));
                }
            }, 5000);

            this.ws.onopen = () => {
                clearTimeout(connectionTimeout);
                console.log('WebSocket 연결 성공');
                this.isConnected = true;
                this.uiModule.updateConnectionStatus('연결됨', true);
                resolve();
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.messageHandler.handleMessage(data);
                } catch (error) {
                    console.error('메시지 파싱 오류:', error, event.data);
                }
            };

            this.ws.onclose = (event) => {
                clearTimeout(connectionTimeout);
                console.log('WebSocket 연결 종료:', event.code, event.reason);
                this.isConnected = false;
                this.uiModule.updateConnectionStatus('연결 끊김', false);

                if (this.isLoggingOut) {
                    // 로그아웃인 경우: 상태 초기화 후 로그인 화면으로 전환
                    console.log('로그아웃 완료 - 로그인 화면으로 전환');
                    this.isAuthenticated = false;
                    this.isAdmin = false;
                    this.isLoggingOut = false;
                    this.showScreen('login');
                } else if (this.isAuthenticated && event.code !== 1000) {
                    // 예상치 못한 연결 끊김인 경우: 재연결 시도 (정상 종료가 아닌 경우만)
                    console.log('연결 끊김 - 3초 후 재연결 시도');
                    setTimeout(() => this.connectWebSocket().catch(console.error), 3000);
                }
            };

            this.ws.onerror = (error) => {
                clearTimeout(connectionTimeout);
                console.error('WebSocket 오류:', error);
                this.uiModule.updateConnectionStatus('연결 오류', false);
                reject(error);
            };
        });
    }

    sendMessage(data) {
        if (this.ws && this.isConnected) {
            this.ws.send(JSON.stringify(data));
        }
    }

    sendCommand(command = null) {
        const input = document.getElementById('commandInput');
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

        // 입력창 초기화
        if (!command && input) {
            input.value = '';
        }

        // 서버로 전송
        this.sendMessage({
            type: 'command',
            command: cmd
        });

        // 게임 출력에 명령어 표시
        this.gameModule.addGameMessage(`> ${cmd}`, 'command');
    }

    showPreviousCommand() {
        if (this.historyIndex > 0) {
            this.historyIndex--;
            const input = document.getElementById('commandInput');
            if (input) {
                input.value = this.commandHistory[this.historyIndex];
            }
        }
    }

    showNextCommand() {
        if (this.historyIndex < this.commandHistory.length - 1) {
            this.historyIndex++;
            const input = document.getElementById('commandInput');
            if (input) {
                input.value = this.commandHistory[this.historyIndex];
            }
        } else {
            this.historyIndex = this.commandHistory.length;
            const input = document.getElementById('commandInput');
            if (input) {
                input.value = '';
            }
        }
    }

    logout() {
        // 로그아웃 플래그 설정 (재연결 방지)
        this.isLoggingOut = true;
        this.sendCommand('quit');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// 전역 변수로 export
window.MudClient = MudClient;