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
            if (data.data && data.data.action === 'login_success') {
                this.client.authModule.handleLoginSuccess(data);
            } else if (data.data && data.data.action === 'register_success') {
                this.client.authModule.handleRegisterSuccess(data);
            } else {
                // 게임 명령어 성공 응답 처리 (look, move 등)
                if (data.message) {
                    this.client.gameModule.addGameMessage(data.message, 'success');
                }

                // 이동 명령어 후 자동 look 실행
                if (data.data && data.data.action === 'move') {
                    setTimeout(() => {
                        this.client.sendCommand('look');
                    }, 100);
                }

                // 능력치 명령어 응답 처리
                if (data.data && data.data.action === 'stats') {
                    this.client.statsModule.updateStatsPanel(data.data);
                }

                // look 명령어 응답 처리 - 동적 버튼 업데이트
                if (data.data && data.data.action === 'look') {
                    this.client.gameModule.updateDynamicButtons(data.data);
                }

                // 일반적인 동적 버튼 업데이트 (data에 exits나 objects가 있는 경우)
                if (data.data && (data.data.exits || data.data.objects)) {
                    this.client.gameModule.updateDynamicButtons(data.data);
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
            case 'room_info':
                this.client.gameModule.handleRoomInfo(data);
                break;
            case 'following_movement_complete':
                this.client.gameModule.handleFollowingMovementComplete(data);
                break;
            case 'npc_interaction':
                this.client.gameModule.handleNPCInteraction(data);
                break;
            case 'shop_list':
                this.client.gameModule.handleShopList(data);
                break;
            case 'transaction_result':
                this.client.gameModule.handleTransactionResult(data);
                break;
            case 'npc_dialogue':
                this.client.gameModule.handleNPCDialogue(data);
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