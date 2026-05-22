"""
workflow/steps/dc_check_step.py — Block rename if target is a Domain Controller.
"""
from src.workflow.steps.base_step import BaseRenameStep, StepResult


class DCCheckStep(BaseRenameStep):
    name = "DC Role Check"

    def execute(self, op, services) -> StepResult:
        if not services.config.check_dc_role:
            return StepResult.ok()

        result = services.ad_repo.is_domain_controller(op.old_name)

        if result is None:
            services.audit.log(
                "RENAME_BLOCKED_DC_CHECK_FAILED", op.operator,
                f"computer={op.old_name}", is_error=True,
                correlation_id=op.operation_id,
            )
            return StepResult.fail("DC_CHECK_FAILED")

        if result is True:
            services.audit.log(
                "RENAME_BLOCKED_DC", op.operator,
                f"computer={op.old_name}", is_error=True,
                correlation_id=op.operation_id,
            )
            return StepResult.fail("IS_DC")

        return StepResult.ok()
