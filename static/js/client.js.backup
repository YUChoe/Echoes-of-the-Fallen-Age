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

        // 하이브리드 인터페이스 관련
        this.currentRoomId = null;

        // 관리자 관련
        this.isAdmin = false;

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
                this.showScreen('register');
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
                this.showScreen('login');
            });
        }

        // 게임 명령어 입력
        const commandInput = document.getElementById('commandInput');
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
        const sendBtn = document.getElementById('sendBtn');
        if (sendBtn) {
            sendBtn.addEventListener('click', () => {
                this.sendCommand();
            });
        }

        // 빠른 명령어 버튼들
        document.querySelectorAll('.cmd-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const cmd = btn.dataset.cmd;
                this.sendCommand(cmd);
            });
        });

        // 로그아웃 버튼
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                this.logout();
            });
        }

        // 관리자 버튼
        const adminBtn = document.getElementById('adminBtn');
        if (adminBtn) {
            adminBtn.addEventListener('click', () => {
                this.showAdminModal();
            });
        }

        // 관리자 모달 설정
        this.setupAdminModal();

        // 능력치 패널 설정
        this.setupStatsPanel();
    }

    showScreen(screenName) {
        // 모든 화면 숨기기
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.remove('active');
        });

        // 선택된 화면 표시
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
        const username = document.getElementById('regUsername').value.trim();
        const password = document.getElementById('regPassword').value;

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
                this.isAdmin = data.is_admin || false; // 관리자 권한 확인
                this.showScreen('game');
                this.updatePlayerInfo(data.username);
                this.addGameMessage(`${data.username}님, 환영합니다!`, 'success');

                // 관리자 버튼 표시/숨김
                this.updateAdminButton();

                // 초기 명령어 실행
                setTimeout(() => {
                    this.sendCommand('look');
                }, 500);

            } else {
                // 게임 명령어 성공 응답 처리 (look, move 등)
                if (data.message) {
                    this.addGameMessage(data.message, 'success');
                }

                // 능력치 명령어 응답 처리
                if (data.data && data.data.action === 'stats') {
                    this.updateStatsPanel(data.data);
                }

                // UI 업데이트가 필요한 경우
                if (data.data && data.data.ui_update_needed) {
                    // UI 업데이트 로직
                }
            }
        } else if (data.response) {
            this.addGameMessage(data.response, data.message_type || 'system');
        } else if (data.type === 'ui_update') {
            this.updateUI(data.ui);
        } else if (data.type === 'room_info') {
            this.addGameMessage(`📍 ${data.room.name}`, 'system');
            this.addGameMessage(data.room.description, 'info');
            this.currentRoomId = data.room.id;
        } else if (data.type === 'chat_message') {
            this.handleChatMessage(data);
        } else if (data.type === 'room_chat_message') {
            this.handleRoomChatMessage(data);
        } else if (data.type === 'private_message') {
            this.handlePrivateMessage(data);
        } else if (data.type === 'admin_response') {
            this.handleAdminResponse(data);
        } else if (data.type === 'room_players_update') {
            this.handleRoomPlayersUpdate(data);
        } else if (data.type === 'whisper_received') {
            this.handleWhisperReceived(data);
        } else if (data.type === 'item_received') {
            this.handleItemReceived(data);
        } else if (data.type === 'being_followed') {
            this.handleBeingFollowed(data);
        } else if (data.type === 'following_movement') {
            this.handleFollowingMovement(data);
        } else if (data.type === 'player_status_change') {
            this.handlePlayerStatusChange(data);
        } else if (data.type === 'room_message') {
            this.handleRoomMessage(data);
        } else if (data.type === 'system_message') {
            this.handleSystemMessage(data);
        } else if (data.type === 'follow_stopped') {
            this.handleFollowStopped(data);
        }
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

        // 입력 필드 클리어
        if (!command && input) {
            input.value = '';
        }

        // 서버로 전송
        this.sendMessage({
            command: cmd
        });

        // 게임 출력에 명령어 표시
        this.addGameMessage(`> ${cmd}`, 'command');
    }

    addGameMessage(message, type = 'system') {
        const output = document.getElementById('gameOutput');
        if (!output) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `game-message ${type}`;

        // 타임스탬프 추가
        const timestamp = new Date().toLocaleTimeString();
        messageDiv.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${this.escapeHtml(message)}`;

        output.appendChild(messageDiv);
        output.scrollTop = output.scrollHeight;

        // 메시지가 너무 많으면 오래된 것 제거
        const messages = output.querySelectorAll('.game-message');
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
            const input = document.getElementById('commandInput');
            if (input) {
                input.value = this.commandHistory[this.historyIndex];
            }
        }
    }

    showNextCommand() {
        const input = document.getElementById('commandInput');
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
        const statusElement = document.getElementById('connectionStatus');
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = `status ${isConnected ? 'connected' : 'disconnected'}`;
        }
    }

    updatePlayerInfo(username) {
        const playerInfo = document.getElementById('playerInfo');
        if (playerInfo) {
            playerInfo.textContent = `플레이어: ${username}`;
        }
    }

    showMessage(message, type, screen) {
        const messageElement = document.getElementById(`${screen}Message`);
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
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.reset();
        }

        // 게임 출력 초기화
        const gameOutput = document.getElementById('gameOutput');
        if (gameOutput) {
            gameOutput.innerHTML = '';
        }

        this.commandHistory = [];
        this.historyIndex = -1;
    }

    // === 하이브리드 인터페이스 메서드들 ===

    setupQuickCommandButtons() {
        document.querySelectorAll('.cmd_btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const cmd = btn.dataset.cmd;
                this.sendCommand(cmd);
            });
        });
    }

    updateUI(uiData) {
        console.log('UI 업데이트:', uiData);

        if (uiData.buttons) {
            this.updateQuickButtons(uiData.buttons);
        }

        if (uiData.room_id) {
            this.currentRoomId = uiData.room_id;
        }
    }

    updateQuickButtons(buttons) {
        const dynamicContainer = document.getElementById('dynamicButtons');
        if (!dynamicContainer) return;

        // 기존 버튼들 제거
        dynamicContainer.innerHTML = '';

        let hasButtons = false;

        // 출구 버튼들 추가
        if (buttons.exits && buttons.exits.length > 0) {
            buttons.exits.forEach(exit => {
                const btn = document.createElement('button');
                btn.className = 'dynamic-btn exit';
                btn.textContent = `${exit.icon} ${exit.text}`;
                btn.addEventListener('click', () => {
                    this.sendCommand(exit.command);
                });
                dynamicContainer.appendChild(btn);
                hasButtons = true;
            });
        }

        // 객체 버튼들 추가
        if (buttons.objects && buttons.objects.length > 0) {
            buttons.objects.forEach(obj => {
                const btn = document.createElement('button');
                btn.className = 'dynamic-btn object';
                btn.textContent = `${obj.icon} ${obj.text}`;
                btn.addEventListener('click', () => {
                    this.sendCommand(obj.command);
                });
                dynamicContainer.appendChild(btn);
                hasButtons = true;
            });
        }

        // 버튼이 있으면 컨테이너 표시, 없으면 숨김
        dynamicContainer.style.display = hasButtons ? 'flex' : 'none';
    }

    // === 관리자 기능 메서드들 ===

    updateAdminButton() {
        const adminBtn = document.getElementById('adminBtn');
        if (adminBtn) {
            adminBtn.style.display = this.isAdmin ? 'block' : 'none';
        }
    }

    setupAdminModal() {
        // 모달 닫기 버튼
        const closeBtn = document.getElementById('closeAdminModal');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.hideAdminModal();
            });
        }

        // 모달 외부 클릭 시 닫기
        const modal = document.getElementById('adminModal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hideAdminModal();
                }
            });
        }

        // 탭 버튼들
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.switchAdminTab(btn.dataset.tab);
            });
        });

        // 관리자 폼들 설정
        this.setupAdminForms();
    }

    setupAdminForms() {
        // 방 생성 폼
        const createRoomForm = document.getElementById('createRoomForm');
        if (createRoomForm) {
            createRoomForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleCreateRoom();
            });
        }

        // 방 편집 폼
        const editRoomForm = document.getElementById('editRoomForm');
        if (editRoomForm) {
            editRoomForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleEditRoom();
            });
        }

        // 출구 생성 폼
        const createExitForm = document.getElementById('createExitForm');
        if (createExitForm) {
            createExitForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleCreateExit();
            });
        }

        // 객체 생성 폼
        const createObjectForm = document.getElementById('createObjectForm');
        if (createObjectForm) {
            createObjectForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleCreateObject();
            });
        }

        // 플레이어 추방 폼
        const kickPlayerForm = document.getElementById('kickPlayerForm');
        if (kickPlayerForm) {
            kickPlayerForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleKickPlayer();
            });
        }

        // 목록 새로고침 버튼들
        const refreshPlayersBtn = document.getElementById('refreshPlayers');
        if (refreshPlayersBtn) {
            refreshPlayersBtn.addEventListener('click', () => {
                this.loadPlayersList();
            });
        }

        const refreshRoomsBtn = document.getElementById('refreshRooms');
        if (refreshRoomsBtn) {
            refreshRoomsBtn.addEventListener('click', () => {
                this.loadRoomsList();
            });
        }

        const refreshObjectsBtn = document.getElementById('refreshObjects');
        if (refreshObjectsBtn) {
            refreshObjectsBtn.addEventListener('click', () => {
                this.loadObjectsList();
            });
        }

        // 플레이어 필터
        const playerFilter = document.getElementById('playerFilter');
        if (playerFilter) {
            playerFilter.addEventListener('change', () => {
                this.filterPlayersList();
            });
        }
    }

    showAdminModal() {
        const modal = document.getElementById('adminModal');
        if (modal) {
            modal.classList.add('active');
            // 모달이 열릴 때 현재 활성 탭의 데이터 로드
            const activeTab = document.querySelector('.tab-btn.active');
            if (activeTab) {
                this.loadTabData(activeTab.dataset.tab);
            }
        }
    }

    hideAdminModal() {
        const modal = document.getElementById('adminModal');
        if (modal) {
            modal.classList.remove('active');
        }
    }

    switchAdminTab(tabName) {
        // 모든 탭 버튼 비활성화
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });

        // 모든 탭 콘텐츠 숨기기
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });

        // 선택된 탭 활성화
        const selectedBtn = document.querySelector(`[data-tab="${tabName}"]`);
        const selectedContent = document.getElementById(`${tabName}Tab`);

        if (selectedBtn) selectedBtn.classList.add('active');
        if (selectedContent) selectedContent.classList.add('active');

        // 탭 데이터 로드
        this.loadTabData(tabName);
    }

    loadTabData(tabName) {
        switch (tabName) {
            case 'rooms':
                this.loadRoomsList();
                break;
            case 'objects':
                this.loadObjectsList();
                break;
            case 'players':
                this.loadPlayersList();
                break;
        }
    }

    // 관리자 폼 핸들러들
    handleCreateRoom() {
        const roomId = document.getElementById('roomId').value.trim();
        const roomName = document.getElementById('roomName').value.trim();
        const roomDescription = document.getElementById('roomDescription').value.trim();

        if (!roomId || !roomName) {
            this.showAdminAlert('방 ID와 이름은 필수입니다.', 'error');
            return;
        }

        let command = `createroom ${roomId} ${roomName}`;
        if (roomDescription) {
            command += ` ${roomDescription}`;
        }

        this.sendAdminCommand(command, 'createroom');
    }

    handleEditRoom() {
        const roomId = document.getElementById('editRoomId').value.trim();
        const property = document.getElementById('editProperty').value;
        const value = document.getElementById('editValue').value.trim();

        if (!roomId || !property || !value) {
            this.showAdminAlert('모든 필드를 입력해주세요.', 'error');
            return;
        }

        const command = `editroom ${roomId} ${property} ${value}`;
        this.sendAdminCommand(command, 'editroom');
    }

    handleCreateExit() {
        const fromRoom = document.getElementById('fromRoom').value.trim();
        const direction = document.getElementById('direction').value;
        const toRoom = document.getElementById('toRoom').value.trim();

        if (!fromRoom || !direction || !toRoom) {
            this.showAdminAlert('모든 필드를 입력해주세요.', 'error');
            return;
        }

        const command = `createexit ${fromRoom} ${direction} ${toRoom}`;
        this.sendAdminCommand(command, 'createexit');
    }

    handleCreateObject() {
        const objectId = document.getElementById('objectId').value.trim();
        const objectName = document.getElementById('objectName').value.trim();
        const objectType = document.getElementById('objectType').value;
        const objectLocation = document.getElementById('objectLocation').value.trim();

        if (!objectId || !objectName || !objectType) {
            this.showAdminAlert('객체 ID, 이름, 타입은 필수입니다.', 'error');
            return;
        }

        let command = `createobject ${objectId} ${objectName} ${objectType}`;
        if (objectLocation) {
            command += ` ${objectLocation}`;
        }

        this.sendAdminCommand(command, 'createobject');
    }

    handleKickPlayer() {
        const username = document.getElementById('kickUsername').value.trim();
        const reason = document.getElementById('kickReason').value.trim();

        if (!username) {
            this.showAdminAlert('플레이어명을 입력해주세요.', 'error');
            return;
        }

        if (!confirm(`정말로 플레이어 '${username}'을 추방하시겠습니까?`)) {
            return;
        }

        let command = `kick ${username}`;
        if (reason) {
            command += ` ${reason}`;
        }

        this.sendAdminCommand(command, 'kick');
    }

    // === 목록 로드 메서드들 ===

    async loadRoomsList() {
        const container = document.getElementById('roomsList');
        if (!container) return;

        this.showLoadingMessage(container);

        try {
            const response = await fetch('/api/admin/rooms');
            const data = await response.json();

            if (data.success) {
                this.displayRoomsList(data.rooms);
            } else {
                this.showErrorMessage(container, data.error || '방 목록을 불러올 수 없습니다.');
            }
        } catch (error) {
            console.error('방 목록 로드 오류:', error);
            this.showErrorMessage(container, '서버 연결 오류가 발생했습니다.');
        }
    }

    async loadObjectsList() {
        const container = document.getElementById('objectsList');
        if (!container) return;

        this.showLoadingMessage(container);

        try {
            const response = await fetch('/api/admin/objects');
            const data = await response.json();

            if (data.success) {
                this.displayObjectsList(data.objects);
            } else {
                this.showErrorMessage(container, data.error || '객체 목록을 불러올 수 없습니다.');
            }
        } catch (error) {
            console.error('객체 목록 로드 오류:', error);
            this.showErrorMessage(container, '서버 연결 오류가 발생했습니다.');
        }
    }

    async loadPlayersList() {
        const container = document.getElementById('playersList');
        if (!container) return;

        this.showLoadingMessage(container);

        try {
            const response = await fetch('/api/admin/players');
            const data = await response.json();

            if (data.success) {
                this.allPlayersData = data; // 필터링을 위해 저장
                this.displayPlayersList(data);
            } else {
                this.showErrorMessage(container, data.error || '플레이어 목록을 불러올 수 없습니다.');
            }
        } catch (error) {
            console.error('플레이어 목록 로드 오류:', error);
            this.showErrorMessage(container, '서버 연결 오류가 발생했습니다.');
        }
    }

    // === 목록 표시 메서드들 ===

    displayRoomsList(rooms) {
        const container = document.getElementById('roomsList');
        if (!container) return;

        if (rooms.length === 0) {
            this.showEmptyMessage(container, '등록된 방이 없습니다.');
            return;
        }

        container.innerHTML = '';

        rooms.forEach(room => {
            const roomDiv = document.createElement('div');
            roomDiv.className = 'data-item';

            const nameKo = room.name.ko || room.name.en || '이름 없음';
            const descKo = room.description.ko || room.description.en || '설명 없음';
            const exitCount = Object.keys(room.exits || {}).length;

            roomDiv.innerHTML = `
                <div class="data-item-header">
                    <div class="data-item-title">${this.escapeHtml(nameKo)}</div>
                    <div class="data-item-id">${this.escapeHtml(room.id)}</div>
                </div>
                <div class="data-item-content">
                    <div class="data-item-description">${this.escapeHtml(descKo)}</div>
                </div>
                <div class="data-item-meta">
                    <span>🚪 출구: ${exitCount}개</span>
                    <span>📦 객체: ${room.object_count || 0}개</span>
                    <span>📅 생성: ${this.formatDate(room.created_at)}</span>
                </div>
            `;

            container.appendChild(roomDiv);
        });
    }

    displayObjectsList(objects) {
        const container = document.getElementById('objectsList');
        if (!container) return;

        if (objects.length === 0) {
            this.showEmptyMessage(container, '등록된 객체가 없습니다.');
            return;
        }

        container.innerHTML = '';

        objects.forEach(obj => {
            const objDiv = document.createElement('div');
            objDiv.className = 'data-item';

            const nameKo = obj.name.ko || obj.name.en || '이름 없음';
            const descKo = obj.description.ko || obj.description.en || '설명 없음';

            objDiv.innerHTML = `
                <div class="data-item-header">
                    <div class="data-item-title">${this.escapeHtml(nameKo)}</div>
                    <div class="data-item-id">${this.escapeHtml(obj.id)}</div>
                </div>
                <div class="data-item-content">
                    <div class="data-item-description">${this.escapeHtml(descKo)}</div>
                    <div class="type-badge">${this.escapeHtml(obj.object_type)}</div>
                </div>
                <div class="data-item-meta">
                    <span>📍 위치: ${this.escapeHtml(obj.location_name || '알 수 없음')}</span>
                    <span>📅 생성: ${this.formatDate(obj.created_at)}</span>
                </div>
            `;

            container.appendChild(objDiv);
        });
    }

    displayPlayersList(data) {
        const container = document.getElementById('playersList');
        if (!container) return;

        const allPlayers = data.all_players || [];
        const onlinePlayers = data.online_players || [];

        if (allPlayers.length === 0) {
            this.showEmptyMessage(container, '등록된 플레이어가 없습니다.');
            return;
        }

        // 온라인 플레이어 ID 맵 생성
        const onlinePlayerIds = new Set(onlinePlayers.map(p => p.id));

        // 모든 플레이어에 온라인 상태 추가
        const playersWithStatus = allPlayers.map(player => {
            const onlinePlayer = onlinePlayers.find(op => op.id === player.id);
            return {
                ...player,
                status: onlinePlayerIds.has(player.id) ? 'online' : 'offline',
                current_room_name: onlinePlayer?.current_room_name || null,
                session_id: onlinePlayer?.session_id || null,
                ip_address: onlinePlayer?.ip_address || null
            };
        });

        this.filteredPlayersData = playersWithStatus;
        this.filterPlayersList();
    }

    filterPlayersList() {
        const container = document.getElementById('playersList');
        const filter = document.getElementById('playerFilter');

        if (!container || !filter || !this.filteredPlayersData) return;

        const filterValue = filter.value;
        let playersToShow = this.filteredPlayersData;

        // 필터 적용
        switch (filterValue) {
            case 'online':
                playersToShow = this.filteredPlayersData.filter(p => p.status === 'online');
                break;
            case 'offline':
                playersToShow = this.filteredPlayersData.filter(p => p.status === 'offline');
                break;
            case 'admin':
                playersToShow = this.filteredPlayersData.filter(p => p.is_admin);
                break;
            case 'all':
            default:
                // 모든 플레이어 표시
                break;
        }

        if (playersToShow.length === 0) {
            this.showEmptyMessage(container, '조건에 맞는 플레이어가 없습니다.');
            return;
        }

        container.innerHTML = '';

        playersToShow.forEach(player => {
            const playerDiv = document.createElement('div');
            playerDiv.className = 'data-item';

            const statusBadge = player.status === 'online' ?
                '<span class="status-badge online">온라인</span>' :
                '<span class="status-badge offline">오프라인</span>';

            const adminBadge = player.is_admin ?
                '<span class="status-badge admin">관리자</span>' : '';

            const roomInfo = player.current_room_name ?
                `<span>📍 현재 위치: ${this.escapeHtml(player.current_room_name)}</span>` : '';

            const lastLogin = player.last_login ?
                `<span>🕒 마지막 로그인: ${this.formatDate(player.last_login)}</span>` : '';

            playerDiv.innerHTML = `
                <div class="data-item-header">
                    <div class="data-item-title">${this.escapeHtml(player.username)}</div>
                    <div>
                        ${statusBadge}
                        ${adminBadge}
                    </div>
                </div>
                <div class="data-item-content">
                    <div class="data-item-meta">
                        <span>🌐 언어: ${player.preferred_locale}</span>
                        ${roomInfo}
                        <span>📅 가입: ${this.formatDate(player.created_at)}</span>
                        ${lastLogin}
                    </div>
                </div>
            `;

            container.appendChild(playerDiv);
        });
    }

    // === 유틸리티 메서드들 ===

    showLoadingMessage(container) {
        container.innerHTML = '<div class="loading-message">로딩 중...</div>';
    }

    showEmptyMessage(container, message) {
        container.innerHTML = `<div class="empty-message">${this.escapeHtml(message)}</div>`;
    }

    showErrorMessage(container, message) {
        container.innerHTML = `<div class="error-message">${this.escapeHtml(message)}</div>`;
    }

    formatDate(dateString) {
        if (!dateString) return '알 수 없음';

        try {
            const date = new Date(dateString);
            return date.toLocaleString('ko-KR', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (error) {
            return '날짜 오류';
        }
    }

    sendAdminCommand(command, action) {
        // 관리자 명령어 전송 (일반 명령어와 구분하기 위해)
        this.sendMessage({
            command: command,
            admin_action: action
        });

        // 게임 출력에도 표시
        this.addGameMessage(`> ${command}`, 'command');
    }

    handleAdminResponse(data) {
        // 관리자 명령어 응답 처리
        const action = data.admin_action;
        const success = data.success;
        const message = data.message;

        if (success) {
            this.showAdminAlert(message, 'success');

            // 성공 시 해당 폼 초기화
            switch (action) {
                case 'createroom':
                    this.clearForm('createRoomForm');
                    break;
                case 'editroom':
                    this.clearForm('editRoomForm');
                    break;
                case 'createexit':
                    this.clearForm('createExitForm');
                    break;
                case 'createobject':
                    this.clearForm('createObjectForm');
                    break;
                case 'kick':
                    this.clearForm('kickPlayerForm');
                    this.refreshPlayersList();
                    break;
            }
        } else {
            this.showAdminAlert(message, 'error');
        }

        // 게임 출력에도 표시
        this.addGameMessage(message, success ? 'success' : 'error');
    }

    showAdminAlert(message, type) {
        // 관리자 패널 내에서 알림 표시
        const alertDiv = document.createElement('div');
        alertDiv.className = `admin-alert ${type}`;
        alertDiv.textContent = message;

        // 모달 헤더 아래에 알림 추가
        const modalBody = document.querySelector('.modal-body');
        if (modalBody) {
            modalBody.insertBefore(alertDiv, modalBody.firstChild);

            // 3초 후 자동 제거
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.parentNode.removeChild(alertDiv);
                }
            }, 3000);
        }
    }

    clearForm(formId) {
        const form = document.getElementById(formId);
        if (form) {
            form.reset();
        }
    }

    // 채팅 메시지 핸들러들 (누락된 메서드들)
    handleChatMessage(data) {
        // 채팅 메시지 처리
        const message = data.message;
        const formattedMessage = message.format_for_display ?
            message.format_for_display :
            `[${data.channel}] ${message.sender_name}: ${message.content}`;

        this.addGameMessage(formattedMessage, 'chat');
    }

    handleRoomChatMessage(data) {
        // 방 채팅 메시지 처리
        const message = data.message;
        const formattedMessage = message.format_for_display ?
            message.format_for_display :
            `${message.sender_name}: ${message.content}`;

        this.addGameMessage(formattedMessage, 'chat');
    }

    handlePrivateMessage(data) {
        // 개인 메시지 처리
        const message = data.message;
        const formattedMessage = message.format_for_display ?
            message.format_for_display :
            `[귓속말] ${message.sender_name}: ${message.content}`;

        this.addGameMessage(formattedMessage, 'chat');
    }

    handleRoomMessage(data) {
        // 방 메시지 처리 (플레이어 이동 알림 등)
        this.addGameMessage(data.message, 'info');
    }

    handleSystemMessage(data) {
        // 시스템 메시지 처리 (로그인/로그아웃 알림 등)
        this.addGameMessage(data.message, 'system');
    }

    handleRoomPlayersUpdate(data) {
        // 방 플레이어 목록 업데이트 처리
        console.log('방 플레이어 목록 업데이트:', data);
        // 필요시 UI 업데이트 로직 추가
    }

    handleWhisperReceived(data) {
        // 귓속말 수신 처리
        this.addGameMessage(data.message, 'whisper');
    }

    handleItemReceived(data) {
        // 아이템 수신 처리
        this.addGameMessage(data.message, 'item');
    }

    handleBeingFollowed(data) {
        // 따라가기 당하는 상황 처리
        this.addGameMessage(data.message, 'follow');
    }

    handleFollowingMovement(data) {
        // 따라가기 이동 처리
        this.addGameMessage(data.message, 'follow');
    }

    handlePlayerStatusChange(data) {
        // 플레이어 상태 변경 처리
        this.addGameMessage(data.message, 'status');
    }

    handleRoomMessage(data) {
        // 방 메시지 처리
        this.addGameMessage(data.message, 'info');
    }

    handleSystemMessage(data) {
        // 시스템 메시지 처리
        this.addGameMessage(data.message, 'system');
    }

    handleFollowStopped(data) {
        // 따라가기 중지 처리
        this.addGameMessage(data.message, 'warning');
    }

    // === 능력치 시스템 관련 메서드들 ===

    setupStatsPanel() {
        // 능력치 버튼 클릭 이벤트
        const statsBtn = document.getElementById('statsBtn');
        const statsModal = document.getElementById('statsModal');
        const closeBtn = document.getElementById('closeStatsModal');

        if (statsBtn && statsModal) {
            statsBtn.addEventListener('click', () => {
                this.showStatsModal();
            });
        }

        if (closeBtn && statsModal) {
            closeBtn.addEventListener('click', () => {
                this.hideStatsModal();
            });
        }

        // 모달 외부 클릭 시 닫기
        if (statsModal) {
            statsModal.addEventListener('click', (e) => {
                if (e.target === statsModal) {
                    this.hideStatsModal();
                }
            });
        }

        // 능력치 모달 내 버튼 이벤트
        const statsActions = document.querySelector('.stats-actions');
        if (statsActions) {
            statsActions.addEventListener('click', (e) => {
                if (e.target.hasAttribute('data-cmd')) {
                    const command = e.target.getAttribute('data-cmd');
                    this.sendCommand(command);
                }
            });
        }

        // 초기 능력치 요청
        this.requestStatsUpdate();
    }

    showStatsModal() {
        const modal = document.getElementById('statsModal');
        if (modal) {
            modal.style.display = 'block';
            // 모달 열 때마다 최신 능력치 정보 요청
            this.requestStatsUpdate();
        }
    }

    hideStatsModal() {
        const modal = document.getElementById('statsModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    requestStatsUpdate() {
        // stats 명령어를 자동으로 실행하여 능력치 정보 가져오기
        if (this.isAuthenticated) {
            this.sendMessage({
                type: 'command',
                command: 'stats'
            });
        }
    }

    updateStatsPanel(statsData) {
        console.log('능력치 패널 업데이트:', statsData);

        if (!statsData || !statsData.stats) {
            console.warn('능력치 데이터가 없습니다');
            return;
        }

        const stats = statsData.stats;

        // 기본 정보 업데이트
        this.updateStatElement('statLevel', stats.level || 1);
        this.updateStatElement('statExp', `${(stats.experience || 0).toLocaleString()} / ${(stats.experience_to_next || 100).toLocaleString()}`);

        // 경험치 바 업데이트
        const expPercent = stats.experience_to_next > 0 ?
            ((stats.experience || 0) / (stats.experience_to_next || 100)) * 100 : 0;
        const expFill = document.getElementById('expFill');
        if (expFill) {
            expFill.style.width = `${Math.min(100, expPercent)}%`;
        }

        // 1차 능력치 업데이트
        this.updateStatElement('statStr', stats.strength || 10);
        this.updateStatElement('statDex', stats.dexterity || 10);
        this.updateStatElement('statInt', stats.intelligence || 10);
        this.updateStatElement('statWis', stats.wisdom || 10);
        this.updateStatElement('statCon', stats.constitution || 10);
        this.updateStatElement('statCha', stats.charisma || 10);

        // 2차 능력치 업데이트
        this.updateStatElement('statHp', stats.health_points || 150);
        this.updateStatElement('statMp', stats.mana_points || 105);
        this.updateStatElement('statSta', stats.stamina || 150);
        this.updateStatElement('statAtk', stats.attack || 31);
        this.updateStatElement('statDef', stats.defense || 20);
        this.updateStatElement('statSpd', stats.speed || 25);
        this.updateStatElement('statRes', stats.resistance || 20);

        // 기타 능력치 업데이트
        this.updateStatElement('statLck', stats.luck || 20);
        this.updateStatElement('statInf', stats.influence || 25);
        this.updateStatElement('statCarryWeight', `${stats.max_carry_weight || 100}kg`);
    }

    updateStatElement(elementId, value, animate = true) {
        const element = document.getElementById(elementId);
        if (!element) {
            console.warn(`능력치 요소를 찾을 수 없습니다: ${elementId}`);
            return;
        }

        const oldValue = element.textContent;
        element.textContent = value;

        // 값이 변경되었고 애니메이션이 활성화된 경우
        if (animate && oldValue !== value.toString()) {
            element.classList.add('updated');
            setTimeout(() => {
                element.classList.remove('updated');
            }, 600);

            // 능력치 값에 따른 색상 적용
            this.applyStatColor(element, value);
        }
    }

    applyStatColor(element, value) {
        // 숫자 값 추출 (문자열에서 숫자만)
        const numValue = typeof value === 'string' ?
            parseInt(value.replace(/[^\d]/g, '')) : value;

        if (isNaN(numValue)) return;

        // 기존 색상 클래스 제거
        element.classList.remove('high', 'medium', 'low');

        // 능력치 범위에 따른 색상 적용
        if (numValue >= 80) {
            element.classList.add('high');
        } else if (numValue >= 40) {
            element.classList.add('medium');
        } else if (numValue < 20) {
            element.classList.add('low');
        }
    }

    handleStatsCommand(data) {
        // stats 명령어 응답 처리
        if (data.data && data.data.action === 'stats') {
            this.updateStatsPanel(data.data);
        }
    }

}

// 클라이언트 초기화
document.addEventListener('DOMContentLoaded', async () => {
    window.mudClient = new MudClient();
});