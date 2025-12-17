# -*- coding: utf-8 -*-
"""퀘스트 시스템"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class QuestStatus(Enum):
    """퀘스트 상태"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class QuestType(Enum):
    """퀘스트 타입"""
    TUTORIAL = "tutorial"
    MAIN = "main"
    SIDE = "side"
    DAILY = "daily"


@dataclass
class QuestObjective:
    """퀘스트 목표"""
    id: str
    description: Dict[str, str]  # 언어별 설명
    target_type: str  # 'collect', 'kill', 'talk', 'visit'
    target_id: str  # 대상 ID
    target_count: int = 1
    current_count: int = 0
    completed: bool = False

    def is_completed(self) -> bool:
        """목표 완료 여부 확인"""
        return self.current_count >= self.target_count

    def update_progress(self, count: int = 1) -> bool:
        """진행도 업데이트"""
        self.current_count = min(self.current_count + count, self.target_count)
        self.completed = self.is_completed()
        return self.completed

    def get_description(self, locale: str = "en") -> str:
        """로케일에 맞는 설명 반환"""
        return self.description.get(locale, self.description.get("en", ""))


@dataclass
class QuestReward:
    """퀘스트 보상"""
    experience: int = 0
    gold: int = 0
    items: List[str] = field(default_factory=list)  # 아이템 ID 목록
    equipment: List[str] = field(default_factory=list)  # 장비 ID 목록


@dataclass
class Quest:
    """퀘스트 정의"""
    id: str
    name: Dict[str, str]  # 언어별 이름
    description: Dict[str, str]  # 언어별 설명
    quest_type: QuestType
    level_requirement: int = 1
    prerequisites: List[str] = field(default_factory=list)  # 선행 퀘스트 ID
    objectives: List[QuestObjective] = field(default_factory=list)
    rewards: QuestReward = field(default_factory=QuestReward)
    auto_complete: bool = False  # 목표 달성 시 자동 완료
    repeatable: bool = False

    def get_name(self, locale: str = "en") -> str:
        """로케일에 맞는 이름 반환"""
        return self.name.get(locale, self.name.get("en", ""))

    def get_description(self, locale: str = "en") -> str:
        """로케일에 맞는 설명 반환"""
        return self.description.get(locale, self.description.get("en", ""))

    def can_start(self, player_level: int, completed_quests: List[str]) -> bool:
        """퀘스트 시작 가능 여부 확인"""
        # 레벨 요구사항 확인
        if player_level < self.level_requirement:
            return False

        # 선행 퀘스트 완료 확인
        for prereq in self.prerequisites:
            if prereq not in completed_quests:
                return False

        return True

    def is_completed(self) -> bool:
        """퀘스트 완료 여부 확인"""
        return all(obj.is_completed() for obj in self.objectives)


@dataclass
class PlayerQuest:
    """플레이어별 퀘스트 진행 상황"""
    quest_id: str
    status: QuestStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    objectives_progress: Dict[str, int] = field(default_factory=dict)

    def update_objective(self, objective_id: str, count: int = 1) -> bool:
        """목표 진행도 업데이트"""
        current = self.objectives_progress.get(objective_id, 0)
        self.objectives_progress[objective_id] = current + count
        return True


class QuestManager:
    """퀘스트 관리자"""

    def __init__(self):
        self.quests: Dict[str, Quest] = {}
        self._load_tutorial_quests()

    def _load_tutorial_quests(self):
        """튜토리얼 퀘스트 로드"""
        # 튜토리얼 퀘스트: 기본 장비 받기
        tutorial_quest = Quest(
            id="tutorial_basic_equipment",
            name={
                "en": "Basic Equipment",
                "ko": "기본 장비"
            },
            description={
                "en": "Visit the church and receive basic equipment from the monk.",
                "ko": "교회를 방문하여 수도사로부터 기본 장비를 받으세요."
            },
            quest_type=QuestType.TUTORIAL,
            level_requirement=1,
            objectives=[
                QuestObjective(
                    id="talk_to_monk",
                    description={
                        "en": "Talk to the monk at the church",
                        "ko": "교회의 수도사와 대화하기"
                    },
                    target_type="talk",
                    target_id="church_monk",
                    target_count=1
                ),
                QuestObjective(
                    id="collect_essence",
                    description={
                        "en": "Collect 10 Essence of Life",
                        "ko": "생명의 정수 10개 수집하기"
                    },
                    target_type="collect",
                    target_id="essence_of_life",
                    target_count=10
                )
            ],
            rewards=QuestReward(
                experience=100,
                gold=50,
                items=["club", "linen_shirt", "linen_pants"]
            ),
            auto_complete=False
        )

        self.quests[tutorial_quest.id] = tutorial_quest
        logger.info(f"튜토리얼 퀘스트 로드됨: {tutorial_quest.id}")

    def get_quest(self, quest_id: str) -> Optional[Quest]:
        """퀘스트 조회"""
        return self.quests.get(quest_id)

    def get_available_quests(self, player_level: int, completed_quests: List[str]) -> List[Quest]:
        """플레이어가 시작할 수 있는 퀘스트 목록"""
        available = []
        for quest in self.quests.values():
            if quest.can_start(player_level, completed_quests):
                available.append(quest)
        return available

    def start_quest(self, player_id: str, quest_id: str) -> bool:
        """퀘스트 시작"""
        quest = self.get_quest(quest_id)
        if not quest:
            return False

        # 플레이어 퀘스트 진행 상황 초기화
        player_quest = PlayerQuest(
            quest_id=quest_id,
            status=QuestStatus.IN_PROGRESS,
            started_at=datetime.now()
        )

        logger.info(f"플레이어 {player_id}가 퀘스트 {quest_id} 시작")
        return True

    def update_quest_progress(self, player_id: str, quest_id: str, objective_id: str, count: int = 1) -> bool:
        """퀘스트 진행도 업데이트"""
        quest = self.get_quest(quest_id)
        if not quest:
            return False

        # 목표 찾기
        objective = None
        for obj in quest.objectives:
            if obj.id == objective_id:
                objective = obj
                break

        if not objective:
            return False

        # 진행도 업데이트
        completed = objective.update_progress(count)
        logger.info(f"플레이어 {player_id} 퀘스트 {quest_id} 목표 {objective_id} 진행: {objective.current_count}/{objective.target_count}")

        # 퀘스트 완료 확인
        if quest.is_completed():
            logger.info(f"플레이어 {player_id} 퀘스트 {quest_id} 완료!")
            return True

        return completed

    def complete_quest(self, player_id: str, quest_id: str) -> Optional[QuestReward]:
        """퀘스트 완료 처리"""
        quest = self.get_quest(quest_id)
        if not quest:
            return None

        if not quest.is_completed():
            return None

        logger.info(f"플레이어 {player_id} 퀘스트 {quest_id} 완료 처리")
        return quest.rewards


# 전역 퀘스트 매니저 인스턴스
_quest_manager = None


def get_quest_manager() -> QuestManager:
    """전역 퀘스트 매니저 인스턴스 반환"""
    global _quest_manager
    if _quest_manager is None:
        _quest_manager = QuestManager()
    return _quest_manager