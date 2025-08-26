/**
 * 서버 메시지 처리 핸들러
 */

class MessageHandler {
    constructor(client) {
        this.client = client;
    }

    handleMessage(data) {
        // 오류 메시지 처리
        if (data.error) {
            const screen = this.client.isAuthenticated ? 'game' : this.client.currentScreen;
            this.client.uiModule.showMessage(data.error, 'error', screen);
            return;
        }

        if (data.status === 'success') {
            if (data.action === 'login_success') {
                this.client.authModule.handleLoginSuccess(data);
            } else if (data.action === 'register_success') {
                this.client.authModule.handleRegisterSuccess(data);
            } else {
                // 게임 명령어 성공 응답 처리 (look, move 등)
                if (data.message) {
                    this.client.gameModule.addGameMessage(data.message, 'success');
                }

                // 능력치 명령어 응답 처리
                if (data.data && data.data.action === 'stats') {
                    this.client.statsModule.updateStatsPanel(data.data);
                }

                // UI 업데이트가 필요한 경우
                if (data.data && data.data.ui_update_needed) {
                    // UI 업데이트 로직
                }
            }
        } else if (data.response) {
            this.client.gameModule.addGameMessage(data.response, data.message_type || 'system');
        }

        // 동적 버튼 업데이트
        if (data.buttons) {
            this.client.gameModule.updateDynamicButtons(data);
        }

        // 특정 메시지 타입별 처리
        this.handleSpecificMessageTypes(data);
    }

    handleSpecificMessageTypes(data) {
        switch (data.type) {
            case 'player_joined':
                this.client.gameModule.handlePlayerJoined(data);
                break;
            case 'player_left':
                this.client.gameModule.handlePlayerLeft(data);
                break;
            case 'player_moved':
                this.client.gameModule.handlePlayerMoved(data);
                break;
            case 'emote_received':
                this.client.gameModule.handleEmoteReceived(data);
                break;
            case 'room_players_update':
                this.client.gameModule.handleRoomPlayersUpdate(data);
                break;
            case 'whisper_received':
                this.client.gameModule.handleWhisperReceived(data);
                break;
            case 'item_received':
                this.client.gameModule.handleItemReceived(data);
                break;
            case 'being_followed':
                this.client.gameModule.handleBeingFollowed(data);
                break;
            case 'following_movement':
                this.client.gameModule.handleFollowingMovement(data);
                break;
            case 'player_status_change':
                this.client.gameModule.handlePlayerStatusChange(data);
                break;
            case 'room_message':
                this.client.gameModule.handleRoomMessage(data);
                break;
            case 'system_message':
                this.client.gameModule.handleSystemMessage(data);
                break;
            case 'follow_stopped':
                this.client.gameModule.handleFollowStopped(data);
                break;
            default:
                // 알 수 없는 메시지 타입
                if (data.message) {
                    this.client.gameModule.addGameMessage(data.message, 'system');
                }
                break;
        }
    }
}

// 전역 변수로 export
window.MessageHandler = MessageHandler;