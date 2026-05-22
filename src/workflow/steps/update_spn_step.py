"""
workflow/steps/update_spn_step.py — Update Service Principal Names after rename.
"""
from src.workflow.steps.base_step import BaseRenameStep, StepResult
from src.data.audit_logger import EVT_SPN_UPDATE


class UpdateSPNStep(BaseRenameStep):
    name = "Update SPNs"

    def execute(self, op, services) -> StepResult:
        if not services.config.update_spns_after_rename:
            return StepResult.ok()

        success = services.spn_mgr.update_spns(op.old_name, op.new_name)
        op.spn_updated = success

        services.audit.log(
            "SPN_UPDATE", op.operator,
            f"old={op.old_name}, new={op.new_name}, success={success}",
            event_id=EVT_SPN_UPDATE,
            is_error=not success,
            correlation_id=op.operation_id,
        )

        # Non-fatal — SPN failure is recoverable manually
        return StepResult.ok()
