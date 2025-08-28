/**
 * 명령어 조합 모듈 - 동사-명사 조합 인터페이스
 */

class CommandBuilderModule {
    constructor(client) {
        this.client = client;
        this.selectedVerb = null;
        this.selectedNoun = null;
        this.availableVerbs = [];
        this.availableNouns = [];
        this.currentContext = null;

        this.setupEventListeners();
    }

    setupEventListeners() {
        // 명령어 조합 패널 이벤트 리스너 설정
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('verb-btn')) {
                this.selectVerb(e.target.getAttribute('data-verb'));
            } else if (e.target.classList.contains('noun-btn')) {
                this.selectNoun(e.target.getAttribute('data-noun'));
            } else if (e.target.id === 'executeCommand') {
                this.executeCommand();
            } else if (e.target.id === 'clearCommand') {
                this.clearSelection();
            }
        });
    }

    // 현재 상황에 맞는 명령어들을 업데이트
    updateAvailableCommands(context) {
        this.currentContext = context;
        this.updateVerbs(context);
        this.updateNouns(context);
        this.renderCommandBuilder();
    }

    // 사용 가능한 동사들 업데이트
    updateVerbs(context) {
        // 기본 명령어들은 상단 버튼으로 이미 제공되므로 동작선택에서 제외
        const baseVerbs = [
            { verb: 'examine', text: '자세히보기', icon: '🔍', description: '대상을 자세히 살펴봅니다' },
            { verb: 'say', text: '말하기', icon: '💬', description: '다른 플레이어들에게 말합니다' }
        ];

        // 상황별 추가 동사들
        const contextVerbs = [];

        // 인벤토리에 아이템이 있을 때
        if (context.hasInventoryItems) {
            contextVerbs.push(
                { verb: 'drop', text: '버리기', icon: '📤', description: '아이템을 버립니다' },
                { verb: 'use', text: '사용하기', icon: '⚡', description: '아이템을 사용합니다' },
                { verb: 'equip', text: '착용하기', icon: '🛡️', description: '장비를 착용합니다' },
                { verb: 'unequip', text: '해제하기', icon: '👕', description: '장비를 해제합니다' },
                { verb: 'give', text: '주기', icon: '🤝', description: '다른 플레이어에게 줍니다' }
            );
        }

        // 방에 객체가 있을 때
        if (context.hasRoomObjects) {
            contextVerbs.push(
                { verb: 'get', text: '가져가기', icon: '📥', description: '아이템을 가져갑니다' }
            );
        }

        // 방에 다른 플레이어가 있을 때
        if (context.hasOtherPlayers) {
            contextVerbs.push(
                { verb: 'tell', text: '귓속말', icon: '🗣️', description: '특정 플레이어에게 귓속말합니다' },
                { verb: 'emote', text: '감정표현', icon: '🎭', description: '감정을 표현합니다' },
                { verb: 'follow', text: '따라가기', icon: '👣', description: '플레이어를 따라갑니다' }
            );
        }

        // 방에 NPC가 있을 때
        if (context.hasNPCs) {
            contextVerbs.push(
                { verb: 'talk', text: '대화하기', icon: '💭', description: 'NPC와 대화합니다' },
                { verb: 'buy', text: '구매하기', icon: '💰', description: 'NPC에게서 구매합니다' },
                { verb: 'sell', text: '판매하기', icon: '💸', description: 'NPC에게 판매합니다' }
            );
        }

        // 출구가 있을 때
        if (context.hasExits) {
            contextVerbs.push(
                { verb: 'go', text: '이동하기', icon: '🚶', description: '다른 방으로 이동합니다' }
            );
        }

        this.availableVerbs = [...baseVerbs, ...contextVerbs];
    }

    // 사용 가능한 명사들 업데이트
    updateNouns(context) {
        this.availableNouns = [];

        // 방의 출구들
        if (context.exits && context.exits.length > 0) {
            context.exits.forEach(exit => {
                this.availableNouns.push({
                    noun: exit,
                    text: this.getDirectionText(exit),
                    icon: this.getDirectionIcon(exit),
                    category: 'exit',
                    description: `${this.getDirectionText(exit)}으로 이동`
                });
            });
        }

        // 방의 객체들
        if (context.objects && context.objects.length > 0) {
            context.objects.forEach(obj => {
                this.availableNouns.push({
                    noun: obj.name || obj,
                    text: obj.name || obj,
                    icon: this.getObjectIcon(obj.type || 'item'),
                    category: 'object',
                    description: `${obj.name || obj} - 방에 있는 물건`
                });
            });
        }

        // 인벤토리 아이템들
        if (context.inventory && context.inventory.length > 0) {
            context.inventory.forEach(item => {
                this.availableNouns.push({
                    noun: item.name || item,
                    text: item.name || item,
                    icon: this.getObjectIcon(item.type || 'item'),
                    category: 'inventory',
                    description: `${item.name || item} - 소지품`
                });
            });
        }

        // 방의 다른 플레이어들
        if (context.players && context.players.length > 0) {
            context.players.forEach(player => {
                this.availableNouns.push({
                    noun: player.name || player,
                    text: player.name || player,
                    icon: '👤',
                    category: 'player',
                    description: `${player.name || player} - 플레이어`
                });
            });
        }

        // 방의 NPC들
        if (context.npcs && context.npcs.length > 0) {
            context.npcs.forEach(npc => {
                this.availableNouns.push({
                    noun: npc.name || npc,
                    text: npc.name || npc,
                    icon: this.getNPCIcon(npc.npc_type || 'generic'),
                    category: 'npc',
                    description: `${npc.name || npc} - NPC`
                });
            });
        }
    }

    // 동사 선택
    selectVerb(verb) {
        this.selectedVerb = verb;
        this.updateVerbButtons();
        this.updateCommandPreview();
        this.filterNounsByVerb(verb);
    }

    // 명사 선택
    selectNoun(noun) {
        this.selectedNoun = noun;
        this.updateNounButtons();
        this.updateCommandPreview();
    }

    // 선택 초기화
    clearSelection() {
        this.selectedVerb = null;
        this.selectedNoun = null;
        this.updateVerbButtons();
        this.updateNounButtons();
        this.updateCommandPreview();
        this.showAllNouns();
    }

    // 동사에 따라 명사 필터링
    filterNounsByVerb(verb) {
        const verbNounMap = {
            'go': ['exit'],
            'get': ['object'],
            'drop': ['inventory'],
            'use': ['inventory'],
            'equip': ['inventory'],
            'unequip': ['inventory'],
            'examine': ['object', 'inventory', 'player', 'npc'],
            'give': ['inventory'],
            'tell': ['player'],
            'talk': ['npc'],
            'buy': ['npc'],
            'sell': ['npc'],
            'follow': ['player'],
            'emote': ['player']
        };

        const allowedCategories = verbNounMap[verb];
        if (allowedCategories) {
            this.showFilteredNouns(allowedCategories);
        } else {
            this.showAllNouns();
        }
    }

    // 필터링된 명사들만 표시
    showFilteredNouns(allowedCategories) {
        const nounButtons = document.querySelectorAll('.noun-btn');
        nounButtons.forEach(btn => {
            const category = btn.getAttribute('data-category');
            if (allowedCategories.includes(category)) {
                btn.style.display = 'inline-block';
                btn.classList.remove('disabled');
            } else {
                btn.style.display = 'none';
            }
        });
    }

    // 모든 명사 표시
    showAllNouns() {
        const nounButtons = document.querySelectorAll('.noun-btn');
        nounButtons.forEach(btn => {
            btn.style.display = 'inline-block';
            btn.classList.remove('disabled');
        });
    }

    // 명령어 실행
    executeCommand() {
        if (!this.selectedVerb) {
            this.client.uiModule.showNotification('먼저 동작을 선택해주세요.', 'warning');
            return;
        }

        let command = this.selectedVerb;

        // 명사가 필요한 동사인지 확인
        const verbsRequiringNoun = ['go', 'get', 'drop', 'use', 'equip', 'unequip', 'examine', 'give', 'tell', 'talk', 'buy', 'sell', 'follow'];

        if (verbsRequiringNoun.includes(this.selectedVerb) && !this.selectedNoun) {
            this.client.uiModule.showNotification('대상을 선택해주세요.', 'warning');
            return;
        }

        if (this.selectedNoun) {
            command += ` ${this.selectedNoun}`;
        }

        // 명령어 실행
        this.client.sendCommand(command);

        // 실행 후 자동 초기화
        setTimeout(() => {
            this.clearSelection();
        }, 100);
    }

    // 명령어 조합 UI 렌더링
    renderCommandBuilder() {
        const container = document.getElementById('commandBuilder');
        if (!container) return;

        container.innerHTML = `
            <div class="command-builder-panel">
                <div class="command-preview">
                    <div class="preview-label">명령어 미리보기:</div>
                    <div class="preview-command" id="commandPreview">명령어를 조합해보세요</div>
                </div>

                <div class="verb-section">
                    <div class="section-label">🎯 동작 선택:</div>
                    <div class="verb-buttons" id="verbButtons">
                        ${this.renderVerbButtons()}
                    </div>
                </div>

                <div class="noun-section">
                    <div class="section-label">📦 대상 선택:</div>
                    <div class="noun-buttons" id="nounButtons">
                        ${this.renderNounButtons()}
                    </div>
                </div>

                <div class="command-actions">
                    <button id="executeCommand" class="btn primary" disabled>
                        ⚡ 실행
                    </button>
                    <button id="clearCommand" class="btn secondary">
                        🔄 초기화
                    </button>
                </div>
            </div>
        `;

        this.updateCommandPreview();
    }

    // 동사 버튼들 렌더링
    renderVerbButtons() {
        return this.availableVerbs.map(verb => `
            <button class="verb-btn ${this.selectedVerb === verb.verb ? 'selected' : ''}"
                    data-verb="${verb.verb}"
                    title="${verb.description}">
                ${verb.icon} ${verb.text}
            </button>
        `).join('');
    }

    // 명사 버튼들 렌더링
    renderNounButtons() {
        if (this.availableNouns.length === 0) {
            return '<div class="no-nouns">선택할 수 있는 대상이 없습니다.</div>';
        }

        // 카테고리별로 그룹화
        const categories = {
            exit: { label: '🚪 출구', items: [] },
            object: { label: '📦 물건', items: [] },
            inventory: { label: '🎒 소지품', items: [] },
            player: { label: '👤 플레이어', items: [] },
            npc: { label: '🧙‍♂️ NPC', items: [] }
        };

        this.availableNouns.forEach(noun => {
            if (categories[noun.category]) {
                categories[noun.category].items.push(noun);
            }
        });

        let html = '';
        Object.entries(categories).forEach(([category, data]) => {
            if (data.items.length > 0) {
                html += `
                    <div class="noun-category">
                        <div class="category-label">${data.label}</div>
                        <div class="category-buttons">
                            ${data.items.map(noun => `
                                <button class="noun-btn ${this.selectedNoun === noun.noun ? 'selected' : ''}"
                                        data-noun="${noun.noun}"
                                        data-category="${noun.category}"
                                        title="${noun.description}">
                                    ${noun.icon} ${noun.text}
                                </button>
                            `).join('')}
                        </div>
                    </div>
                `;
            }
        });

        return html;
    }

    // 동사 버튼 상태 업데이트
    updateVerbButtons() {
        const verbButtons = document.querySelectorAll('.verb-btn');
        verbButtons.forEach(btn => {
            if (btn.getAttribute('data-verb') === this.selectedVerb) {
                btn.classList.add('selected');
            } else {
                btn.classList.remove('selected');
            }
        });
    }

    // 명사 버튼 상태 업데이트
    updateNounButtons() {
        const nounButtons = document.querySelectorAll('.noun-btn');
        nounButtons.forEach(btn => {
            if (btn.getAttribute('data-noun') === this.selectedNoun) {
                btn.classList.add('selected');
            } else {
                btn.classList.remove('selected');
            }
        });
    }

    // 명령어 미리보기 업데이트
    updateCommandPreview() {
        const previewElement = document.getElementById('commandPreview');
        const executeButton = document.getElementById('executeCommand');

        if (!previewElement || !executeButton) return;

        let command = '';
        let canExecute = false;

        if (this.selectedVerb) {
            command = this.selectedVerb;

            if (this.selectedNoun) {
                command += ` ${this.selectedNoun}`;
            }

            // 명사가 필요한 동사인지 확인
            const verbsRequiringNoun = ['go', 'get', 'drop', 'use', 'equip', 'unequip', 'examine', 'give', 'tell', 'talk', 'buy', 'sell', 'follow'];

            if (verbsRequiringNoun.includes(this.selectedVerb)) {
                canExecute = this.selectedNoun !== null;
            } else {
                canExecute = true;
            }
        }

        previewElement.textContent = command || '명령어를 조합해보세요';
        executeButton.disabled = !canExecute;

        if (canExecute) {
            executeButton.classList.remove('disabled');
        } else {
            executeButton.classList.add('disabled');
        }
    }

    // 유틸리티 메서드들
    getDirectionText(direction) {
        const directionMap = {
            'north': '북쪽', 'south': '남쪽', 'east': '동쪽', 'west': '서쪽',
            'up': '위쪽', 'down': '아래쪽', 'northeast': '북동쪽', 'northwest': '북서쪽',
            'southeast': '남동쪽', 'southwest': '남서쪽'
        };
        return directionMap[direction] || direction;
    }

    getDirectionIcon(direction) {
        const iconMap = {
            'north': '⬆️', 'south': '⬇️', 'east': '➡️', 'west': '⬅️',
            'up': '🔼', 'down': '🔽', 'northeast': '↗️', 'northwest': '↖️',
            'southeast': '↘️', 'southwest': '↙️'
        };
        return iconMap[direction] || '🚪';
    }

    getObjectIcon(type) {
        const iconMap = {
            'weapon': '⚔️', 'armor': '🛡️', 'food': '🍎', 'book': '📚',
            'key': '🗝️', 'treasure': '💎', 'furniture': '🪑', 'container': '📦',
            'item': '📦'
        };
        return iconMap[type] || '📦';
    }

    getNPCIcon(npcType) {
        const iconMap = {
            'merchant': '🧙‍♂️', 'guard': '🛡️', 'quest_giver': '📜', 'generic': '👤'
        };
        return iconMap[npcType] || '👤';
    }
}

// 전역 변수로 export
window.CommandBuilderModule = CommandBuilderModule;