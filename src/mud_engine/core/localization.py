"""
다국어 지원 시스템
"""

import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class LocalizationManager:
    """다국어 메시지 관리자"""

    def __init__(self):
        """초기화"""
        self.messages: Dict[str, Dict[str, str]] = {}
        self.default_locale = "en"
        self.supported_locales = ["en", "ko"]
        self._load_default_messages()

    def _load_default_messages(self) -> None:
        """기본 메시지 로드"""
        # 기본 시스템 메시지들
        self.messages = {
            # 인증 관련
            "auth.login_success": {
                "en": "✅ Welcome, {username}!",
                "ko": "✅ '{username}'님, 환영합니다!"
            },
            "auth.login_failed": {
                "en": "❌ Invalid username or password.",
                "ko": "❌ 사용자명 또는 비밀번호가 올바르지 않습니다."
            },
            "auth.already_logged_in": {
                "en": "❌ User is already logged in.",
                "ko": "❌ 이미 로그인된 사용자입니다."
            },
            "auth.not_authenticated": {
                "en": "❌ You are not authenticated.",
                "ko": "❌ 인증되지 않은 사용자입니다."
            },
            "auth.language_preference": {
                "en": "🌐 Language preference: {language}",
                "ko": "🌐 언어 설정: {language}"
            },

            # 게임 입장
            "game.entered": {
                "en": "Game entered! Type 'help' for commands.",
                "ko": "게임에 입장했습니다! 'help' 명령어로 도움말을 확인하세요."
            },
            "game.player_joined": {
                "en": "🎮 {username} joined the game.",
                "ko": "🎮 {username}님이 게임에 참여했습니다."
            },
            "game.player_left": {
                "en": "👋 {username} left the game.",
                "ko": "👋 {username}님이 게임을 떠났습니다."
            },

            # 이동 관련
            "movement.no_exit": {
                "en": "❌ You cannot go {direction}.",
                "ko": "❌ {direction} 방향으로는 갈 수 없습니다."
            },
            "movement.room_not_found": {
                "en": "❌ Room not found.",
                "ko": "❌ 방을 찾을 수 없습니다."
            },
            "movement.moved": {
                "en": "{username} moved {direction}.",
                "ko": "{username}님이 {direction}(으)로 이동했습니다."
            },
            "movement.error": {
                "en": "❌ An error occurred during movement.",
                "ko": "❌ 이동 중 오류가 발생했습니다."
            },

            # 전투 관련
            "combat.start": {
                "en": "⚔️ Combat started with {monster}!",
                "ko": "⚔️ {monster}와(과) 전투를 시작합니다!"
            },
            "combat.victory": {
                "en": "🎉 Victory! You defeated {monster}!",
                "ko": "🎉 승리! {monster}을(를) 처치했습니다!"
            },
            "combat.defeat": {
                "en": "💀 You were defeated...",
                "ko": "💀 전투에서 패배했습니다..."
            },
            "combat.your_turn": {
                "en": "🎯 Your turn! Choose your action:",
                "ko": "🎯 당신의 턴입니다! 행동을 선택하세요:"
            },
            "combat.monster_turn": {
                "en": "⏳ {monster}'s turn...",
                "ko": "⏳ {monster}의 턴입니다..."
            },
            "combat.attack_hit": {
                "en": "✅ Hit! {damage} damage to {target}!",
                "ko": "✅ 명중! {target}에게 {damage} 데미지!"
            },
            "combat.attack_miss": {
                "en": "❌ Missed {target}!",
                "ko": "❌ {target}을(를) 빗나갔습니다!"
            },
            "combat.defend": {
                "en": "{actor} takes a defensive stance. (Next damage reduced by 50%)",
                "ko": "{actor}이(가) 방어 자세를 취했습니다. (다음 공격 데미지 50% 감소)"
            },
            "combat.flee_success": {
                "en": "💨 You fled from combat!",
                "ko": "💨 전투에서 도망쳤습니다!"
            },
            "combat.flee_failed": {
                "en": "❌ Failed to flee!",
                "ko": "❌ 도망치지 못했습니다!"
            },
            "combat.round": {
                "en": "⚔️ Combat Round {round}",
                "ko": "⚔️ 전투 라운드 {round}"
            },
            "combat.player_hp": {
                "en": "👤 {name}",
                "ko": "👤 {name}"
            },
            "combat.monsters": {
                "en": "👹 Monsters:",
                "ko": "👹 몬스터:"
            },
            "combat.monster_entry": {
                "en": "   • {name}",
                "ko": "   • {name}"
            },
            "combat.hp_display": {
                "en": "     HP: {hp_bar} {current}/{max}",
                "ko": "     HP: {hp_bar} {current}/{max}"
            },
            "combat.action_attack": {
                "en": "[1] attack  - Attack with weapon",
                "ko": "[1] attack  - 무기로 공격"
            },
            "combat.action_defend": {
                "en": "[2] defend  - Defensive stance (50% damage reduction next turn)",
                "ko": "[2] defend  - 방어 자세 (다음 데미지 50% 감소)"
            },
            "combat.action_flee": {
                "en": "[3] flee    - Flee from combat (50% chance)",
                "ko": "[3] flee    - 도망치기 (50% 확률)"
            },
            "combat.enter_command": {
                "en": "Enter command:",
                "ko": "명령어를 입력하세요:"
            },
            "combat.defend_stance": {
                "en": "{actor} takes a defensive stance. (Next damage reduced by 50%)",
                "ko": "{actor}이(가) 방어 자세를 취했습니다. (다음 공격 데미지 50% 감소)"
            },
            "combat.fled_from_combat": {
                "en": "{actor} fled from combat!",
                "ko": "{actor}이(가) 전투에서 도망쳤습니다!"
            },
            "combat.wait_action": {
                "en": "{actor} waits.",
                "ko": "{actor}이(가) 대기합니다."
            },
            "combat.help_title": {
                "en": "⚔️ Combat Commands Available:",
                "ko": "⚔️ 전투 중 사용 가능한 명령어:"
            },
            "combat.help_attack": {
                "en": "[1] attack (or number 1) - Attack with weapon",
                "ko": "[1] attack (또는 숫자 1) - 무기로 공격"
            },
            "combat.help_defend": {
                "en": "[2] defend (or number 2) - Defensive stance (50% damage reduction next turn)",
                "ko": "[2] defend (또는 숫자 2) - 방어 자세 (다음 데미지 50% 감소)"
            },
            "combat.help_flee": {
                "en": "[3] flee (or number 3) - Flee from combat (50% chance)",
                "ko": "[3] flee (또는 숫자 3) - 도망치기 (50% 확률)"
            },
            "combat.help_other": {
                "en": "📋 Other Commands:",
                "ko": "📋 기타 명령어:"
            },
            "combat.victory": {
                "en": "🎉 Victory in combat!",
                "ko": "🎉 전투에서 승리했습니다!"
            },
            "combat.defeat": {
                "en": "💀 Defeated in combat...",
                "ko": "💀 전투에서 패배했습니다..."
            },
            "combat.rewards": {
                "en": "💰 Rewards:",
                "ko": "💰 보상:"
            },
            "combat.exp_gained": {
                "en": "  - Experience: {exp}",
                "ko": "  - 경험치: {exp}"
            },
            "combat.gold_gained": {
                "en": "  - Gold: {gold}",
                "ko": "  - 골드: {gold}"
            },
            "combat.return_location": {
                "en": "Returning to original location...",
                "ko": "원래 위치로 돌아왔습니다."
            },
            "combat.victory_message": {
                "en": "🎉 Victory in combat!",
                "ko": "🎉 전투에서 승리했습니다!"
            },
            "combat.defeat_message": {
                "en": "💀 Defeated in combat...",
                "ko": "💀 전투에서 패배했습니다..."
            },
            "combat.rewards_header": {
                "en": "💰 Rewards:",
                "ko": "💰 보상:"
            },
            "combat.gold_reward": {
                "en": "  - Gold: {gold}",
                "ko": "  - 골드: {gold}"
            },
            "combat.items_obtained": {
                "en": "📦 Items obtained:",
                "ko": "📦 획득한 아이템:"
            },
            "combat.item_ground": {
                "en": "  - {name} x{quantity} (dropped on ground)",
                "ko": "  - {name} x{quantity} (땅에 떨어짐)"
            },
            "combat.item_inventory": {
                "en": "  - {name} x{quantity} (inventory)",
                "ko": "  - {name} x{quantity} (인벤토리)"
            },
            "combat.returning_location": {
                "en": "Returning to original location...",
                "ko": "원래 위치로 돌아갑니다..."
            },
            "help.look_combat": {
                "en": "Check combat status",
                "ko": "전투 상태 확인"
            },
            "help.status": {
                "en": "Check attributes",
                "ko": "능력치 확인"
            },
            "help.combat_detail": {
                "en": "Detailed combat information",
                "ko": "전투 상태 상세 정보"
            },
            "help.tip_numbers": {
                "en": "Tip: You can just enter numbers to select actions!",
                "ko": "팁: 숫자만 입력해도 행동을 선택할 수 있습니다!"
            },

            # 아이템 관련
            "item.not_found": {
                "en": "❌ Item '{item}' not found.",
                "ko": "❌ '{item}' 아이템을 찾을 수 없습니다."
            },
            "item.picked_up": {
                "en": "📦 You picked up {item}.",
                "ko": "📦 {item}을(를) 주웠습니다."
            },
            "item.dropped": {
                "en": "📦 You dropped {item}.",
                "ko": "📦 {item}을(를) 떨어뜨렸습니다."
            },
            "item.too_heavy": {
                "en": "❌ Too heavy to carry.",
                "ko": "❌ 너무 무거워서 들 수 없습니다."
            },
            "item.disappeared": {
                "en": "💨 {item} disappeared before your eyes.",
                "ko": "💨 {item}이(가) 눈앞에서 사라졌습니다."
            },

            # 명령어 관련
            "command.unknown": {
                "en": "❌ Unknown command: {command}",
                "ko": "❌ 알 수 없는 명령어: {command}"
            },
            "command.invalid_args": {
                "en": "❌ Invalid arguments. Usage: {usage}",
                "ko": "❌ 잘못된 인자입니다. 사용법: {usage}"
            },
            "command.admin_only": {
                "en": "❌ This command is for administrators only.",
                "ko": "❌ 이 명령어는 관리자만 사용할 수 있습니다."
            },

            # 시스템 메시지
            "system.server_shutdown": {
                "en": "🔧 Server is shutting down...",
                "ko": "🔧 서버가 종료됩니다..."
            },
            "system.maintenance": {
                "en": "🔧 Server maintenance in progress.",
                "ko": "🔧 서버 점검 중입니다."
            },
            "system.input_timeout": {
                "en": "❌ Input timeout exceeded.",
                "ko": "❌ 입력 시간이 초과되었습니다."
            },
            "system.connection_closed": {
                "en": "Connection closed",
                "ko": "연결 종료"
            },
            "system.max_attempts_exceeded": {
                "en": "❌ Maximum attempts exceeded.",
                "ko": "❌ 최대 시도 횟수를 초과했습니다."
            },
            "system.auth_error": {
                "en": "❌ An error occurred during authentication.",
                "ko": "❌ 인증 처리 중 오류가 발생했습니다."
            },

            # 에러 메시지
            "error.generic": {
                "en": "❌ An error occurred.",
                "ko": "❌ 오류가 발생했습니다."
            },
            "error.database": {
                "en": "❌ Database error occurred.",
                "ko": "❌ 데이터베이스 오류가 발생했습니다."
            },
            "error.network": {
                "en": "❌ Network error occurred.",
                "ko": "❌ 네트워크 오류가 발생했습니다."
            },

            # 언어 설정
            "language.changed": {
                "en": "✅ Language changed to English.",
                "ko": "✅ 언어가 한국어로 변경되었습니다."
            },
            "language.invalid": {
                "en": "❌ Invalid language. Supported: {languages}",
                "ko": "❌ 지원되지 않는 언어입니다. 지원 언어: {languages}"
            },

            # 도움말
            "help.header": {
                "en": "📖 Available Commands:",
                "ko": "📖 사용 가능한 명령어:"
            },
            "help.footer": {
                "en": "Type 'help <command>' for detailed information.",
                "ko": "'help <명령어>'로 자세한 정보를 확인하세요."
            },

            # 기본 명령어 메시지
            "look.refresh": {
                "en": "✅ You look around again.",
                "ko": "✅ 주변을 다시 둘러봅니다."
            },
            "look.error": {
                "en": "❌ Failed to look around.",
                "ko": "❌ 방 정보를 조회하는 중 오류가 발생했습니다."
            },
            "movement.success": {
                "en": "✅ 🚶 You moved {direction}.",
                "ko": "✅ 🚶 {direction} 방향으로 이동했습니다."
            },
            "movement.failed": {
                "en": "❌ Failed to move.",
                "ko": "❌ 이동에 실패했습니다."
            },
            "movement.player_left": {
                "en": "🚶 {username} left to the {direction}.",
                "ko": "🚶 {username}님이 {direction} 방향으로 떠났습니다."
            },
            "movement.player_arrived": {
                "en": "🚶 {username} arrived.",
                "ko": "🚶 {username}님이 도착했습니다."
            },

            # 채팅 메시지
            "say.success": {
                "en": "💬 You say: \"{message}\"",
                "ko": "💬 당신이 말했습니다: \"{message}\""
            },
            "say.broadcast": {
                "en": "💬 {username} says: \"{message}\"",
                "ko": "💬 {username}님이 말합니다: \"{message}\""
            },
            "say.usage_error": {
                "en": "Please enter a message to say.\nUsage: say <message>",
                "ko": "말할 내용을 입력해주세요.\n사용법: say <메시지>"
            },

            # 이동 관련 추가 메시지
            "movement.combat_blocked": {
                "en": "❌ You cannot move during combat. Flee or win the battle first.",
                "ko": "❌ 전투 중에는 이동할 수 없습니다. 먼저 전투에서 도망치거나 승리하세요."
            },
            "movement.no_location": {
                "en": "❌ Cannot determine current location.",
                "ko": "❌ 현재 위치를 확인할 수 없습니다."
            },

            # Go 명령어 메시지
            "go.usage_error": {
                "en": "Please specify a direction to move.\nUsage: go <direction>\nAvailable directions: north, south, east, west",
                "ko": "이동할 방향을 지정해주세요.\n사용법: go <방향>\n사용 가능한 방향: north, south, east, west"
            },
            "go.invalid_direction": {
                "en": "'{direction}' is not a valid direction.\nAvailable directions: north, south, east, west",
                "ko": "'{direction}'은(는) 올바른 방향이 아닙니다.\n사용 가능한 방향: north, south, east, west"
            },

            # 출구 관련 메시지
            "exits.no_exits": {
                "en": "🚪 There are no exits from this room.",
                "ko": "🚪 이 방에는 출구가 없습니다."
            },
            "exits.available": {
                "en": "🚪 Available exits: {exits}",
                "ko": "🚪 사용 가능한 출구: {exits}"
            },
            "exits.error": {
                "en": "❌ Failed to check exits.",
                "ko": "❌ 출구 정보를 확인하는 중 오류가 발생했습니다."
            },

            # 능력치 관련 메시지
            "stats.error": {
                "en": "❌ Failed to retrieve stats.",
                "ko": "❌ 능력치 정보를 확인하는 중 오류가 발생했습니다."
            },

            # 종료 메시지
            "quit.message": {
                "en": "Goodbye! Thanks for playing.",
                "ko": "안전하게 게임을 종료합니다. 안녕히 가세요!"
            },

            # 방 정보 표시 관련
            "room.time_day": {
                "en": "☀️  Day",
                "ko": "☀️  낮"
            },
            "room.time_night": {
                "en": "🌙 Night",
                "ko": "🌙 밤"
            },
            "room.exits": {
                "en": "🚪 Exits: {exits}",
                "ko": "🚪 출구: {exits}"
            },
            "room.players_here": {
                "en": "👥 Players here:",
                "ko": "👥 이곳에 있는 플레이어들:"
            },
            "room.objects_here": {
                "en": "📦 Objects here:",
                "ko": "📦 이곳에 있는 물건들:"
            },
            "room.npcs_here": {
                "en": "🧑‍💼 NPCs here:",
                "ko": "🧑‍💼 이곳에 있는 NPC들:"
            },
            "room.animals_here": {
                "en": "🐾 Animals here:",
                "ko": "🐾 이곳에 있는 동물들:"
            },
            "room.monsters_here": {
                "en": "👹 Monsters here:",
                "ko": "👹 이곳에 있는 몬스터들:"
            },
            "room.merchant_type": {
                "en": " (merchant)",
                "ko": " (상인)"
            },

            # 몬스터 이동 메시지
            "monster.appears": {
                "en": "🐾 {monster_name} appears.",
                "ko": "🐾 {monster_name}이(가) 나타났습니다."
            },
            "monster.leaves": {
                "en": "🐾 {monster_name} leaves.",
                "ko": "🐾 {monster_name}이(가) 떠났습니다."
            },

            # 시간 변화 알림
            "time.dawn": {
                "en": "🌅 The eastern sky brightens. Day has come.",
                "ko": "🌅 동쪽 하늘이 밝아옵니다. 낮이 되었습니다."
            },
            "time.dusk": {
                "en": "🌙 Darkness falls. Night has come.",
                "ko": "🌙 어둠이 내려앉습니다. 밤이 되었습니다."
            },

            # 도움말 명령어 관련
            "help.available_commands": {
                "en": "🎮 Available Commands:",
                "ko": "🎮 사용 가능한 명령어:"
            },
            "help.admin_commands": {
                "en": "🔧 Administrator Commands:",
                "ko": "🔧 관리자 명령어:"
            },
            "help.detailed_help": {
                "en": "Type 'help <command>' for detailed information about a specific command.",
                "ko": "특정 명령어의 자세한 도움말을 보려면 'help <명령어>'를 입력하세요."
            },

            # 명령어 설명들
            "cmd.attack.desc": {
                "en": "Attack a monster",
                "ko": "몬스터를 공격합니다"
            },
            "cmd.buy.desc": {
                "en": "Buy items from merchants",
                "ko": "상인에게서 아이템을 구매합니다"
            },
            "cmd.changename.desc": {
                "en": "Change your display name (once per day)",
                "ko": "게임 내 표시 이름을 변경합니다 (하루에 한 번만 가능)"
            },
            "cmd.combat.desc": {
                "en": "Check current combat status",
                "ko": "현재 전투 상태를 확인합니다"
            },
            "cmd.drop.desc": {
                "en": "Drop an item from inventory to current room",
                "ko": "인벤토리의 객체를 현재 방에 놓습니다"
            },
            "cmd.east.desc": {
                "en": "Move east",
                "ko": "east 방향으로 이동합니다"
            },
            "cmd.equip.desc": {
                "en": "Equip an item from inventory",
                "ko": "인벤토리의 장비를 착용합니다"
            },
            "cmd.exits.desc": {
                "en": "Check available exits from current room",
                "ko": "현재 방의 출구를 확인합니다"
            },
            "cmd.follow.desc": {
                "en": "Follow another player",
                "ko": "다른 플레이어를 따라갑니다"
            },
            "cmd.get.desc": {
                "en": "Pick up an object from the room",
                "ko": "방에 있는 객체를 인벤토리에 추가합니다"
            },
            "cmd.give.desc": {
                "en": "Give an item to another player",
                "ko": "다른 플레이어에게 아이템을 줍니다"
            },
            "cmd.go.desc": {
                "en": "Move in a specified direction",
                "ko": "지정한 방향으로 이동합니다"
            },
            "cmd.help.desc": {
                "en": "Show command help",
                "ko": "명령어 도움말을 표시합니다"
            },
            "cmd.inspect.desc": {
                "en": "Examine monsters or NPCs in detail",
                "ko": "몬스터나 NPC의 상세 정보를 확인합니다"
            },
            "cmd.inventory.desc": {
                "en": "Show your current inventory",
                "ko": "현재 소지하고 있는 객체들을 표시합니다"
            },
            "cmd.language.desc": {
                "en": "Change language settings",
                "ko": "언어 설정을 변경합니다"
            },
            "cmd.look.desc": {
                "en": "Look around or examine a specific target",
                "ko": "주변을 둘러보거나 특정 대상을 자세히 살펴봅니다"
            },
            "cmd.north.desc": {
                "en": "Move north",
                "ko": "north 방향으로 이동합니다"
            },
            "cmd.players.desc": {
                "en": "Show players in current room",
                "ko": "현재 방에 있는 플레이어들을 표시합니다"
            },
            "cmd.quit.desc": {
                "en": "Exit the game",
                "ko": "게임을 종료합니다"
            },
            "cmd.say.desc": {
                "en": "Send a message to all players in the same room",
                "ko": "같은 방에 있는 모든 플레이어에게 메시지를 전달합니다"
            },
            "cmd.sell.desc": {
                "en": "Sell items to merchants",
                "ko": "상인에게 아이템을 판매합니다"
            },
            "cmd.shop.desc": {
                "en": "View merchant's inventory",
                "ko": "상점의 상품 목록을 봅니다"
            },
            "cmd.south.desc": {
                "en": "Move south",
                "ko": "south 방향으로 이동합니다"
            },
            "cmd.stats.desc": {
                "en": "Check your character stats and status",
                "ko": "플레이어의 능력치와 상태를 확인합니다"
            },
            "cmd.talk.desc": {
                "en": "Talk to NPCs",
                "ko": "NPC와 대화합니다"
            },
            "cmd.tell.desc": {
                "en": "Send a private message to a specific player",
                "ko": "특정 플레이어에게 개인 메시지를 전달합니다"
            },
            "cmd.unequip.desc": {
                "en": "Unequip currently equipped items",
                "ko": "착용 중인 장비를 해제합니다"
            },
            "cmd.use.desc": {
                "en": "Use consumable items or activate objects",
                "ko": "소모품이나 사용 가능한 아이템을 사용합니다"
            },
            "cmd.west.desc": {
                "en": "Move west",
                "ko": "west 방향으로 이동합니다"
            },
            "cmd.whisper.desc": {
                "en": "Whisper to another player",
                "ko": "다른 플레이어에게 귓속말을 합니다"
            },
            "cmd.who.desc": {
                "en": "Show list of currently connected players",
                "ko": "현재 접속 중인 플레이어 목록을 표시합니다"
            },

            # 관리자 명령어 설명들
            "cmd.admin.desc": {
                "en": "Show administrator command list",
                "ko": "관리자 명령어 목록을 표시합니다"
            },
            "cmd.adminchangename.desc": {
                "en": "Change another player's name (admin only)",
                "ko": "다른 플레이어의 이름을 변경합니다 (관리자 전용)"
            },
            "cmd.createexit.desc": {
                "en": "Create exits between rooms",
                "ko": "방 사이에 출구를 생성합니다"
            },
            "cmd.createobject.desc": {
                "en": "Create new game objects",
                "ko": "새로운 게임 객체를 생성합니다"
            },
            "cmd.createroom.desc": {
                "en": "Create new rooms",
                "ko": "새로운 방을 생성합니다"
            },
            "cmd.editroom.desc": {
                "en": "Edit existing rooms",
                "ko": "기존 방을 편집합니다"
            },
            "cmd.goto.desc": {
                "en": "Teleport to specified coordinates",
                "ko": "지정한 좌표로 바로 이동합니다"
            },
            "cmd.info.desc": {
                "en": "Show detailed room information",
                "ko": "현재 방의 상세 정보를 표시합니다"
            },
            "cmd.scheduler.desc": {
                "en": "Manage global scheduler (list/info/enable/disable)",
                "ko": "글로벌 스케줄러 관리 (list/info/enable/disable)"
            },

            # 관리자 이름 변경 명령어
            "admin.changename.usage": {
                "en": "Usage: adminchangename <player_id> <new_name>",
                "ko": "사용법: adminchangename <플레이어아이디> <새이름>"
            },
            "admin.changename.insufficient_args": {
                "en": "❌ Insufficient arguments",
                "ko": "❌ 인자 부족"
            },
            "admin.changename.success": {
                "en": "✅ Successfully changed {old_name}'s name to '{new_name}'",
                "ko": "✅ {old_name}님의 이름을 '{new_name}'(으)로 변경했습니다"
            },
            "admin.changename.player_not_found": {
                "en": "❌ Player '{player_id}' not found",
                "ko": "❌ 플레이어 '{player_id}'을(를) 찾을 수 없습니다"
            },
            "admin.changename.error": {
                "en": "❌ An error occurred while changing the name.",
                "ko": "❌ 이름 변경 중 오류가 발생했습니다."
            },
            "admin.changename.failed": {
                "en": "❌ Name change failed: {error}",
                "ko": "❌ 이름 변경 실패: {error}"
            },

            # who 명령어 메시지
            "who.connected_players": {
                "en": "📋 Connected players ({count}):",
                "ko": "📋 접속 중인 플레이어 ({count}명):"
            },
            "who.no_players": {
                "en": "No players currently connected.",
                "ko": "현재 접속 중인 플레이어가 없습니다."
            },
            "who.player_entry": {
                "en": "• {username}{marker} (online: {time}s)",
                "ko": "• {username}{marker} (접속시간: {time}초)"
            },
            "who.you_marker": {
                "en": " (you)",
                "ko": " (당신)"
            },

            # players 명령어 메시지
            "players.in_room": {
                "en": "📍 Players in current room ({count}):",
                "ko": "📍 현재 방에 있는 플레이어들 ({count}명):"
            },
            "players.no_players_in_room": {
                "en": "No other players in this room.",
                "ko": "이 방에는 다른 플레이어가 없습니다."
            },
            "players.player_entry": {
                "en": "👤 {username}{marker}",
                "ko": "👤 {username}{marker}"
            },
            "players.me_marker": {
                "en": " (me)",
                "ko": " (나)"
            }
        }

        logger.info(f"기본 메시지 {len(self.messages)}개 로드 완료")

    def get_message(self, key: str, locale: str = None, **kwargs) -> str:
        """
        메시지 조회

        Args:
            key: 메시지 키 (예: "auth.login_success")
            locale: 언어 코드 (None이면 기본 언어)
            **kwargs: 메시지 포맷팅용 변수들

        Returns:
            str: 로케일에 맞는 메시지
        """
        if locale is None:
            locale = self.default_locale

        if locale not in self.supported_locales:
            locale = self.default_locale

        # 메시지 조회
        message_dict = self.messages.get(key)
        if not message_dict:
            logger.warning(f"메시지 키를 찾을 수 없음: {key}")
            return f"[Missing message: {key}]"

        # 로케일별 메시지 조회
        message = message_dict.get(locale)
        if not message:
            # 기본 언어로 폴백
            message = message_dict.get(self.default_locale)
            if not message:
                logger.warning(f"메시지를 찾을 수 없음: {key} (locale: {locale})")
                return f"[Missing message: {key}]"

        # 변수 치환
        try:
            return message.format(**kwargs)
        except KeyError as e:
            logger.warning(f"메시지 포맷팅 실패: {key}, 누락된 변수: {e}")
            return message
        except Exception as e:
            logger.error(f"메시지 포맷팅 오류: {key}, 오류: {e}")
            return message

    def add_message(self, key: str, messages: Dict[str, str]) -> None:
        """
        메시지 추가

        Args:
            key: 메시지 키
            messages: 언어별 메시지 딕셔너리 (예: {"en": "Hello", "ko": "안녕하세요"})
        """
        self.messages[key] = messages
        logger.debug(f"메시지 추가: {key}")

    def load_from_file(self, file_path: str) -> bool:
        """
        파일에서 메시지 로드

        Args:
            file_path: JSON 파일 경로

        Returns:
            bool: 성공 여부
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"메시지 파일이 존재하지 않음: {file_path}")
                return False

            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 기존 메시지에 추가
            for key, messages in data.items():
                if isinstance(messages, dict):
                    self.messages[key] = messages
                else:
                    logger.warning(f"잘못된 메시지 형식: {key}")

            logger.info(f"메시지 파일 로드 완료: {file_path}")
            return True

        except Exception as e:
            logger.error(f"메시지 파일 로드 실패: {file_path}, 오류: {e}")
            return False

    def save_to_file(self, file_path: str) -> bool:
        """
        메시지를 파일로 저장

        Args:
            file_path: JSON 파일 경로

        Returns:
            bool: 성공 여부
        """
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.messages, f, ensure_ascii=False, indent=2)

            logger.info(f"메시지 파일 저장 완료: {file_path}")
            return True

        except Exception as e:
            logger.error(f"메시지 파일 저장 실패: {file_path}, 오류: {e}")
            return False

    def get_supported_locales(self) -> list:
        """지원되는 언어 목록 반환"""
        return self.supported_locales.copy()

    def is_supported_locale(self, locale: str) -> bool:
        """지원되는 언어인지 확인"""
        return locale in self.supported_locales


# 전역 인스턴스
_localization_manager = None


def get_localization_manager() -> LocalizationManager:
    """전역 다국어 관리자 인스턴스 반환"""
    global _localization_manager
    if _localization_manager is None:
        _localization_manager = LocalizationManager()
    return _localization_manager


def get_message(key: str, locale: str = None, **kwargs) -> str:
    """
    편의 함수: 메시지 조회

    Args:
        key: 메시지 키
        locale: 언어 코드
        **kwargs: 포맷팅 변수들

    Returns:
        str: 로케일에 맞는 메시지
    """
    return get_localization_manager().get_message(key, locale, **kwargs)