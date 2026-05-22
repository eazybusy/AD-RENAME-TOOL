"""
workflow/steps/verify_replication_step.py — Verify rename replicated in AD.
FIX: cancel_event support — 15-second retry loop interrupted on cancel.
"""
import time
from src.workflow.steps.base_step import BaseRenameStep, StepResult


class VerifyReplicationStep(BaseRenameStep):
    name = "Verify AD Replication"

    _MAX_RETRIES = 3
    _RETRY_DELAY = 5  # seconds

    def execute(self, op, services) -> StepResult:
        cancel = getattr(services, "cancel_event", None)

        for attempt in range(self._MAX_RETRIES):
            if cancel and cancel.is_set():
                return StepResult.fail("CANCELLED", "Operation cancelled during replication check")

            exists = services.ad_repo.name_exists(op.new_name)
            if exists:
                op.ad_verified = True
                services.audit.log(
                    "AD_REPLICATION_VERIFIED", op.operator,
                    f"new_name={op.new_name}, attempt={attempt + 1}",
                    correlation_id=op.operation_id,
                )
                return StepResult.ok()

            if attempt < self._MAX_RETRIES - 1:
                # Interruptible sleep — wake up every second to check cancel
                for _ in range(self._RETRY_DELAY):
                    if cancel and cancel.is_set():
                        return StepResult.fail("CANCELLED", "Operation cancelled during replication wait")
                    time.sleep(1.0)

        # Non-fatal — rename succeeded even if we can't verify replication yet
        services.audit.log(
            "AD_REPLICATION_UNVERIFIED", op.operator,
            f"new_name={op.new_name} not yet visible (replication lag)",
            is_error=False, correlation_id=op.operation_id,
        )
        return StepResult.ok()
