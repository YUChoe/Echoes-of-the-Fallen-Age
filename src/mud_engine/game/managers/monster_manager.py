# -*- coding: utf-8 -*-
"""몬스터 관리자 모듈"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import uuid4

from ..repositories import MonsterRepository
from ..monster import Monster, MonsterType, MonsterBehavior, MonsterStats

logger = logging.getLogger(__name__)


class MonsterManager:
    """몬스터 및 스폰 시스템 관리 전담 클래스"""

    def __init__(self, monster_repo: MonsterRepository) -> None:
        """MonsterManager를 초기화합니다."""
        self._monster_repo: MonsterRepository = monster_repo
        self._spawn_scheduler_task: Optional[asyncio.Task] = None
        self._spawn_points: Dict[str, List[Dict[str, Any]]] = {}
        self._global_spawn_limits: Dict[str, int] = {}
        self._game_engine: Optional[Any] = None  # GameEngine 참조 (순환 참조 방지를 위해 Optional)
        self._room_manager: Optional[Any] = None  # RoomManager 참조
        logger.info("MonsterManager 초기화 완료")
    
    def set_game_engine(self, game_engine: Any) -> None:
        """GameEngine 참조를 설정합니다 (순환 참조 방지를 위해 초기화 후 설정)"""
        self._game_engine = game_engine
        logger.debug("MonsterManager에 GameEngine 참조 설정됨")
    
    def set_room_manager(self, room_manager: Any) -> None:
        """RoomManager 참조를 설정합니다"""
        self._room_manager = room_manager
        logger.debug("MonsterManager에 RoomManager 참조 설정됨")

    # === 스폰 스케줄러 ===

    async def start_spawn_scheduler(self) -> None:
        """몬스터 스폰 스케줄러를 시작합니다."""
        if self._spawn_scheduler_task and not self._spawn_scheduler_task.done():
            logger.warning("스폰 스케줄러가 이미 실행 중입니다")
            return
        logger.info("몬스터 스폰 스케줄러 시작")
        self._spawn_scheduler_task = asyncio.create_task(self._spawn_scheduler_loop())

    async def stop_spawn_scheduler(self) -> None:
        """몬스터 스폰 스케줄러를 중지합니다."""
        if self._spawn_scheduler_task:
            self._spawn_scheduler_task.cancel()
            try:
                await self._spawn_scheduler_task
            except asyncio.CancelledError:
                pass
            logger.info("몬스터 스폰 스케줄러 중지")

    async def _spawn_scheduler_loop(self) -> None:
        """스폰 스케줄러 메인 루프"""
        try:
            while True:
                await self._process_respawns()
                await self._process_initial_spawns()
                await self._process_monster_roaming()
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            logger.info("스폰 스케줄러 루프 종료")
            raise
        except Exception as e:
            logger.error(f"스폰 스케줄러 오류: {e}")
            await asyncio.sleep(5)

    async def _process_respawns(self) -> None:
        """리스폰 대기 중인 몬스터들을 처리합니다."""
        try:
            dead_monsters = await self._monster_repo.find_by(is_alive=False)
            for monster in dead_monsters:
                if monster.is_ready_to_respawn():
                    await self._respawn_monster(monster)
        except Exception as e:
            logger.error(f"리스폰 처리 실패: {e}")

    async def _process_initial_spawns(self) -> None:
        """초기 스폰이 필요한 방들을 처리합니다."""
        try:
            for room_id, spawn_configs in self._spawn_points.items():
                for spawn_config in spawn_configs:
                    await self._check_and_spawn_monster(room_id, spawn_config)
        except Exception as e:
            logger.error(f"초기 스폰 처리 실패: {e}")

    async def _check_and_spawn_monster(self, room_id: str, spawn_config: Dict[str, Any]) -> None:
        """특정 방에 몬스터 스폰이 필요한지 확인하고 스폰합니다."""
        try:
            monster_template_id = spawn_config.get('monster_template_id')
            max_count = spawn_config.get('max_count', 1)
            spawn_chance = spawn_config.get('spawn_chance', 1.0)

            # 글로벌 제한 확인
            global_limit = self._global_spawn_limits.get(monster_template_id)
            if global_limit is not None:
                all_monsters = await self.get_all_monsters()
                global_count = sum(1 for m in all_monsters 
                                 if m.get_property('template_id') == monster_template_id and m.is_alive)
                if global_count >= global_limit:
                    logger.debug(f"글로벌 스폰 제한 도달: {monster_template_id} ({global_count}/{global_limit})")
                    return

            # 방별 제한 확인
            current_monsters = await self._monster_repo.get_monsters_in_room(room_id)
            template_monsters = [m for m in current_monsters if m.get_property('template_id') == monster_template_id and m.is_alive]

            if len(template_monsters) < max_count:
                import random
                if random.random() <= spawn_chance:
                    await self._spawn_monster_from_template(room_id, monster_template_id)
                    logger.info(f"몬스터 자동 스폰: {room_id}, 현재 {len(template_monsters)+1}/{max_count}")
        except Exception as e:
            logger.error(f"몬스터 스폰 체크 실패 ({room_id}): {e}")

    async def _spawn_monster_from_template(self, room_id: str, template_id: str) -> Optional[Monster]:
        """템플릿을 기반으로 몬스터를 스폰합니다."""
        try:
            template = await self._monster_repo.get_by_id(template_id)
            if not template:
                logger.error(f"몬스터 템플릿을 찾을 수 없음: {template_id}")
                return None

            new_monster = Monster(
                id=str(uuid4()),
                name=template.name.copy(),
                description=template.description.copy(),
                monster_type=template.monster_type,
                behavior=template.behavior,
                stats=MonsterStats(
                    strength=template.stats.strength,
                    dexterity=template.stats.dexterity,
                    constitution=template.stats.constitution,
                    intelligence=template.stats.intelligence,
                    wisdom=template.stats.wisdom,
                    charisma=template.stats.charisma,
                    level=template.stats.level,
                    current_hp=template.stats.get_max_hp()
                ),
                experience_reward=template.experience_reward,
                gold_reward=template.gold_reward,
                drop_items=template.drop_items.copy(),
                spawn_room_id=room_id,
                current_room_id=room_id,
                respawn_time=template.respawn_time,
                is_alive=True,
                aggro_range=template.aggro_range,
                roaming_range=template.roaming_range,
                properties={'template_id': template_id},
                created_at=datetime.now(),
                faction_id=template.faction_id
            )

            created_monster = await self._monster_repo.create(new_monster.to_dict())
            if created_monster:
                logger.info(f"몬스터 스폰됨: {created_monster.get_localized_name()} (방: {room_id})")
                return created_monster
        except Exception as e:
            logger.error(f"몬스터 스폰 실패 ({template_id} -> {room_id}): {e}")
        return None

    async def _respawn_monster(self, monster: Monster) -> bool:
        """몬스터를 리스폰합니다."""
        try:
            success = await self._monster_repo.respawn_monster(monster.id)
            if success:
                logger.info(f"몬스터 리스폰됨: {monster.get_localized_name()} (방: {monster.spawn_room_id})")
            return success
        except Exception as e:
            logger.error(f"몬스터 리스폰 실패 ({monster.id}): {e}")
            return False

    # === 스폰 포인트 관리 ===

    async def add_spawn_point(self, room_id: str, monster_template_id: str, max_count: int = 1, spawn_chance: float = 1.0, room_manager=None) -> None:
        """방에 몬스터 스폰 포인트를 추가합니다."""
        try:
            if room_manager:
                room = await room_manager.get_room(room_id)
                if not room:
                    logger.error(f"스폰 포인트 추가 실패: 방이 존재하지 않음 ({room_id})")
                    return

            template = await self._monster_repo.get_by_id(monster_template_id)
            if not template:
                logger.error(f"스폰 포인트 추가 실패: 몬스터 템플릿이 존재하지 않음 ({monster_template_id})")
                return

            if room_id not in self._spawn_points:
                self._spawn_points[room_id] = []

            spawn_config = {
                'monster_template_id': monster_template_id,
                'max_count': max_count,
                'spawn_chance': spawn_chance
            }
            self._spawn_points[room_id].append(spawn_config)
            logger.info(f"스폰 포인트 추가됨: {room_id} -> {monster_template_id} (최대 {max_count}마리)")
        except Exception as e:
            logger.error(f"스폰 포인트 추가 실패: {e}")

    async def remove_spawn_point(self, room_id: str, monster_template_id: str) -> bool:
        """방에서 몬스터 스폰 포인트를 제거합니다."""
        try:
            if room_id not in self._spawn_points:
                return False

            original_count = len(self._spawn_points[room_id])
            self._spawn_points[room_id] = [
                config for config in self._spawn_points[room_id]
                if config.get('monster_template_id') != monster_template_id
            ]

            removed = len(self._spawn_points[room_id]) < original_count
            if removed:
                logger.info(f"스폰 포인트 제거됨: {room_id} -> {monster_template_id}")

            if not self._spawn_points[room_id]:
                del self._spawn_points[room_id]
            return removed
        except Exception as e:
            logger.error(f"스폰 포인트 제거 실패: {e}")
            return False

    async def get_spawn_points(self) -> Dict[str, List[Dict[str, Any]]]:
        """모든 스폰 포인트 정보를 반환합니다."""
        return self._spawn_points.copy()

    async def get_room_spawn_points(self, room_id: str) -> List[Dict[str, Any]]:
        """특정 방의 스폰 포인트 정보를 반환합니다."""
        return self._spawn_points.get(room_id, []).copy()

    async def clear_spawn_points(self, room_id: Optional[str] = None) -> None:
        """스폰 포인트를 정리합니다."""
        try:
            if room_id:
                if room_id in self._spawn_points:
                    del self._spawn_points[room_id]
                    logger.info(f"방 {room_id}의 스폰 포인트 정리됨")
            else:
                self._spawn_points.clear()
                logger.info("모든 스폰 포인트 정리됨")
        except Exception as e:
            logger.error(f"스폰 포인트 정리 실패: {e}")

    # === 글로벌 스폰 제한 ===

    def set_global_spawn_limit(self, template_id: str, max_count: int) -> None:
        """특정 몬스터 템플릿의 글로벌 최대 스폰 수를 설정합니다."""
        self._global_spawn_limits[template_id] = max_count
        logger.info(f"글로벌 스폰 제한 설정: {template_id} -> {max_count}마리")

    def get_global_spawn_limit(self, template_id: str) -> Optional[int]:
        """특정 몬스터 템플릿의 글로벌 최대 스폰 수를 조회합니다."""
        return self._global_spawn_limits.get(template_id)

    def get_all_global_spawn_limits(self) -> Dict[str, int]:
        """모든 글로벌 스폰 제한 설정을 반환합니다."""
        return self._global_spawn_limits.copy()

    async def cleanup_excess_monsters(self, template_id: str) -> int:
        """글로벌 제한을 초과하는 몬스터를 DB에서 삭제합니다."""
        try:
            global_limit = self._global_spawn_limits.get(template_id)
            if global_limit is None:
                logger.warning(f"글로벌 제한이 설정되지 않음: {template_id}")
                return 0

            all_monsters = await self.get_all_monsters()
            template_monsters = [m for m in all_monsters 
                               if m.get_property('template_id') == template_id and m.is_alive]

            excess_count = len(template_monsters) - global_limit
            if excess_count <= 0:
                logger.info(f"초과 몬스터 없음: {template_id} ({len(template_monsters)}/{global_limit})")
                return 0

            template_monsters.sort(key=lambda m: m.created_at)
            monsters_to_delete = template_monsters[:excess_count]

            deleted_count = 0
            for monster in monsters_to_delete:
                success = await self.delete_monster(monster.id)
                if success:
                    deleted_count += 1
                    logger.info(f"초과 몬스터 삭제: {monster.id} ({monster.get_localized_name('ko')})")

            logger.info(f"초과 몬스터 정리 완료: {template_id} - {deleted_count}마리 삭제")
            return deleted_count
        except Exception as e:
            logger.error(f"초과 몬스터 정리 실패 ({template_id}): {e}")
            return 0

    async def cleanup_all_excess_monsters(self) -> Dict[str, int]:
        """모든 템플릿에 대해 글로벌 제한을 초과하는 몬스터를 정리합니다."""
        try:
            result = {}
            for template_id in self._global_spawn_limits.keys():
                deleted_count = await self.cleanup_excess_monsters(template_id)
                if deleted_count > 0:
                    result[template_id] = deleted_count
            logger.info(f"전체 초과 몬스터 정리 완료: {result}")
            return result
        except Exception as e:
            logger.error(f"전체 초과 몬스터 정리 실패: {e}")
            return {}

    # === 몬스터 관리 ===

    async def get_monsters_in_room(self, room_id: str) -> List[Monster]:
        """특정 방에 있는 모든 살아있는 몬스터를 조회합니다."""
        try:
            all_monsters = await self._monster_repo.get_monsters_in_room(room_id)
            return [monster for monster in all_monsters if monster.is_alive]
        except Exception as e:
            logger.error(f"방 내 몬스터 조회 실패 ({room_id}): {e}")
            return []

    async def kill_monster(self, monster_id: str) -> bool:
        """몬스터를 사망 처리합니다."""
        try:
            return await self._monster_repo.kill_monster(monster_id)
        except Exception as e:
            logger.error(f"몬스터 사망 처리 실패 ({monster_id}): {e}")
            return False

    async def get_monster(self, monster_id: str) -> Optional[Monster]:
        """몬스터 ID로 몬스터 정보를 조회합니다."""
        try:
            return await self._monster_repo.get_by_id(monster_id)
        except Exception as e:
            logger.error(f"몬스터 조회 실패 ({monster_id}): {e}")
            raise

    async def get_all_monsters(self) -> List[Monster]:
        """모든 몬스터를 조회합니다."""
        try:
            return await self._monster_repo.get_all()
        except Exception as e:
            logger.error(f"전체 몬스터 조회 실패: {e}")
            raise

    async def create_monster(self, monster_data: Dict[str, Any]) -> Monster:
        """새로운 몬스터를 생성합니다."""
        try:
            monster = Monster(
                id=monster_data.get('id'),
                name=monster_data.get('name', {}),
                description=monster_data.get('description', {}),
                monster_type=monster_data.get('monster_type', MonsterType.PASSIVE),
                behavior=monster_data.get('behavior', MonsterBehavior.STATIONARY),
                stats=monster_data.get('stats', MonsterStats()),
                experience_reward=monster_data.get('experience_reward', 50),
                gold_reward=monster_data.get('gold_reward', 10),
                drop_items=monster_data.get('drop_items', []),
                spawn_room_id=monster_data.get('spawn_room_id'),
                current_room_id=monster_data.get('current_room_id'),
                respawn_time=monster_data.get('respawn_time', 300),
                aggro_range=monster_data.get('aggro_range', 1),
                roaming_range=monster_data.get('roaming_range', 2),
                properties=monster_data.get('properties', {})
            )
            created_monster = await self._monster_repo.create(monster.to_dict())
            logger.info(f"새 몬스터 생성됨: {created_monster.id}")
            return created_monster
        except Exception as e:
            logger.error(f"몬스터 생성 실패: {e}")
            raise

    async def update_monster(self, monster: Monster) -> bool:
        """몬스터 정보를 업데이트합니다."""
        try:
            updated_monster = await self._monster_repo.update(monster.id, monster.to_dict())
            if updated_monster:
                logger.info(f"몬스터 업데이트됨: {monster.id}")
                return True
            return False
        except Exception as e:
            logger.error(f"몬스터 업데이트 실패 ({monster.id}): {e}")
            raise

    async def delete_monster(self, monster_id: str) -> bool:
        """몬스터를 삭제합니다."""
        try:
            success = await self._monster_repo.delete(monster_id)
            if success:
                logger.info(f"몬스터 삭제됨: {monster_id}")
            return success
        except Exception as e:
            logger.error(f"몬스터 삭제 실패 ({monster_id}): {e}")
            raise

    async def move_monster_to_room(self, monster_id: str, room_id: str, room_manager=None, game_engine=None) -> bool:
        """몬스터를 특정 방으로 이동시킵니다."""
        try:
            if room_manager:
                room = await room_manager.get_room(room_id)
                if not room:
                    logger.warning(f"대상 방이 존재하지 않음: {room_id}")
                    return False

            monster = await self.get_monster(monster_id)
            if not monster:
                logger.warning(f"몬스터가 존재하지 않음: {monster_id}")
                return False

            # 이전 방 ID 저장
            old_room_id = monster.current_room_id

            # 몬스터 위치 업데이트
            monster.current_room_id = room_id
            success = await self.update_monster(monster)
            
            if success:
                logger.info(f"몬스터 {monster_id}를 방 {room_id}로 이동")
                
                # 이동 메시지 브로드캐스트 (game_engine이 제공된 경우)
                if game_engine:
                    monster_name = monster.get_localized_name('ko')
                    
                    # 이전 방의 플레이어들에게 퇴장 알림
                    if old_room_id and old_room_id != room_id:
                        leave_message = {
                            "type": "room_message",
                            "message": f"🐾 {monster_name}이(가) 떠났습니다.",
                            "timestamp": datetime.now().isoformat()
                        }
                        await game_engine.broadcast_to_room(old_room_id, leave_message)
                    
                    # 새 방의 플레이어들에게 입장 알림
                    enter_message = {
                        "type": "room_message",
                        "message": f"🐾 {monster_name}이(가) 나타났습니다.",
                        "timestamp": datetime.now().isoformat()
                    }
                    await game_engine.broadcast_to_room(room_id, enter_message)
                    
            return success
        except Exception as e:
            logger.error(f"몬스터 방 이동 실패 ({monster_id} -> {room_id}): {e}")
            raise

    async def find_monsters_by_name(self, name_pattern: str, locale: str = 'ko') -> List[Monster]:
        """이름 패턴으로 몬스터를 검색합니다."""
        try:
            all_monsters = await self.get_all_monsters()
            matching_monsters = []
            for monster in all_monsters:
                if not monster.is_alive:
                    continue
                monster_name = monster.get_localized_name(locale).lower()
                if name_pattern.lower() in monster_name:
                    matching_monsters.append(monster)
            return matching_monsters
        except Exception as e:
            logger.error(f"몬스터 이름 검색 실패 ({name_pattern}): {e}")
            raise

    # === 몬스터 로밍 ===

    async def _process_monster_roaming(self) -> None:
        """로밍 가능한 몬스터들의 이동을 처리합니다."""
        try:
            all_monsters = await self.get_all_monsters()
            alive_monsters = [m for m in all_monsters if m.is_alive]

            for monster in alive_monsters:
                if not monster.can_roam():
                    continue

                roaming_config = monster.get_property('roaming_config')
                if not roaming_config:
                    continue

                roam_chance = roaming_config.get('roam_chance', 0.5)
                import random
                if random.random() > roam_chance:
                    continue

                await self._roam_monster(monster, roaming_config, self._room_manager, self._game_engine)
        except Exception as e:
            logger.error(f"몬스터 로밍 처리 실패: {e}")

    async def _roam_monster(self, monster: Monster, roaming_config: Dict[str, Any], room_manager=None, game_engine=None) -> None:
        """몬스터를 로밍 범위 내에서 이동시킵니다."""
        try:
            if not monster.current_room_id:
                return

            if room_manager:
                current_room = await room_manager.get_room(monster.current_room_id)
                if not current_room or current_room.x is None or current_room.y is None:
                    return

                roaming_area = roaming_config.get('roaming_area', {})
                min_x = roaming_area.get('min_x')
                max_x = roaming_area.get('max_x')
                min_y = roaming_area.get('min_y')
                max_y = roaming_area.get('max_y')

                available_exits = []
                for direction, target_room_id in current_room.exits.items():
                    target_room = await room_manager.get_room(target_room_id)
                    if not target_room or target_room.x is None or target_room.y is None:
                        continue

                    if min_x is not None and target_room.x < min_x:
                        continue
                    if max_x is not None and target_room.x > max_x:
                        continue
                    if min_y is not None and target_room.y < min_y:
                        continue
                    if max_y is not None and target_room.y > max_y:
                        continue

                    available_exits.append((direction, target_room_id))

                if not available_exits:
                    return

                import random
                _, target_room_id = random.choice(available_exits)
                success = await self.move_monster_to_room(monster.id, target_room_id, room_manager, game_engine)
                if success:
                    logger.debug(f"몬스터 {monster.get_localized_name('ko')}가 {target_room_id}로 이동")
        except Exception as e:
            logger.error(f"몬스터 로밍 실패 ({monster.id}): {e}")

    # === 선공 시스템 ===

    async def check_aggressive_monsters(self, player_id: str, room_id: str, combat_system) -> Optional[Monster]:
        """방에 입장한 플레이어에 대해 선공형 몬스터의 자동 공격을 확인합니다."""
        try:
            if combat_system.is_in_combat(player_id):
                return None

            monsters = await self.get_monsters_in_room(room_id)
            for monster in monsters:
                if monster.monster_type != MonsterType.AGGRESSIVE:
                    continue

                if self._is_monster_in_combat(monster.id, combat_system):
                    continue

                if monster.current_room_id == room_id:
                    logger.info(f"선공형 몬스터 {monster.get_localized_name('ko')}가 플레이어 {player_id}를 공격합니다")
                    return monster
            return None
        except Exception as e:
            logger.error(f"선공형 몬스터 확인 실패: {e}")
            return None

    def _is_monster_in_combat(self, monster_id: str, combat_system) -> bool:
        """몬스터가 현재 전투 중인지 확인합니다."""
        try:
            for combat in combat_system.active_combats.values():
                if combat.monster.id == monster_id:
                    return True
            return False
        except Exception as e:
            logger.error(f"몬스터 전투 상태 확인 실패: {e}")
            return False

    async def setup_default_spawn_points(self, room_manager=None) -> None:
        """기본 스폰 포인트들을 설정합니다."""
        try:
            small_rat_template = await self._monster_repo.get_by_id('template_small_rat')
            if not small_rat_template:
                logger.info("작은 쥐 템플릿이 없습니다. 스폰 포인트 설정을 건너뜁니다.")
                return

            if room_manager:
                all_rooms = await room_manager.get_all_rooms()
                plains_rooms = []
                for room in all_rooms:
                    desc_ko = room.description.get('ko', '')
                    if '평원' in desc_ko and room.x is not None and room.y is not None:
                        if room.y >= -2:
                            plains_rooms.append(room)

                if not plains_rooms:
                    logger.info("평원 방을 찾을 수 없습니다.")
                    return

                spawn_count = 0
                for room in plains_rooms[:10]:
                    await self.add_spawn_point(
                        room_id=room.id,
                        monster_template_id='template_small_rat',
                        max_count=5,
                        spawn_chance=0.5,
                        room_manager=room_manager
                    )
                    spawn_count += 1

                logger.info(f"작은 쥐 스폰 포인트 {spawn_count}개 설정 완료")
        except Exception as e:
            logger.error(f"기본 스폰 포인트 설정 실패: {e}")
