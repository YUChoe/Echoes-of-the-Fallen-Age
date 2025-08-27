/**
 * 게임 관련 모듈 (메시지 처리, 명령어, UI 업데이트)
 */

class GameModule {
    constructor(client) {
        this.client = client;
    }

    setupEventListeners() {
        // 게임 명령어 입력
        const commandInput = document.getElementById('commandInput');
        if (commandInput) {
            commandInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.client.sendCommand();
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    this.client.showPreviousCommand();
                } else if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    this.client.showNextCommand();
                }
            });
        }

        // 전송 버튼
        const sendBtn = document.getElementById('sendBtn');
        if (sendBtn) {
            sendBtn.addEventListener('click', () => {
                this.client.sendCommand();
            });
        }

        // 빠른 명령어 버튼들
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('cmd-btn') && e.target.hasAttribute('data-cmd')) {
                const command = e.target.getAttribute('data-cmd');
                this.client.sendCommand(command);
            }
        });

        // 로그아웃 버튼
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                this.client.logout();
            });
        }
    }

    addGameMessage(message, type = 'system') {
        const output = document.getElementById('gameOutput');
        if (!output) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `game-message ${type}`;

        // 타임스탬프 추가
        const timestamp = new Date().toLocaleTimeString();
        messageDiv.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${this.client.escapeHtml(message)}`;

        output.appendChild(messageDiv);
        output.scrollTop = output.scrollHeight;

        // 메시지 개수 제한 (성능 최적화)
        const messages = output.querySelectorAll('.game-message');
        if (messages.length > 1000) {
            messages[0].remove();
        }
    }

    updateDynamicButtons(data) {
        const container = document.getElementById('dynamicButtons');
        if (!container) return;

        // 기존 버튼들 제거
        container.innerHTML = '';

        if (!data.buttons || (!data.buttons.exits?.length && !data.buttons.objects?.length)) {
            container.style.display = 'none';
            return;
        }

        container.style.display = 'block';

        // 출구 버튼들 추가
        if (data.buttons.exits?.length) {
            const exitsGroup = document.createElement('div');
            exitsGroup.className = 'button-group';
            exitsGroup.innerHTML = '<span class="group-label">🚪 출구:</span>';

            data.buttons.exits.forEach(exit => {
                const btn = document.createElement('button');
                btn.className = 'dynamic-btn exit';
                btn.setAttribute('data-cmd', exit.command);
                btn.textContent = `${exit.icon} ${exit.text}`;
                btn.addEventListener('click', () => {
                    this.client.sendCommand(exit.command);
                });
                exitsGroup.appendChild(btn);
            });

            container.appendChild(exitsGroup);
        }

        // 객체 버튼들 추가
        if (data.buttons.objects?.length) {
            const objectsGroup = document.createElement('div');
            objectsGroup.className = 'button-group';
            objectsGroup.innerHTML = '<span class="group-label">📦 객체:</span>';

            data.buttons.objects.forEach(obj => {
                const btn = document.createElement('button');
                btn.className = 'dynamic-btn object';
                btn.setAttribute('data-cmd', obj.command);
                btn.textContent = `${obj.icon} ${obj.text}`;
                btn.addEventListener('click', () => {
                    this.client.sendCommand(obj.command);
                });
                objectsGroup.appendChild(btn);
            });

            container.appendChild(objectsGroup);
        }
    }

    // 플레이어 상호작용 메시지 핸들러들
    handlePlayerJoined(data) {
        this.addGameMessage(data.message, 'player-join');
    }

    handlePlayerLeft(data) {
        this.addGameMessage(data.message, 'player-leave');
    }

    handlePlayerMoved(data) {
        this.addGameMessage(data.message, 'player-move');
    }

    handleEmoteReceived(data) {
        this.addGameMessage(data.message, 'emote');
    }

    handleRoomPlayersUpdate(data) {
        console.log('방 플레이어 목록 업데이트:', data);
        // 필요시 UI 업데이트 로직 추가
    }

    handleWhisperReceived(data) {
        this.addGameMessage(data.message, 'whisper');
    }

    handleItemReceived(data) {
        this.addGameMessage(data.message, 'item');
    }

    handleBeingFollowed(data) {
        this.addGameMessage(data.message, 'follow');
    }

    handleFollowingMovement(data) {
        this.addGameMessage(data.message, 'follow');
    }

    handlePlayerStatusChange(data) {
        this.addGameMessage(data.message, 'status');
    }

    handleRoomMessage(data) {
        this.addGameMessage(data.message, 'info');
    }

    handleSystemMessage(data) {
        this.addGameMessage(data.message, 'system');
    }

    handleFollowStopped(data) {
        this.addGameMessage(data.message, 'warning');
    }
}

// 전역 변수로 export
window.GameModule = GameModule;