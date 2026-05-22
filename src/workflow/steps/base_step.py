"""
workflow/steps/base_step.py — Base class for all rename pipeline steps.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class StepResult:
    success: bool
    error_code: Optional[str] = None
    error_detail: Optional[str] = None
    should_rollback: bool = False

    @classmethod
    def ok(cls) -> "StepResult":
        return cls(success=True)

    @classmethod
    def fail(cls, code: str, detail: str = "", rollback: bool = False) -> "StepResult":
        return cls(success=False, error_code=code, error_detail=detail, should_rollback=rollback)


class BaseRenameStep(ABC):
    """Each rename step: single responsibility, independently testable."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def execute(self, op, services) -> StepResult: ...
