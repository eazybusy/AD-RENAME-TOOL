"""
workflow/rename_workflow.py — 10-step rename pipeline (TASK 2.3).
Each step is independently testable and replaceable.
"""
import logging
from typing import Callable, Optional

from src.domain.rename_operation import RenameOperation, RenameStatus
from src.workflow.steps.base_step import BaseRenameStep, StepResult
from src.workflow.steps.lock_step import LockStep
from src.workflow.steps.dc_check_step import DCCheckStep
from src.workflow.steps.duplicate_check_step import DuplicateCheckStep
from src.workflow.steps.notify_step import NotifyUserStep
from src.workflow.steps.grace_period_step import GracePeriodStep
from src.workflow.steps.snapshot_step import SnapshotADStep
from src.workflow.steps.execute_rename_step import ExecuteRenameStep
from src.workflow.steps.verify_replication_step import VerifyReplicationStep
from src.workflow.steps.update_spn_step import UpdateSPNStep
from src.workflow.steps.register_dns_step import RegisterDNSStep

logger = logging.getLogger(__name__)


class RenameWorkflow:
    """
    Orchestrates the 10-step rename pipeline.
    Dependency-injected services → fully testable.
    TASK 3.2: All log entries include correlation_id = op.operation_id.
    """

    def __init__(self, services, config, log_callback: Optional[Callable] = None):
        self._svc = services
        self._cfg = config
        self._log = log_callback or (lambda msg: logger.info(msg))

        self._steps: list[BaseRenameStep] = [
            LockStep(),
            DCCheckStep(),
            DuplicateCheckStep(),
            NotifyUserStep(),
            GracePeriodStep(),
            SnapshotADStep(),
            ExecuteRenameStep(),
            VerifyReplicationStep(),
            UpdateSPNStep(),
            RegisterDNSStep(),
        ]

    def execute(self, op: RenameOperation) -> RenameOperation:
        op.mark_started()
        completed_steps: list[BaseRenameStep] = []

        for step in self._steps:
            # TASK 3.2: correlation ID in every log line
            self._log(f"[OP:{op.operation_id}] Step: {step.name}")
            try:
                result: StepResult = step.execute(op, self._svc)
            except Exception as e:
                result = StepResult.fail(
                    "STEP_EXCEPTION",
                    f"{step.name}: {e}",
                    rollback=True,
                )

            if not result.success:
                op.mark_failed(result.error_code, result.error_detail)
                self._log(
                    f"[OP:{op.operation_id}] FAILED at '{step.name}' — "
                    f"{result.error_code}: {result.error_detail}"
                )
                if result.should_rollback:
                    self._attempt_rollback(op, completed_steps)
                return op

            completed_steps.append(step)

        op.mark_success()
        self._log(
            f"[OP:{op.operation_id}] SUCCESS: {op.old_name} → {op.new_name} "
            f"({op.duration_ms}ms)"
        )
        # FIX: release locks / resources on success path (previously leaked)
        self._finalize(completed_steps, op)
        return op

    def _finalize(self, completed: list[BaseRenameStep], op: RenameOperation):
        """Release resources (locks, etc.) after a successful workflow run."""
        for step in reversed(completed):
            if hasattr(step, "release"):
                try:
                    step.release(op, self._svc)
                except Exception as e:
                    self._log(f"[OP:{op.operation_id}] Finalize error in '{step.name}': {e}")

    def _attempt_rollback(self, op: RenameOperation, completed: list[BaseRenameStep]):
        op.rollback_attempted = True
        self._log(f"[OP:{op.operation_id}] Starting rollback...")
        for step in reversed(completed):
            if hasattr(step, "rollback"):
                try:
                    step.rollback(op, self._svc)
                except Exception as e:
                    self._log(f"[OP:{op.operation_id}] Rollback failed in '{step.name}': {e}")
        op.rollback_ok = (op.status != RenameStatus.FAILED)
