/**
 * 능력치 시스템 모듈
 */

class StatsModule {
    constructor(client) {
        this.client = client;
    }

    setupEventListeners() {
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
                    this.client.sendCommand(command);
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
        if (this.client.isAuthenticated) {
            this.client.sendMessage({
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

// 전역 변수로 export
window.StatsModule = StatsModule;