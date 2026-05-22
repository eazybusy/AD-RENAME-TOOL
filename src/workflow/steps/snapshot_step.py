"""
workflow/steps/snapshot_step.py — Capture AD DN for rollback before rename.
"""
from src.workflow.steps.base_step import BaseRenameStep, StepResult


class SnapshotADStep(BaseRenameStep):
    name = "AD Snapshot (Pre-rename)"

    def execute(self, op, services) -> StepResult:
        dn = services.ad_repo.get_distinguished_name(op.old_name)
        if not dn:
            services.audit.log(
                "SNAPSHOT_FAILED", op.operator,
                f"computer={op.old_name} — could not retrieve DN",
                is_error=True, correlation_id=op.operation_id,
            )
            return StepResult.fail("SNAPSHOT_FAILED", "Cannot retrieve AD Distinguished Name")

        op.pre_dn = dn
        services.audit.log(
            "SNAPSHOT_OK", op.operator,
            f"computer={op.old_name}, dn={dn}",
            correlation_id=op.operation_id,
        )
        return StepResult.ok()
