/**
 * NPC 상호작용 모듈
 */
class NPCModule {
    constructor(client) {
        this.client = client;
        this.currentNPC = null;
        this.shopItems = [];
        this.playerGold = 100;

        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // NPC 모달 닫기
        const closeBtn = document.getElementById('closeNpcModal');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeNPCModal());
        }

        // 모달 외부 클릭으로 닫기
        const modal = document.getElementById('npcModal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeNPCModal();
                }
            });
        }

        // 탭 전환
        const tabBtns = document.querySelectorAll('#npcModal .tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tabName = e.target.dataset.tab;
                this.switchTab(tabName);
            });
        });

        // ESC 키로 모달 닫기
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isNPCModalOpen()) {
                this.closeNPCModal();
            }
        });
    }

    /**
     * NPC 모달 열기
     */
    openNPCModal(npcData) {
        this.currentNPC = npcData;

        // NPC 정보 업데이트
        this.updateNPCInfo(npcData);

        // 모달 표시
        const modal = document.getElementById('npcModal');
        if (modal) {
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }

        // 상인인 경우 상점 탭 표시
        if (npcData.npc_type === 'merchant') {
            this.showShopTab();
            this.loadShopItems();
        } else {
            this.hideShopTab();
        }

        // 대화 탭을 기본으로 선택
        this.switchTab('talk');
    }

    /**
     * NPC 모달 닫기
     */
    closeNPCModal() {
        const modal = document.getElementById('npcModal');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }

        this.currentNPC = null;
        this.shopItems = [];
    }

    /**
     * NPC 모달이 열려있는지 확인
     */
    isNPCModalOpen() {
        const modal = document.getElementById('npcModal');
        return modal && modal.style.display === 'flex';
    }

    /**
     * NPC 정보 업데이트
     */
    updateNPCInfo(npcData) {
        // NPC 이름
        const nameEl = document.getElementById('npcName');
        if (nameEl) {
            nameEl.textContent = npcData.name || 'Unknown NPC';
        }

        // NPC 설명
        const descEl = document.getElementById('npcDescription');
        if (descEl) {
            descEl.textContent = npcData.description || 'No description available.';
        }

        // NPC 아바타 (타입에 따라)
        const avatarEl = document.getElementById('npcAvatar');
        if (avatarEl) {
            const avatars = {
                'merchant': '🧙‍♂️',
                'guard': '🛡️',
                'quest_giver': '📜',
                'generic': '👤'
            };
            avatarEl.textContent = avatars[npcData.npc_type] || '👤';
        }

        // 모달 제목
        const titleEl = document.getElementById('npcModalTitle');
        if (titleEl) {
            const typeNames = {
                'merchant': '상인',
                'guard': '경비병',
                'quest_giver': '퀘스트 제공자',
                'generic': 'NPC'
            };
            const typeName = typeNames[npcData.npc_type] || 'NPC';
            titleEl.textContent = `${avatars[npcData.npc_type] || '👤'} ${typeName} - ${npcData.name}`;
        }
    }

    /**
     * 상점 탭 표시
     */
    showShopTab() {
        const shopTab = document.getElementById('shopTab');
        if (shopTab) {
            shopTab.style.display = 'block';
        }
    }

    /**
     * 상점 탭 숨기기
     */
    hideShopTab() {
        const shopTab = document.getElementById('shopTab');
        if (shopTab) {
            shopTab.style.display = 'none';
        }
    }

    /**
     * 탭 전환
     */
    switchTab(tabName) {
        // 모든 탭 버튼 비활성화
        const tabBtns = document.querySelectorAll('#npcModal .tab-btn');
        tabBtns.forEach(btn => btn.classList.remove('active'));

        // 모든 탭 콘텐츠 숨기기
        const tabContents = document.querySelectorAll('#npcModal .tab-content');
        tabContents.forEach(content => content.classList.remove('active'));

        // 선택된 탭 활성화
        const selectedBtn = document.querySelector(`#npcModal .tab-btn[data-tab="${tabName}"]`);
        if (selectedBtn) {
            selectedBtn.classList.add('active');
        }

        const selectedContent = document.getElementById(tabName === 'talk' ? 'talkTab' : 'shopTabContent');
        if (selectedContent) {
            selectedContent.classList.add('active');
        }
    }

    /**
     * 상점 아이템 로드
     */
    async loadShopItems() {
        if (!this.currentNPC || this.currentNPC.npc_type !== 'merchant') {
            return;
        }

        // 상점 명령어 전송
        this.client.sendCommand('shop');
    }

    /**
     * 상점 아이템 표시
     */
    displayShopItems(items) {
        const container = document.getElementById('shopItems');
        if (!container) return;

        if (!items || items.length === 0) {
            container.innerHTML = '<div class="no-items">판매할 상품이 없습니다.</div>';
            return;
        }

        let html = '';
        items.forEach((item, index) => {
            html += `
                <div class="shop-item" data-item-id="${item.id}">
                    <div class="item-info">
                        <div class="item-icon">${this.getItemIcon(item.category)}</div>
                        <div class="item-details">
                            <h5 class="item-name">${item.name}</h5>
                            <p class="item-description">${item.description}</p>
                            <div class="item-meta">
                                <span class="item-category">${this.getCategoryName(item.category)}</span>
                                <span class="item-weight">${item.weight}kg</span>
                            </div>
                        </div>
                    </div>
                    <div class="item-actions">
                        <div class="item-price">${item.price} gold</div>
                        <button class="btn primary small" onclick="buyItem('${item.name}')">구매</button>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    /**
     * 아이템 아이콘 가져오기
     */
    getItemIcon(category) {
        const icons = {
            'weapon': '⚔️',
            'armor': '🛡️',
            'consumable': '🧪',
            'misc': '📦'
        };
        return icons[category] || '📦';
    }

    /**
     * 카테고리 이름 가져오기
     */
    getCategoryName(category) {
        const names = {
            'weapon': '무기',
            'armor': '방어구',
            'consumable': '소모품',
            'misc': '기타'
        };
        return names[category] || '기타';
    }

    /**
     * 플레이어 골드 업데이트
     */
    updatePlayerGold(gold) {
        this.playerGold = gold;
        const goldEl = document.getElementById('playerGold');
        if (goldEl) {
            goldEl.textContent = gold;
        }
    }

    /**
     * 대화 메시지 추가
     */
    addDialogueMessage(speaker, message, isNPC = false) {
        const historyEl = document.getElementById('dialogueHistory');
        if (!historyEl) return;

        const messageEl = document.createElement('div');
        messageEl.className = `dialogue-message ${isNPC ? 'npc' : 'player'}`;
        messageEl.innerHTML = `<strong>${speaker}:</strong> ${message}`;

        historyEl.appendChild(messageEl);
        historyEl.scrollTop = historyEl.scrollHeight;
    }

    /**
     * 상점 목록 새로고침
     */
    refreshShop() {
        if (this.currentNPC && this.currentNPC.npc_type === 'merchant') {
            this.loadShopItems();
        }
    }

    /**
     * NPC 관련 메시지 처리
     */
    handleNPCMessage(data) {
        // 상점 목록 응답 처리
        if (data.type === 'shop_list') {
            this.displayShopItems(data.items);
            if (data.player_gold !== undefined) {
                this.updatePlayerGold(data.player_gold);
            }
        }

        // 대화 응답 처리
        else if (data.type === 'npc_dialogue') {
            this.addDialogueMessage(data.npc_name, data.message, true);
        }

        // 구매/판매 결과 처리
        else if (data.type === 'transaction_result') {
            if (data.success) {
                this.addDialogueMessage('시스템', data.message, false);
                if (data.player_gold !== undefined) {
                    this.updatePlayerGold(data.player_gold);
                }
                // 상점 목록 새로고침
                if (this.currentNPC && this.currentNPC.npc_type === 'merchant') {
                    setTimeout(() => this.loadShopItems(), 500);
                }
            } else {
                this.addDialogueMessage('시스템', data.message || '거래에 실패했습니다.', false);
            }
        }
    }
}

/**
 * 전역 함수들 (HTML에서 호출)
 */
function sendNpcCommand(command) {
    if (window.mudClient && window.mudClient.npcModule.currentNPC) {
        const npcName = window.mudClient.npcModule.currentNPC.name;
        let fullCommand = command;

        if (command === 'talk') {
            fullCommand = `talk ${npcName}`;
        } else if (command === 'examine') {
            fullCommand = `examine ${npcName}`;
        } else if (command === 'shop') {
            fullCommand = `shop ${npcName}`;
        }

        window.mudClient.sendCommand(fullCommand);
    }
}

function buyItem(itemName) {
    if (window.mudClient && window.mudClient.npcModule.currentNPC) {
        const npcName = window.mudClient.npcModule.currentNPC.name;
        window.mudClient.sendCommand(`buy ${itemName} ${npcName}`);
    }
}

function sellItem(itemName) {
    if (window.mudClient && window.mudClient.npcModule.currentNPC) {
        const npcName = window.mudClient.npcModule.currentNPC.name;
        window.mudClient.sendCommand(`sell ${itemName} ${npcName}`);
    }
}

function refreshShop() {
    if (window.mudClient && window.mudClient.npcModule) {
        window.mudClient.npcModule.refreshShop();
    }
}