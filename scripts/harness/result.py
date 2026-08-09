#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""시나리오 검증 결과 수집

각 검증 항목의 통과, 실패, 건너뜀을 기록하고 종료 코드를 산출한다.
서버가 실행되지 않아 수행할 수 없는 항목은 실패가 아니라 건너뜀으로 처리한다.
"""

from dataclasses import dataclass, field
from enum import Enum


class Status(Enum):
    """검증 항목의 상태"""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class Check:
    """검증 항목 하나"""

    name: str
    status: Status
    detail: str = ""


@dataclass
class ScenarioResult:
    """한 시나리오의 검증 결과"""

    scenario: str
    checks: list[Check] = field(default_factory=list)

    def ok(self, name: str, detail: str = "") -> None:
        """통과를 기록한다."""
        self.checks.append(Check(name, Status.PASS, detail))
        self._emit(Status.PASS, name, detail)

    def fail(self, name: str, detail: str = "") -> None:
        """실패를 기록한다."""
        self.checks.append(Check(name, Status.FAIL, detail))
        self._emit(Status.FAIL, name, detail)

    def skip(self, name: str, detail: str = "") -> None:
        """건너뜀을 기록한다. 종료 코드에 영향을 주지 않는다."""
        self.checks.append(Check(name, Status.SKIP, detail))
        self._emit(Status.SKIP, name, detail)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.status is Status.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if c.status is Status.FAIL)

    @property
    def skipped(self) -> int:
        return sum(1 for c in self.checks if c.status is Status.SKIP)

    @property
    def has_failure(self) -> bool:
        return self.failed > 0

    def _emit(self, status: Status, name: str, detail: str) -> None:
        marker = {Status.PASS: "  OK  ", Status.FAIL: " FAIL ", Status.SKIP: " SKIP "}[status]
        suffix = f" - {detail}" if detail else ""
        print(f"[{marker}] {name}{suffix}", flush=True)


@dataclass
class RunSummary:
    """전체 실행 요약"""

    results: list[ScenarioResult] = field(default_factory=list)

    def add(self, result: ScenarioResult) -> None:
        self.results.append(result)

    @property
    def passed(self) -> int:
        return sum(r.passed for r in self.results)

    @property
    def failed(self) -> int:
        return sum(r.failed for r in self.results)

    @property
    def skipped(self) -> int:
        return sum(r.skipped for r in self.results)

    @property
    def exit_code(self) -> int:
        """실패가 하나라도 있으면 1, 그 밖에는 0"""
        return 1 if self.failed else 0

    def report(self) -> None:
        """요약을 출력한다."""
        print()
        print("=" * 60)
        print("시나리오별 결과")
        print("-" * 60)
        for result in self.results:
            print(
                f"  {result.scenario:<24} "
                f"통과 {result.passed:>3}  실패 {result.failed:>3}  건너뜀 {result.skipped:>3}"
            )
        print("-" * 60)
        print(f"  합계  통과 {self.passed}  실패 {self.failed}  건너뜀 {self.skipped}")
        print("=" * 60)

        if self.failed:
            print(f"판정: 실패 ({self.failed}건)")
        elif self.passed == 0:
            print("판정: 수행된 검증이 없음")
        else:
            print("판정: 성공")
