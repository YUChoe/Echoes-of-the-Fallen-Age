"""
종족 관계 판정 규칙 단위 테스트

faction_rules 모듈은 telnet_session.py 의 _is_friendly_faction 과
_is_neutral_faction 규칙을 옮긴 것이다. 원본 메서드는 프레젠터 제거 단계에서
사라졌으므로, 여기서는 옮겨온 규칙의 기대값을 명시해 고정한다.
"""

import pytest

from src.mud_engine.game import faction_rules

# (player_faction, target_faction) 조합
_CASES = [
    ("ash_knights", "ash_knights"),
    ("ash_knights", "animals"),
    ("ash_knights", "wild"),
    ("ash_knights", None),
    ("ash_knights", ""),
    ("wild", "wild"),
    ("wild", "ash_knights"),
    ("wild", "animals"),
    ("wild", None),
    ("unknown_faction", "animals"),
    ("unknown_faction", "unknown_faction"),
]

# (player_faction, target_faction, is_friendly, is_neutral)
# 원본 규칙: 같은 종족이면 우호, ash_knights 에게 animals 만 중립, 그 밖은 모두 거짓
_EXPECTED = [
    ("ash_knights", "ash_knights", True, False),
    ("ash_knights", "animals", False, True),
    ("ash_knights", "wild", False, False),
    ("ash_knights", None, False, False),
    ("ash_knights", "", False, False),
    ("wild", "wild", True, False),
    ("wild", "ash_knights", False, False),
    ("wild", "animals", False, False),
    ("wild", None, False, False),
    ("unknown_faction", "animals", False, False),
    ("unknown_faction", "unknown_faction", True, False),
]


class TestPreservedRules:
    """세션 계층에서 옮겨온 판정 규칙"""

    @pytest.mark.parametrize(
        ("player_faction", "target_faction", "expected", "_unused"), _EXPECTED
    )
    def test_friendly(self, player_faction, target_faction, expected, _unused):
        """우호 판정이 원본 규칙과 같다"""
        assert faction_rules.is_friendly(player_faction, target_faction) is expected

    @pytest.mark.parametrize(
        ("player_faction", "target_faction", "_unused", "expected"), _EXPECTED
    )
    def test_neutral(self, player_faction, target_faction, _unused, expected):
        """중립 판정이 원본 규칙과 같다"""
        assert faction_rules.is_neutral(player_faction, target_faction) is expected


class TestGetDisposition:
    """disposition 산출 규칙"""

    def test_same_faction_is_friendly(self):
        """같은 종족은 우호"""
        assert faction_rules.get_disposition("ash_knights", "ash_knights") == faction_rules.FRIENDLY
        assert faction_rules.get_disposition("wild", "wild") == faction_rules.FRIENDLY

    def test_animals_are_neutral_for_ash_knights(self):
        """ash_knights 기준 animals 는 중립"""
        assert faction_rules.get_disposition("ash_knights", "animals") == faction_rules.NEUTRAL

    def test_other_faction_is_hostile(self):
        """그 밖의 종족은 적대"""
        assert faction_rules.get_disposition("ash_knights", "wild") == faction_rules.HOSTILE

    def test_missing_target_faction_is_hostile(self):
        """대상 종족이 없으면 적대"""
        assert faction_rules.get_disposition("ash_knights", None) == faction_rules.HOSTILE
        assert faction_rules.get_disposition("ash_knights", "") == faction_rules.HOSTILE

    def test_missing_player_faction_uses_default(self):
        """플레이어 종족이 없으면 기본 종족으로 판정한다"""
        assert faction_rules.get_disposition(None, "ash_knights") == faction_rules.FRIENDLY
        assert faction_rules.get_disposition(None, "animals") == faction_rules.NEUTRAL
        assert faction_rules.get_disposition(None, "wild") == faction_rules.HOSTILE

    def test_animals_not_neutral_for_unknown_player_faction(self):
        """중립 표에 없는 플레이어 종족에게 animals 는 적대"""
        assert faction_rules.get_disposition("wild", "animals") == faction_rules.HOSTILE

    def test_returns_only_defined_values(self):
        """반환값은 정의된 세 값 중 하나다"""
        allowed = {faction_rules.FRIENDLY, faction_rules.NEUTRAL, faction_rules.HOSTILE}

        for player_faction, target_faction in _CASES:
            assert faction_rules.get_disposition(player_faction, target_faction) in allowed
