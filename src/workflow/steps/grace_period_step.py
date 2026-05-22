"""
workflow/steps/grace_period_step.py — Wait for notification grace period.
FIX: cancel_event support — 600-second block interrupted immediately on cancel.
"""
import time
from src.workflow.steps.base_step import BaseRenameStep, StepResult


class GracePeriodStep(BaseRenameStep):
    name = "Grace Period Wait"

    def execute(self, op, services) -> StepResult:
        grace = services.config.notification_grace_seconds
        if grace <= 0 or not services.config.notify_user_before_rename:
            return StepResult.ok()

        cancel = getattr(services, "cancel_event", None)

        services.audit.log(
            "GRACE_PERIOD_START", op.operator,
            f"computer={op.old_name}, waiting={grace}s",
            correlation_id=op.operation_id,
        )

        deadline = time.monotonic() + grace
        while time.monotonic() < deadline:
            if cancel and cancel.is_set():
                services.audit.log(
                    "GRACE_PERIOD_CANCELLED", op.operator,
                    f"computer={op.old_name}",
                    correlation_id=op.operation_id,
                )
                return StepResult.fail("CANCELLED", "Operation cancelled during grace period")
            remaining = deadline - time.monotonic()
            time.sleep(min(1.0, max(0.0, remaining)))

        return StepResult.ok()
