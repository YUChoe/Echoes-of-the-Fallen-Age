/**
 * 서버 메시지 처리 핸들러
 */

class MessageHandler {
    constructor(client) {
        this.client = client;
    }

    handleMessage(data) {
        // 디버깅을 위한 로깅
        console.log('서버 메시지 수신:', data);

        // 메시지 중복 표시 방지를 위한 플래그
        let messageDisplayed = false;

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
                    messageDisplayed = true;
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
                    // 방 컨텍스트 업데이트 (NPC 정보 포함)
                    this.client.updateRoomContext({
                        exits: data.data.exits ? data.data.exits.reduce((acc, exit) => {
                            acc[exit] = exit; // 간단한 매핑
                            return acc;
                        }, {}) : {},
                        objects: data.data.objects ? data.data.objects.map(obj => ({ name: obj })) : [],
                        players: data.data.players || [],
                        npcs: data.data.npcs || []
                    });
                }

                // look_refresh 명령어 응답 처리 - 기존 방 정보 다시 표시
                if (data.data && data.data.action === 'look_refresh') {
                    // 클라이언트에서 이미 가지고 있는 방 정보를 다시 표시하도록 요청
                    // 실제로는 아무것도 하지 않음 (중복 표시 방지)
                    console.log('방 정보 새로고침 요청 - 중복 표시 방지됨');
                }

                // inventory 명령어 응답 처리 - 인벤토리 컨텍스트 업데이트
                if (data.data && data.data.action === 'inventory') {
                    this.client.updateInventoryContext(data.data.items || []);
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
        } else if (data.response && !messageDisplayed) {
            // 이미 메시지가 표시되지 않은 경우에만 response 메시지 표시
            // 단, 명령어 확인 메시지는 표시하지 않음 (중복 방지)
            if (!data.response.includes('명령을 받았습니다')) {
                this.client.gameModule.addGameMessage(data.response, data.message_type || 'system');
            }
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