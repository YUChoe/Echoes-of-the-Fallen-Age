# -*- coding: utf-8 -*-
"""템플릿 로더 모듈"""
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, TYPE_CHECKING

from ..game.monster import Monster, MonsterType, MonsterBehavior, MonsterStats

if TYPE_CHECKING:
    from ..game.models import GameObject

logger = logging.getLogger(__name__)


class TemplateLoader:
    """설정 파일에서 템플릿을 로드하는 클래스"""

    def __init__(self, config_dir: str = "configs") -> None:
        """TemplateLoader를 초기화합니다."""
        self.config_dir = Path(config_dir)
        self.monster_templates: Dict[str, Dict[str, Any]] = {}
        self.item_templates: Dict[str, Dict[str, Any]] = {}
        logger.info(f"TemplateLoader 초기화: {config_dir}")

    async def load_all_templates(self) -> None:
        """모든 템플릿을 로드합니다."""
        await self.load_monster_templates()
        await self.load_item_templates()
        logger.info(f"템플릿 로드 완료: 몬스터 {len(self.monster_templates)}개, 아이템 {len(self.item_templates)}개")

    async def load_monster_templates(self) -> None:
        """몬스터 템플릿을 로드합니다."""
        monster_dir = self.config_dir / "monsters"
        if not monster_dir.exists():
            logger.warning(f"몬스터 설정 디렉토리가 존재하지 않음: {monster_dir}")
            return

        for json_file in monster_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)

                template_id = template_data.get('template_id')
                if not template_id:
                    logger.warning(f"template_id가 없는 파일: {json_file}")
                    continue

                self.monster_templates[template_id] = template_data
                logger.debug(f"몬스터 템플릿 로드: {template_id} from {json_file.name}")
            except Exception as e:
                logger.error(f"몬스터 템플릿 로드 실패 ({json_file}): {e}")

    async def load_item_templates(self) -> None:
        """아이템 템플릿을 로드합니다."""
        item_dir = self.config_dir / "items"
        if not item_dir.exists():
            logger.warning(f"아이템 설정 디렉토리가 존재하지 않음: {item_dir}")
            return

        for json_file in item_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)

                # 단일 템플릿 또는 템플릿 배열 처리
                if isinstance(template_data, list):
                    for template in template_data:
                        template_id = template.get('template_id')
                        if template_id:
                            self.item_templates[template_id] = template
                            logger.debug(f"아이템 템플릿 로드: {template_id} from {json_file.name}")
                else:
                    template_id = template_data.get('template_id')
                    if template_id:
                        self.item_templates[template_id] = template_data
                        logger.debug(f"아이템 템플릿 로드: {template_id} from {json_file.name}")
            except Exception as e:
                logger.error(f"아이템 템플릿 로드 실패 ({json_file}): {e}")

    def get_monster_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """몬스터 템플릿을 조회합니다."""
        return self.monster_templates.get(template_id)

    def get_item_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """아이템 템플릿을 조회합니다."""
        return self.item_templates.get(template_id)

    def get_all_monster_templates(self) -> Dict[str, Dict[str, Any]]:
        """모든 몬스터 템플릿을 반환합니다."""
        return self.monster_templates.copy()

    def get_all_item_templates(self) -> Dict[str, Dict[str, Any]]:
        """모든 아이템 템플릿을 반환합니다."""
        return self.item_templates.copy()

    def create_monster_from_template(self, template_id: str, monster_id: str, room_id: str) -> Optional[Monster]:
        """템플릿에서 몬스터 인스턴스를 생성합니다."""
        template = self.get_monster_template(template_id)
        if not template:
            logger.error(f"몬스터 템플릿을 찾을 수 없음: {template_id}")
            return None

        try:
            # 몬스터 타입 변환
            monster_type_str = template.get('monster_type', 'PASSIVE')
            monster_type = MonsterType[monster_type_str.upper()]

            # 행동 타입 변환
            behavior_str = template.get('behavior', 'STATIONARY')
            behavior = MonsterBehavior[behavior_str.upper()]

            # 스탯 생성
            stats_data = template.get('stats', {})
            stats = MonsterStats(
                strength=stats_data.get('strength', 10),
                dexterity=stats_data.get('dexterity', 10),
                constitution=stats_data.get('constitution', 10),
                intelligence=stats_data.get('intelligence', 10),
                wisdom=stats_data.get('wisdom', 10),
                charisma=stats_data.get('charisma', 10),
                level=stats_data.get('level', 1),
                current_hp=stats_data.get('current_hp', stats_data.get('constitution', 10) * 5)
            )

            # 몬스터 생성
            monster = Monster(
                id=monster_id,
                name=template.get('name', {}),
                description=template.get('description', {}),
                monster_type=monster_type,
                behavior=behavior,
                stats=stats,
                gold_reward=template.get('gold_reward', 0),
                drop_items=template.get('drop_items', []),
                x=None,  # 좌표는 나중에 설정
                y=None,  # 좌표는 나중에 설정
                respawn_time=template.get('respawn_time', 300),
                aggro_range=template.get('aggro_range', 0),
                roaming_range=template.get('roaming_range', 0),
                faction_id=template.get('faction_id'),
                properties={'template_id': template_id, 'is_template': False}
            )

            logger.debug(f"템플릿에서 몬스터 생성: {monster_id} (템플릿: {template_id})")
            return monster
        except Exception as e:
            logger.error(f"템플릿에서 몬스터 생성 실패 ({template_id}): {e}")
            return None

    def create_item_from_template(self, template_id: str, item_id: str, location_type: str = "room", location_id: Optional[str] = None) -> Optional['GameObject']:
        """템플릿에서 아이템 인스턴스를 생성합니다."""
        from ..game.models import GameObject

        template = self.get_item_template(template_id)
        if not template:
            logger.error(f"아이템 템플릿을 찾을 수 없음: {template_id}")
            return None

        try:
            # 이름과 설명을 딕셔너리 형태로 변환
            name = {}
            if template.get('name_en'):
                name['en'] = template['name_en']
            if template.get('name_ko'):
                name['ko'] = template['name_ko']

            # 이름이 비어있으면 기본값 설정
            if not name:
                name = {'ko': template_id, 'en': template_id}

            description = {}
            if template.get('description_en'):
                description['en'] = template['description_en']
            if template.get('description_ko'):
                description['ko'] = template['description_ko']

            # 설명이 비어있으면 기본값 설정
            if not description:
                description = {'ko': f'{template_id} 아이템입니다.', 'en': f'This is {template_id} item.'}

            # 아이템 생성
            item = GameObject(
                id=item_id,
                name=name,
                description=description,
                location_type=location_type,
                location_id=location_id,
                properties=template.get('properties', {}),
                weight=template.get('weight', 1.0),
                max_stack=template.get('max_stack', 1),
                equipment_slot=template.get('equipment_slot'),
                is_equipped=False
            )

            # 템플릿 ID를 속성에 추가
            item.properties['template_id'] = template_id
            item.properties['is_template'] = False

            logger.debug(f"템플릿에서 아이템 생성: {item_id} (템플릿: {template_id})")
            return item
        except Exception as e:
            logger.error(f"템플릿에서 아이템 생성 실패 ({template_id}): {e}")
            return None

    def get_spawn_config(self, template_id: str) -> Optional[Dict[str, Any]]:
        """템플릿의 스폰 설정을 조회합니다."""
        template = self.get_monster_template(template_id)
        if template:
            return template.get('spawn_config')
        return None