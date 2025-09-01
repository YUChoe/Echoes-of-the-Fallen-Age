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

        // 줄바꿈 처리: \n을 <br>로 변환
        const escapedMessage = this.client.escapeHtml(message);
        const formattedMessage = escapedMessage.replace(/\n/g, '<br>');

        messageDiv.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${formattedMessage}`;

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

        // 출구, 객체, NPC 정보가 있는지 확인
        const hasExits = data.exits && data.exits.length > 0;
        const hasObjects = data.objects && data.objects.length > 0;
        const hasNPCs = data.npcs && data.npcs.length > 0;
        const hasButtons = data.buttons && (data.buttons.exits?.length || data.buttons.objects?.length || data.buttons.npcs?.length);

        if (!hasExits && !hasObjects && !hasNPCs && !hasButtons) {
            container.style.display = 'none';
            return;
        }

        container.style.display = 'block';

        // 출구 버튼들 추가 (data.exits 또는 data.buttons.exits에서)
        const exits = data.buttons?.exits || (data.exits ? data.exits.map(exit => ({
            command: exit,
            text: this.getDirectionText(exit),
            icon: this.getDirectionIcon(exit)
        })) : []);

        if (exits.length > 0) {
            const exitsGroup = document.createElement('div');
            exitsGroup.className = 'button-group exits';
            exitsGroup.innerHTML = '<span class="group-label">🚪 출구:</span>';

            exits.forEach(exit => {
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

        // 객체 버튼들 추가 (data.objects 또는 data.buttons.objects에서)
        const objects = data.buttons?.objects || (data.objects ? data.objects.map(obj => ({
            command: `examine ${obj}`,
            text: obj,
            icon: '📦'
        })) : []);

        if (objects.length > 0) {
            const objectsGroup = document.createElement('div');
            objectsGroup.className = 'button-group';
            objectsGroup.innerHTML = '<span class="group-label">📦 객체:</span>';

            objects.forEach(obj => {
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

        // NPC 버튼들 추가
        const npcs = data.buttons?.npcs || (data.npcs ? data.npcs.map(npc => ({
            command: `talk ${npc.name}`,
            text: npc.name,
            icon: this.getNPCIcon(npc.npc_type),
            npc_data: npc
        })) : []);

        if (npcs.length > 0) {
            const npcsGroup = document.createElement('div');
            npcsGroup.className = 'button-group';
            npcsGroup.innerHTML = '<span class="group-label">👤 NPC:</span>';

            npcs.forEach(npc => {
                const btn = document.createElement('button');
                btn.className = 'dynamic-btn npc';
                btn.setAttribute('data-cmd', npc.command);
                btn.textContent = `${npc.icon} ${npc.text}`;
                btn.addEventListener('click', () => {
                    // NPC 모달 열기
                    if (this.client.npcModule && npc.npc_data) {
                        this.client.npcModule.openNPCModal(npc.npc_data);
                    } else {
                        // 기본 대화 명령어 실행
                        this.client.sendCommand(npc.command);
                    }
                });
                npcsGroup.appendChild(btn);
            });

            container.appendChild(npcsGroup);
        }
    }

    getNPCIcon(npcType) {
        const iconMap = {
            'merchant': '🧙‍♂️',
            'guard': '🛡️',
            'quest_giver': '📜',
            'generic': '👤'
        };
        return iconMap[npcType] || '👤';
    }

    getDirectionText(direction) {
        const directionMap = {
            'north': '북쪽',
            'south': '남쪽',
            'east': '동쪽',
            'west': '서쪽',
            'up': '위쪽',
            'down': '아래쪽',
            'northeast': '북동쪽',
            'northwest': '북서쪽',
            'southeast': '남동쪽',
            'southwest': '남서쪽'
        };
        return directionMap[direction] || direction;
    }

    getDirectionIcon(direction) {
        const iconMap = {
            'north': '⬆️',
            'south': '⬇️',
            'east': '➡️',
            'west': '⬅️',
            'up': '🔼',
            'down': '🔽',
            'northeast': '↗️',
            'northwest': '↖️',
            'southeast': '↘️',
            'southwest': '↙️'
        };
        return iconMap[direction] || '🚪';
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
        // 로그인 관련 중복 메시지 필터링
        if (data.message && data.message.includes('게임에 참여했습니다')) {
            // 로그인 시 이미 환영 메시지가 표시되었으므로 참여 메시지는 표시하지 않음
            console.log('로그인 참여 메시지 중복 방지:', data.message);
            return;
        }

        this.addGameMessage(data.message, 'system');
    }

    handleFollowStopped(data) {
        this.addGameMessage(data.message, 'warning');
    }

    handleRoomInfo(data) {
        // 방 정보를 받았을 때 자동으로 look 명령어 결과처럼 처리
        console.log('=== GameModule.handleRoomInfo 호출됨 ===');
        console.log('데이터:', data);

        if (data.room) {
            const room = data.room;
            console.log('방 정보:', room);
            console.log('몬스터 데이터:', room.monsters);

            let message = `🏰 ${room.name}\n${room.description}\n`;

            // 몬스터 정보 추가
            if (room.monsters && room.monsters.length > 0) {
                console.log('몬스터 정보 추가 중:', room.monsters.length, '마리');
                message += "\n👹 이곳에 있는 몬스터들:\n";
                room.monsters.forEach(monster => {
                    const monsterLine = `• ${monster.name} (레벨 ${monster.level}, HP: ${monster.current_hp}/${monster.max_hp})\n`;
                    console.log('몬스터 라인 추가:', monsterLine);
                    message += monsterLine;
                });
            } else {
                console.log('몬스터 정보 없음 또는 빈 배열');
            }

            // 객체 정보 추가
            if (room.objects && room.objects.length > 0) {
                message += "\n📦 이곳에 있는 물건들:\n";
                room.objects.forEach(obj => {
                    message += `• ${obj.name}\n`;
                });
            }

            // 출구 정보 추가
            if (room.exits && Object.keys(room.exits).length > 0) {
                message += "\n🚪 출구:\n";
                Object.keys(room.exits).forEach(direction => {
                    message += `• ${this.getDirectionText(direction)}\n`;
                });
            }

            // 메시지 표시
            this.addGameMessage(message.trim(), 'info');

            // 동적 버튼 업데이트
            this.updateDynamicButtons({
                exits: Object.keys(room.exits || {}),
                objects: room.objects ? room.objects.map(obj => obj.name) : [],
                monsters: room.monsters ? room.monsters.map(monster => monster.name) : [],
                npcs: room.npcs || []
            });

            // 클라이언트의 방 컨텍스트 업데이트
            this.client.updateRoomContext(room);
        }
    }

    handleFollowingMovementComplete(data) {
        this.addGameMessage(data.message, 'follow');
    }

    // NPC 관련 메시지 처리
    handleNPCInteraction(data) {
        // NPC 상호작용 메시지 처리
        this.addGameMessage(data.message, 'npc');

        // NPC 모듈로 전달
        if (this.client.npcModule) {
            this.client.npcModule.handleNPCMessage(data);
        }
    }

    handleShopList(data) {
        // 상점 목록 메시지 처리
        if (data.message) {
            this.addGameMessage(data.message, 'shop');
        }

        // NPC 모듈로 전달
        if (this.client.npcModule) {
            this.client.npcModule.handleNPCMessage({
                type: 'shop_list',
                items: data.items,
                player_gold: data.player_gold
            });
        }
    }

    handleTransactionResult(data) {
        // 거래 결과 메시지 처리
        this.addGameMessage(data.message, data.success ? 'success' : 'error');

        // NPC 모듈로 전달
        if (this.client.npcModule) {
            this.client.npcModule.handleNPCMessage({
                type: 'transaction_result',
                success: data.success,
                message: data.message,
                player_gold: data.player_gold
            });
        }
    }

    handleNPCDialogue(data) {
        // NPC 대화 메시지 처리
        this.addGameMessage(data.message, 'npc');

        // NPC 모듈로 전달
        if (this.client.npcModule) {
            this.client.npcModule.handleNPCMessage({
                type: 'npc_dialogue',
                npc_name: data.npc_name,
                message: data.message
            });
        }
    }
}

// 전역 변수로 export
window.GameModule = GameModule;