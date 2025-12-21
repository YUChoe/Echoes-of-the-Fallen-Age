# -*- coding: utf-8 -*-
"""
아이템 템플릿 시스템
"""

import logging
import json
import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class ItemTemplate:
    """아이템 템플릿"""

    template_id: str  # 템플릿 ID (예: "gold_coin", "essence_of_life")
    name_en: str
    name_ko: str
    description_en: str
    description_ko: str
    weight: float = 0.1
    properties: Dict[str, Any] = field(default_factory=dict)
    max_stack: int = 1  # 최대 스택 개수 (1이면 스택 불가)

    def create_instance(
        self,
        location_type: str = "room",
        location_id: Optional[str] = None,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """
        템플릿으로부터 아이템 인스턴스 생성

        Args:
            location_type: 위치 타입 ("room", "inventory")
            location_id: 위치 ID (room_id 또는 player_id)
            quantity: 수량

        Returns:
            Dict: GameObject 생성용 데이터
        """
        instance_id = str(uuid4())

        # properties에 템플릿 정보와 수량 추가
        instance_properties = self.properties.copy()
        instance_properties['template_id'] = self.template_id
        instance_properties['quantity'] = quantity

        return {
            'id': instance_id,
            'name': {'en': self.name_en, 'ko': self.name_ko},
            'description': {'en': self.description_en, 'ko': self.description_ko},
            'location_type': location_type,
            'location_id': location_id,
            'properties': instance_properties,
            'weight': self.weight * quantity,
            'max_stack': self.max_stack,
            'equipment_slot': None,
            'is_equipped': False
        }


class ItemTemplateManager:
    """아이템 템플릿 관리자"""

    def __init__(self, config_dir: str = "configs/items"):
        """아이템 템플릿 관리자 초기화"""
        self.templates: Dict[str, ItemTemplate] = {}
        self.config_dir = config_dir
        self._load_templates_from_config()
        logger.info(f"ItemTemplateManager 초기화 완료 - {len(self.templates)}개 템플릿 등록")

    def _load_templates_from_config(self):
        """설정 파일에서 아이템 템플릿 로드"""
        if not os.path.exists(self.config_dir):
            logger.warning(f"아이템 템플릿 디렉토리가 존재하지 않습니다: {self.config_dir}")
            return

        for filename in os.listdir(self.config_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.config_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # 단일 템플릿 파일인지 다중 템플릿 파일인지 확인
                    if 'template_id' in data:
                        # 단일 템플릿
                        self._create_template_from_data(data)
                    else:
                        # 다중 템플릿 (딕셔너리 형태)
                        for template_data in data.values():
                            self._create_template_from_data(template_data)

                    logger.debug(f"아이템 템플릿 파일 로드 완료: {filename}")

                except Exception as e:
                    logger.error(f"아이템 템플릿 파일 로드 실패 {filename}: {e}")

    def _create_template_from_data(self, data: Dict[str, Any]):
        """데이터에서 ItemTemplate 생성 및 등록"""
        try:
            template = ItemTemplate(
                template_id=data['template_id'],
                name_en=data['name_en'],
                name_ko=data['name_ko'],
                description_en=data['description_en'],
                description_ko=data['description_ko'],
                weight=data.get('weight', 0.1),
                properties=data.get('properties', {}),
                max_stack=data.get('max_stack', 1)
            )
            self.register_template(template)
        except KeyError as e:
            logger.error(f"아이템 템플릿 데이터에 필수 필드가 없습니다: {e}")
        except Exception as e:
            logger.error(f"아이템 템플릿 생성 실패: {e}")

    def register_template(self, template: ItemTemplate):
        """템플릿 등록"""
        self.templates[template.template_id] = template
        logger.debug(f"아이템 템플릿 등록: {template.template_id} ({template.name_ko})")

    def get_template(self, template_id: str) -> Optional[ItemTemplate]:
        """템플릿 조회"""
        return self.templates.get(template_id)

    def create_item(
        self,
        template_id: str,
        location_type: str = "room",
        location_id: Optional[str] = None,
        quantity: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        템플릿으로부터 아이템 생성

        Args:
            template_id: 템플릿 ID
            location_type: 위치 타입
            location_id: 위치 ID
            quantity: 수량

        Returns:
            Dict: GameObject 생성용 데이터 (템플릿이 없으면 None)
        """
        template = self.get_template(template_id)
        if not template:
            logger.error(f"아이템 템플릿을 찾을 수 없습니다: {template_id}")
            return None

        return template.create_instance(location_type, location_id, quantity)
