"""
workflow/steps/lock_step.py — Acquire distributed rename lock.
FIX: Added release() so workflow can free lock on SUCCESS path too.
"""
import threading
from src.workflow.steps.base_step import BaseRenameStep, StepResult

_rename_lock = threading.Lock()


class LockStep(BaseRenameStep):
    name = "Acquire Rename Lock"

    def __init__(self):
        self._acquired = False

    def execute(self, op, services) -> StepResult:
        acquired = _rename_lock.acquire(blocking=False)
        if not acquired:
            return StepResult.fail(
                "LOCK_BUSY",
                "Another rename operation is already in progress. Please wait."
            )
        self._acquired = True
        return StepResult.ok()

    def release(self, op, services):
        """Called by _finalize() on the SUCCESS path to free the lock."""
        if self._acquired:
            try:
                _rename_lock.release()
                self._acquired = False
            except RuntimeError:
                pass

    def rollback(self, op, services):
        """Called on the FAILURE path — delegates to release()."""
        self.release(op, services)
