/**
 * UI 관련 유틸리티 모듈
 */

class UIModule {
    constructor(client) {
        this.client = client;
    }

    updateConnectionStatus(status, isConnected) {
        const statusElement = document.getElementById('connectionStatus');
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = `status ${isConnected ? 'connected' : 'disconnected'}`;
        }
    }

    updatePlayerInfo(username) {
        const playerInfoElement = document.getElementById('playerInfo');
        if (playerInfoElement) {
            playerInfoElement.textContent = `플레이어: ${username}`;
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

    showLoadingMessage(container) {
        container.innerHTML = '<div class="loading-message">로딩 중...</div>';
    }

    showEmptyMessage(container, message) {
        container.innerHTML = `<div class="empty-message">${this.client.escapeHtml(message)}</div>`;
    }

    showErrorMessage(container, message) {
        container.innerHTML = `<div class="error-message">${this.client.escapeHtml(message)}</div>`;
    }

    formatDate(dateString) {
        if (!dateString) return '알 수 없음';

        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('ko-KR', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (error) {
            return '알 수 없음';
        }
    }

    // 모달 관련 유틸리티
    showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'block';
            modal.classList.add('active');
        }
    }

    hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
            modal.classList.remove('active');
        }
    }

    // 폼 관련 유틸리티
    resetForm(formId) {
        const form = document.getElementById(formId);
        if (form) {
            form.reset();
        }
    }

    getFormData(formId) {
        const form = document.getElementById(formId);
        if (!form) return {};

        const formData = new FormData(form);
        const data = {};

        for (let [key, value] of formData.entries()) {
            data[key] = value.trim();
        }

        return data;
    }

    // 알림 관련 유틸리티
    showNotification(message, type = 'info', duration = 3000) {
        // 알림 컨테이너가 없으면 생성
        let container = document.getElementById('notification-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notification-container';
            container.className = 'notification-container';
            document.body.appendChild(container);
        }

        // 알림 요소 생성
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;

        // 컨테이너에 추가
        container.appendChild(notification);

        // 애니메이션 효과
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);

        // 자동 제거
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, duration);
    }

    // 로딩 스피너 관련
    showLoadingSpinner(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const spinner = document.createElement('div');
        spinner.className = 'loading-spinner';
        spinner.innerHTML = `
            <div class="spinner"></div>
            <div class="loading-text">로딩 중...</div>
        `;

        container.appendChild(spinner);
    }

    hideLoadingSpinner(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const spinner = container.querySelector('.loading-spinner');
        if (spinner) {
            spinner.remove();
        }
    }

    // 확인 대화상자
    showConfirmDialog(message, onConfirm, onCancel) {
        const dialog = document.createElement('div');
        dialog.className = 'confirm-dialog-overlay';
        dialog.innerHTML = `
            <div class="confirm-dialog">
                <div class="confirm-message">${this.client.escapeHtml(message)}</div>
                <div class="confirm-buttons">
                    <button class="btn secondary cancel-btn">취소</button>
                    <button class="btn primary confirm-btn">확인</button>
                </div>
            </div>
        `;

        document.body.appendChild(dialog);

        // 이벤트 리스너
        const confirmBtn = dialog.querySelector('.confirm-btn');
        const cancelBtn = dialog.querySelector('.cancel-btn');

        const cleanup = () => {
            document.body.removeChild(dialog);
        };

        confirmBtn.addEventListener('click', () => {
            cleanup();
            if (onConfirm) onConfirm();
        });

        cancelBtn.addEventListener('click', () => {
            cleanup();
            if (onCancel) onCancel();
        });

        // 외부 클릭 시 취소
        dialog.addEventListener('click', (e) => {
            if (e.target === dialog) {
                cleanup();
                if (onCancel) onCancel();
            }
        });
    }
}

// 전역 변수로 export
window.UIModule = UIModule;