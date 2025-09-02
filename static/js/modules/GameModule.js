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
                    // 성향 정보 추가
                    let temperamentInfo = '';
                    if (monster.monster_type) {
                        const temperamentMap = {
                            'aggressive': '공격적',
                            'passive': '수동적',
                            'neutral': '중립적'
                        };
                        temperamentInfo = ` [${temperamentMap[monster.monster_type] || monster.monster_type}]`;
                    }

                    const monsterLine = `• ${monster.name} (레벨 ${monster.level}, HP: ${monster.current_hp}/${monster.max_hp})${temperamentInfo}\n`;
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

    // 전투 시작 처리
    handleCombatStart(data) {
        try {
            console.log('전투 시작 메시지 수신:', data);
            this.addGameMessage(data.message, 'combat-start');

            if (data.combat_status) {
                this.showCombatUI(data.combat_status);
            }
        } catch (error) {
            console.error('전투 시작 메시지 처리 오류:', error);
            this.addGameMessage('전투 시작 정보 표시 중 오류가 발생했습니다.', 'error');
        }
    }

    // 전투 메시지 처리
    handleCombatMessage(data) {
        try {
            console.log('전투 메시지 수신:', data);
            this.addGameMessage(data.message, 'combat');

            if (data.combat_status) {
                this.updateCombatStatus(data.combat_status);
            }
        } catch (error) {
            console.error('전투 메시지 처리 오류:', error);
            this.addGameMessage('전투 정보 표시 중 오류가 발생했습니다.', 'error');
        }
    }

    // 전투 상태 업데이트
    handleCombatStatus(data) {
        try {
            console.log('전투 상태 업데이트:', data);
            if (data.combat_status) {
                this.updateCombatStatus(data.combat_status);
            }
        } catch (error) {
            console.error('전투 상태 업데이트 오류:', error);
        }
    }

    // 전투 종료 처리
    handleCombatEnd(data) {
        try {
            console.log('전투 종료 메시지 수신:', data);
            this.addGameMessage(data.message, 'combat-end');
            this.hideCombatUI();
        } catch (error) {
            console.error('전투 종료 메시지 처리 오류:', error);
            this.addGameMessage('전투 종료 정보 표시 중 오류가 발생했습니다.', 'error');
        }
    }

    // 턴 시작 처리
    handleTurnStart(data) {
        try {
            console.log('턴 시작 메시지 수신:', data);
            this.addGameMessage(data.message, 'turn-start');

            if (data.combat_status) {
                this.updateCombatStatus(data.combat_status);
                this.highlightCurrentTurn(data.combat_status.current_turn);

                // 플레이어 턴인지 확인 (현재 턴이 플레이어 이름과 일치하는지)
                const isPlayerTurn = data.combat_status.current_turn === this.client.playerName;
                if (isPlayerTurn) {
                    this.showActionButtons();
                }
            }
        } catch (error) {
            console.error('턴 시작 메시지 처리 오류:', error);
        }
    }

    // 액션 결과 처리
    handleActionResult(data) {
        try {
            console.log('액션 결과 메시지 수신:', data);
            this.addGameMessage(data.message, 'action-result');

            if (data.combat_status) {
                this.updateCombatStatus(data.combat_status);
            }
        } catch (error) {
            console.error('액션 결과 메시지 처리 오류:', error);
        }
    }

    // 선공형 몬스터 공격 처리
    handleMonsterAggro(data) {
        try {
            console.log('선공형 몬스터 공격 메시지 수신:', data);

            // 공격 메시지 표시
            const message = data.message || `${data.monster_name || '몬스터'}가 당신을 공격합니다!`;
            this.addGameMessage(message, 'warning');

            // 전투 상태 연동 (필요시)
            if (data.combat_started && data.combat_info) {
                console.log('선공형 몬스터 공격으로 전투 시작:', data.combat_info);
                this.showCombatUI(data.combat_info);
            }

            // 디버깅 로깅
            console.log('선공형 몬스터 공격 처리 완료:', {
                monster_name: data.monster_name,
                message: message,
                combat_started: data.combat_started
            });

        } catch (error) {
            console.error('선공형 몬스터 공격 메시지 처리 오류:', error);
            // 최소한의 대체 알림
            this.addGameMessage('몬스터가 당신을 공격했습니다!', 'warning');
        }
    }

    // 전투 UI 표시
    showCombatUI(combatStatus) {
        console.log('전투 UI 표시:', combatStatus);
        // 전투 UI 패널이 없으면 생성
        let combatUI = document.getElementById('combatUI');
        if (!combatUI) {
            this.createCombatUI();
            combatUI = document.getElementById('combatUI');
        }

        if (combatUI) {
            combatUI.style.display = 'block';
            this.updateCombatStatus(combatStatus);
        }
    }

    // 전투 UI 숨김
    hideCombatUI() {
        console.log('전투 UI 숨김');
        const combatUI = document.getElementById('combatUI');
        if (combatUI) {
            combatUI.style.display = 'none';
        }

        // 액션 버튼도 숨김
        this.hideActionButtons();
    }

    // 전투 상태 업데이트 (다중 전투 지원)
    updateCombatStatus(combatStatus) {
        console.log('다중 전투 상태 업데이트:', combatStatus);

        // 플레이어 HP 업데이트
        this.updateHPBar('playerHP', combatStatus.player.hp, combatStatus.player.max_hp);

        // 몬스터들 HP 업데이트
        this.updateMonstersHP(combatStatus.monsters || [combatStatus.monster]);

        // 타겟 선택기 업데이트
        this.updateTargetSelector(combatStatus.monsters || [combatStatus.monster], combatStatus.current_target_index);

        // 턴 정보 업데이트
        const turnInfo = document.getElementById('turnInfo');
        if (turnInfo) {
            turnInfo.textContent = `턴 ${combatStatus.turn_number}: ${combatStatus.current_turn}`;
        }

        // 전투 상태 업데이트
        const combatState = document.getElementById('combatState');
        if (combatState) {
            combatState.textContent = `상태: ${combatStatus.state}`;
        }
    }

    // 다중 몬스터 HP 업데이트
    updateMonstersHP(monsters) {
        const monstersContainer = document.getElementById('monstersContainer');
        if (!monstersContainer) return;

        // 기존 몬스터 UI 제거
        monstersContainer.innerHTML = '';

        // 각 몬스터에 대해 HP 바 생성
        monsters.forEach((monster, index) => {
            if (!monster) return;

            const monsterDiv = document.createElement('div');
            monsterDiv.className = `participant monster ${monster.is_alive === false ? 'dead' : ''}`;
            monsterDiv.innerHTML = `
                <div class="participant-name">👹 ${monster.name}</div>
                <div id="monsterHP_${index}" class="hp-container">
                    <div class="hp-bar">
                        <div class="hp-fill"></div>
                    </div>
                    <div class="hp-text">${monster.hp}/${monster.max_hp}</div>
                </div>
            `;
            monstersContainer.appendChild(monsterDiv);

            // HP 바 업데이트
            this.updateHPBar(`monsterHP_${index}`, monster.hp, monster.max_hp);
        });
    }

    // 타겟 선택기 업데이트
    updateTargetSelector(monsters, currentTargetIndex) {
        const targetSelector = document.getElementById('targetSelector');
        const targetSelect = document.getElementById('targetSelect');

        if (!targetSelector || !targetSelect) return;

        // 살아있는 몬스터가 2마리 이상일 때만 타겟 선택기 표시
        const aliveMonsters = monsters.filter(monster => monster && monster.is_alive !== false);

        if (aliveMonsters.length > 1) {
            targetSelector.style.display = 'block';

            // 옵션 초기화
            targetSelect.innerHTML = '';

            // 살아있는 몬스터들을 옵션으로 추가
            aliveMonsters.forEach((monster, index) => {
                const option = document.createElement('option');
                option.value = monster.name;
                option.textContent = `${monster.name} (HP: ${monster.hp}/${monster.max_hp})`;
                if (index === (currentTargetIndex || 0)) {
                    option.selected = true;
                }
                targetSelect.appendChild(option);
            });
        } else {
            targetSelector.style.display = 'none';
        }
    }

    // HP 바 업데이트
    updateHPBar(elementId, currentHP, maxHP) {
        const hpBar = document.querySelector(`#${elementId} .hp-fill`);
        const hpText = document.querySelector(`#${elementId} .hp-text`);

        if (hpBar && hpText) {
            const percentage = (currentHP / maxHP) * 100;
            hpBar.style.width = `${percentage}%`;
            hpText.textContent = `${currentHP}/${maxHP}`;

            // HP에 따른 색상 변경
            if (percentage < 30) {
                hpBar.style.background = 'linear-gradient(90deg, #ff4757, #ff3742)';
            } else if (percentage < 60) {
                hpBar.style.background = 'linear-gradient(90deg, #ffa502, #ff6348)';
            } else {
                hpBar.style.background = 'linear-gradient(90deg, #2ed573, #7bed9f)';
            }
        }
    }

    // 현재 턴 강조
    highlightCurrentTurn(currentPlayer) {
        console.log('현재 턴 강조:', currentPlayer);
        const turnIndicator = document.getElementById('turnIndicator');
        if (turnIndicator) {
            turnIndicator.textContent = `${currentPlayer}의 턴`;
            turnIndicator.className = 'turn-indicator active';
        }
    }

    // 액션 버튼 표시
    showActionButtons() {
        console.log('액션 버튼 표시');
        const actionButtons = document.getElementById('combatActions');
        if (actionButtons) {
            actionButtons.style.display = 'block';
        }
    }

    // 액션 버튼 숨김
    hideActionButtons() {
        console.log('액션 버튼 숨김');
        const actionButtons = document.getElementById('combatActions');
        if (actionButtons) {
            actionButtons.style.display = 'none';
        }
    }

    // 전투 UI 생성 (다중 전투 지원)
    createCombatUI() {
        console.log('다중 전투 UI 생성');

        // 기존 UI가 있으면 제거
        const existingUI = document.getElementById('combatUI');
        if (existingUI) {
            existingUI.remove();
        }

        // 전투 UI HTML 생성
        const combatUIHTML = `
            <div id="combatUI" class="combat-ui" style="display: none;">
                <div class="combat-header">
                    <h3>⚔️ 전투 중</h3>
                    <div id="turnInfo" class="turn-info">턴 정보</div>
                    <div id="combatState" class="combat-state">상태 정보</div>
                </div>

                <div class="combat-participants">
                    <div class="participant player">
                        <div class="participant-name">👤 플레이어</div>
                        <div id="playerHP" class="hp-container">
                            <div class="hp-bar">
                                <div class="hp-fill"></div>
                            </div>
                            <div class="hp-text">100/100</div>
                        </div>
                    </div>

                    <div id="monstersContainer" class="monsters-container">
                        <!-- 몬스터들이 동적으로 추가됨 -->
                    </div>
                </div>

                <div id="targetSelector" class="target-selector" style="display: none;">
                    <label>공격 대상 선택:</label>
                    <select id="targetSelect">
                        <!-- 타겟 옵션들이 동적으로 추가됨 -->
                    </select>
                </div>

                <div id="turnIndicator" class="turn-indicator">대기 중...</div>

                <div id="combatActions" class="combat-actions" style="display: none;">
                    <button class="combat-btn attack" data-cmd="attack">⚔️ 공격</button>
                    <button class="combat-btn defend" data-cmd="defend">🛡️ 방어</button>
                    <button class="combat-btn flee" data-cmd="flee">💨 도망</button>
                </div>
            </div>
        `;

        // body에 추가
        document.body.insertAdjacentHTML('beforeend', combatUIHTML);

        // 액션 버튼 이벤트 리스너 추가
        const actionButtons = document.querySelectorAll('.combat-btn');
        actionButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const command = btn.getAttribute('data-cmd');

                // 공격 명령어인 경우 타겟 선택 확인
                if (command === 'attack') {
                    const targetSelect = document.getElementById('targetSelect');
                    if (targetSelect && targetSelect.options.length > 1) {
                        const selectedTarget = targetSelect.value;
                        this.client.sendCommand(`${command} ${selectedTarget}`);
                    } else {
                        this.client.sendCommand(command);
                    }
                } else {
                    this.client.sendCommand(command);
                }

                // 버튼 일시적으로 비활성화
                btn.disabled = true;
                setTimeout(() => {
                    btn.disabled = false;
                }, 1000);
            });
        });
    }
}

// 전역 변수로 export
window.GameModule = GameModule;