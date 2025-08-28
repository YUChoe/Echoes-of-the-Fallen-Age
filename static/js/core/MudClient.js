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
        this.commandBuilderModule = null;

        // 명령어 조합 모드 상태
        this.isCommandBuilderMode = true;

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
        this.commandBuilderModule = new CommandBuilderModule(this);
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

        // 명령어 조합 모드 토글 버튼
        const toggleBtn = document.getElementById('toggleCommandBuilder');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                this.toggleCommandBuilderMode();
            });
        }
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

            // 게임 화면 전환 시 모든 UI 요소를 초기화하고 올바른 모드 활성화
            this.initializeGameUI();
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

    // 게임 UI 초기화
    initializeGameUI() {
        // 인라인 스타일 제거 (CSS 클래스가 제어하도록)
        const commandBuilder = document.getElementById('commandBuilder');
        const dynamicButtons = document.getElementById('dynamicButtons');
        const inputContainer = document.querySelector('.input-container');

        if (commandBuilder) {
            commandBuilder.style.display = '';
        }
        if (dynamicButtons) {
            dynamicButtons.style.display = '';
        }
        if (inputContainer) {
            inputContainer.style.display = '';
        }

        // 즉시 올바른 모드 활성화
        if (this.isCommandBuilderMode) {
            this.activateCommandBuilderMode();
        } else {
            this.activateNormalMode();
        }
    }

    // 명령어 조합 모드 활성화
    activateCommandBuilderMode() {
        const toggleBtn = document.getElementById('toggleCommandBuilder');

        // body 클래스로 모드 제어
        document.body.className = 'command-builder-active';

        if (toggleBtn) {
            toggleBtn.classList.add('active');
            toggleBtn.textContent = '📝 일반 모드';
        }

        // 명령어 조합 컨텍스트 업데이트
        this.updateCommandBuilderContext();
    }

    // 일반 모드 활성화
    activateNormalMode() {
        const toggleBtn = document.getElementById('toggleCommandBuilder');

        // body 클래스로 모드 제어
        document.body.className = 'normal-mode-active';

        if (toggleBtn) {
            toggleBtn.classList.remove('active');
            toggleBtn.textContent = '🎯 명령어 조합 모드';
        }
    }

    // 명령어 조합 모드 토글
    toggleCommandBuilderMode() {
        this.isCommandBuilderMode = !this.isCommandBuilderMode;

        if (this.isCommandBuilderMode) {
            this.activateCommandBuilderMode();
        } else {
            this.activateNormalMode();
        }
    }

    // 명령어 조합 시스템의 컨텍스트 업데이트
    updateCommandBuilderContext() {
        if (!this.commandBuilderModule || !this.isCommandBuilderMode) return;

        // 현재 게임 상태를 기반으로 컨텍스트 생성
        const context = {
            exits: this.currentRoomExits || [],
            objects: this.currentRoomObjects || [],
            inventory: this.currentInventory || [],
            players: this.currentRoomPlayers || [],
            npcs: this.currentRoomNPCs || [],
            hasExits: (this.currentRoomExits || []).length > 0,
            hasRoomObjects: (this.currentRoomObjects || []).length > 0,
            hasInventoryItems: (this.currentInventory || []).length > 0,
            hasOtherPlayers: (this.currentRoomPlayers || []).length > 0,
            hasNPCs: (this.currentRoomNPCs || []).length > 0
        };

        this.commandBuilderModule.updateAvailableCommands(context);
    }

    // 게임 상태 업데이트 메서드들
    updateRoomContext(roomData) {
        this.currentRoomExits = roomData.exits ? Object.keys(roomData.exits) : [];
        this.currentRoomObjects = roomData.objects || [];
        this.currentRoomPlayers = roomData.players || [];
        this.currentRoomNPCs = roomData.npcs || [];



        // 명령어 조합 모드가 활성화되어 있으면 컨텍스트 업데이트
        if (this.isCommandBuilderMode) {
            this.updateCommandBuilderContext();
        }
    }

    updateInventoryContext(inventoryData) {
        this.currentInventory = inventoryData || [];

        // 명령어 조합 모드가 활성화되어 있으면 컨텍스트 업데이트
        if (this.isCommandBuilderMode) {
            this.updateCommandBuilderContext();
        }
    }
}

// 전역 변수로 export
window.MudClient = MudClient;