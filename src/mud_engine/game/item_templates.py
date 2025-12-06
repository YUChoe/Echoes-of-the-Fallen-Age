# -*- coding: utf-8 -*-
"""
아이템 템플릿 시스템
"""

import logging
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
    object_type: str  # "item", "currency", "essence"
    category: str  # "currency", "consumable", "misc"
    weight: float = 0.1
    properties: Dict[str, Any] = field(default_factory=dict)
    stackable: bool = True  # 중첩 가능 여부
    max_stack: int = 999  # 최대 중첩 개수
    
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
        instance_properties['stackable'] = self.stackable
        instance_properties['max_stack'] = self.max_stack
        
        return {
            'id': instance_id,
            'name': {'en': self.name_en, 'ko': self.name_ko},
            'description': {'en': self.description_en, 'ko': self.description_ko},
            'object_type': self.object_type,
            'location_type': location_type,
            'location_id': location_id,
            'properties': instance_properties,
            'weight': self.weight * quantity,
            'category': self.category,
            'equipment_slot': None,
            'is_equipped': False
        }


class ItemTemplateManager:
    """아이템 템플릿 관리자"""
    
    def __init__(self):
        """아이템 템플릿 관리자 초기화"""
        self.templates: Dict[str, ItemTemplate] = {}
        self._register_default_templates()
        logger.info(f"ItemTemplateManager 초기화 완료 - {len(self.templates)}개 템플릿 등록")
    
    def _register_default_templates(self):
        """기본 아이템 템플릿 등록"""
        
        # 골드 코인
        self.register_template(ItemTemplate(
            template_id="gold_coin",
            name_en="Gold Coin",
            name_ko="골드",
            description_en="A shiny gold coin.",
            description_ko="반짝이는 금화입니다.",
            object_type="item",
            category="currency",
            weight=0.01,
            properties={'value': 1},
            stackable=True,
            max_stack=9999
        ))
        
        # EOL (Essence of Life)
        self.register_template(ItemTemplate(
            template_id="essence_of_life",
            name_en="Essence of Life",
            name_ko="생명의 정수",
            description_en="A glowing essence extracted from a defeated creature.",
            description_ko="처치한 생명체에서 추출한 빛나는 정수입니다.",
            object_type="consumable",
            category="consumable",
            weight=0.0,  # 무게 없음
            properties={'essence_type': 'life', 'power': 1},
            stackable=True,
            max_stack=999
        ))
    
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
