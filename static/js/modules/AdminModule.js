/**
 * 관리자 기능 모듈
 */

class AdminModule {
    constructor(client) {
        this.client = client;
    }

    setupEventListeners() {
        // 관리자 버튼
        const adminBtn = document.getElementById('adminBtn');
        if (adminBtn) {
            adminBtn.addEventListener('click', () => {
                this.showAdminModal();
            });
        }

        this.setupAdminModal();
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

    // 방 관련 메서드들
    async loadRoomsList() {
        const container = document.getElementById('roomsList');
        if (!container) return;

        this.client.uiModule.showLoadingMessage(container);

        try {
            const response = await fetch('/api/admin/rooms');
            if (!response.ok) throw new Error('방 목록 로드 실패');

            const data = await response.json();
            this.displayRoomsList(data.rooms || []);
        } catch (error) {
            console.error('방 목록 로드 오류:', error);
            this.client.uiModule.showErrorMessage(container, '방 목록을 불러올 수 없습니다.');
        }
    }

    displayRoomsList(rooms) {
        const container = document.getElementById('roomsList');
        if (!container) return;

        if (rooms.length === 0) {
            this.client.uiModule.showEmptyMessage(container, '등록된 방이 없습니다.');
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
                    <div class="data-item-title">${this.client.escapeHtml(nameKo)}</div>
                    <div class="data-item-id">${this.client.escapeHtml(room.id)}</div>
                </div>
                <div class="data-item-content">
                    <div class="data-item-description">${this.client.escapeHtml(descKo)}</div>
                </div>
                <div class="data-item-meta">
                    <span>📅 생성: ${this.client.uiModule.formatDate(room.created_at)}</span>
                    <span>🚪 출구: ${exitCount}개</span>
                    <span>📦 객체: ${room.object_count || 0}개</span>
                </div>
            `;

            container.appendChild(roomDiv);
        });
    }

    async handleCreateRoom() {
        const roomId = document.getElementById('roomId')?.value.trim();
        const roomName = document.getElementById('roomName')?.value.trim();
        const roomDescription = document.getElementById('roomDescription')?.value.trim();

        if (!roomId || !roomName) {
            alert('방 ID와 이름을 입력해주세요.');
            return;
        }

        const command = `createroom ${roomId} "${roomName}"${roomDescription ? ` "${roomDescription}"` : ''}`;
        this.client.sendCommand(command);

        // 폼 초기화
        document.getElementById('createRoomForm')?.reset();
    }

    async handleEditRoom() {
        const roomId = document.getElementById('editRoomId')?.value.trim();
        const property = document.getElementById('editProperty')?.value;
        const value = document.getElementById('editValue')?.value.trim();

        if (!roomId || !property || !value) {
            alert('모든 필드를 입력해주세요.');
            return;
        }

        const command = `editroom ${roomId} ${property} "${value}"`;
        this.client.sendCommand(command);

        // 폼 초기화
        document.getElementById('editRoomForm')?.reset();
    }

    async handleCreateExit() {
        const fromRoom = document.getElementById('fromRoom')?.value.trim();
        const direction = document.getElementById('direction')?.value;
        const toRoom = document.getElementById('toRoom')?.value.trim();

        if (!fromRoom || !direction || !toRoom) {
            alert('모든 필드를 입력해주세요.');
            return;
        }

        const command = `createexit ${fromRoom} ${direction} ${toRoom}`;
        this.client.sendCommand(command);

        // 폼 초기화
        document.getElementById('createExitForm')?.reset();
    }

    // 객체 관련 메서드들
    async loadObjectsList() {
        const container = document.getElementById('objectsList');
        if (!container) return;

        this.client.uiModule.showLoadingMessage(container);

        try {
            const response = await fetch('/api/admin/objects');
            if (!response.ok) throw new Error('객체 목록 로드 실패');

            const data = await response.json();
            this.displayObjectsList(data.objects || []);
        } catch (error) {
            console.error('객체 목록 로드 오류:', error);
            this.client.uiModule.showErrorMessage(container, '객체 목록을 불러올 수 없습니다.');
        }
    }

    displayObjectsList(objects) {
        const container = document.getElementById('objectsList');
        if (!container) return;

        if (objects.length === 0) {
            this.client.uiModule.showEmptyMessage(container, '등록된 객체가 없습니다.');
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
                    <div class="data-item-title">${this.client.escapeHtml(nameKo)}</div>
                    <div class="data-item-id">${this.client.escapeHtml(obj.id)}</div>
                </div>
                <div class="data-item-content">
                    <div class="data-item-description">${this.client.escapeHtml(descKo)}</div>
                    <div class="type-badge">${this.client.escapeHtml(obj.object_type)}</div>
                </div>
                <div class="data-item-meta">
                    <span>📅 생성: ${this.client.uiModule.formatDate(obj.created_at)}</span>
                    <span>📍 위치: ${this.client.escapeHtml(obj.location_name || '알 수 없음')}</span>
                    <span>📅 생성: ${this.client.uiModule.formatDate(obj.created_at)}</span>
                </div>
            `;

            container.appendChild(objDiv);
        });
    }

    async handleCreateObject() {
        const objectId = document.getElementById('objectId')?.value.trim();
        const objectName = document.getElementById('objectName')?.value.trim();
        const objectType = document.getElementById('objectType')?.value;
        const objectLocation = document.getElementById('objectLocation')?.value.trim();

        if (!objectId || !objectName || !objectType) {
            alert('객체 ID, 이름, 타입을 입력해주세요.');
            return;
        }

        const command = `createobject ${objectId} "${objectName}" ${objectType}${objectLocation ? ` ${objectLocation}` : ''}`;
        this.client.sendCommand(command);

        // 폼 초기화
        document.getElementById('createObjectForm')?.reset();
    }

    // 플레이어 관련 메서드들
    async loadPlayersList() {
        const container = document.getElementById('playersList');
        if (!container) return;

        this.client.uiModule.showLoadingMessage(container);

        try {
            const response = await fetch('/api/admin/players');
            if (!response.ok) throw new Error('플레이어 목록 로드 실패');

            const data = await response.json();
            this.displayPlayersList(data.players || []);
        } catch (error) {
            console.error('플레이어 목록 로드 오류:', error);
            this.client.uiModule.showErrorMessage(container, '플레이어 목록을 불러올 수 없습니다.');
        }
    }

    displayPlayersList(players) {
        const container = document.getElementById('playersList');
        if (!container) return;

        if (players.length === 0) {
            this.client.uiModule.showEmptyMessage(container, '등록된 플레이어가 없습니다.');
            return;
        }

        // 필터 적용
        const filter = document.getElementById('playerFilter')?.value || 'all';
        const filteredPlayers = this.filterPlayers(players, filter);

        container.innerHTML = '';
        filteredPlayers.forEach(player => {
            const playerDiv = document.createElement('div');
            playerDiv.className = 'data-item';

            const statusBadge = player.status === 'online' ?
                '<span class="status-badge online">온라인</span>' :
                '<span class="status-badge offline">오프라인</span>';

            const adminBadge = player.is_admin ?
                '<span class="status-badge admin">관리자</span>' : '';

            const roomInfo = player.current_room_name ?
                `<span>📍 위치: ${this.client.escapeHtml(player.current_room_name)}</span>` :
                '<span>📍 위치: 알 수 없음</span>';

            playerDiv.innerHTML = `
                <div class="data-item-header">
                    <div class="data-item-title">${this.client.escapeHtml(player.username)}</div>
                    <div>
                        ${statusBadge}
                        ${adminBadge}
                    </div>
                </div>
                <div class="data-item-content">
                    <div class="data-item-meta">
                        <span>📅 가입: ${this.client.uiModule.formatDate(player.created_at)}</span>
                        <span>🌐 언어: ${player.preferred_locale}</span>
                        ${roomInfo}
                    </div>
                </div>
            `;

            container.appendChild(playerDiv);
        });
    }

    filterPlayers(players, filter) {
        switch (filter) {
            case 'online':
                return players.filter(p => p.status === 'online');
            case 'offline':
                return players.filter(p => p.status === 'offline');
            case 'admin':
                return players.filter(p => p.is_admin);
            default:
                return players;
        }
    }

    filterPlayersList() {
        // 현재 로드된 데이터로 필터링 (재로드 없이)
        this.loadPlayersList();
    }

    async handleKickPlayer() {
        const username = document.getElementById('kickUsername')?.value.trim();
        const reason = document.getElementById('kickReason')?.value.trim();

        if (!username) {
            alert('추방할 플레이어명을 입력해주세요.');
            return;
        }

        const command = `kick ${username}${reason ? ` "${reason}"` : ''}`;
        this.client.sendCommand(command);

        // 폼 초기화
        document.getElementById('kickPlayerForm')?.reset();
    }
}

// 전역 변수로 export
window.AdminModule = AdminModule;