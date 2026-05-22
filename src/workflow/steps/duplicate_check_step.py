"""
workflow/steps/duplicate_check_step.py — Check new name doesn't already exist in AD.
"""
from src.workflow.steps.base_step import BaseRenameStep, StepResult


class DuplicateCheckStep(BaseRenameStep):
    name = "Duplicate Name Check"

    def execute(self, op, services) -> StepResult:
        if not services.config.check_duplicate_name:
            return StepResult.ok()

        exists = services.ad_repo.name_exists(op.new_name)

        if exists is None:
            services.audit.log(
                "RENAME_DUP_CHECK_FAILED", op.operator,
                f"new_name={op.new_name}", is_error=True,
                correlation_id=op.operation_id,
            )
            return StepResult.fail("DUP_CHECK_FAILED")

        if exists:
            services.audit.log(
                "RENAME_BLOCKED_DUPLICATE", op.operator,
                f"new_name={op.new_name} already exists in AD", is_error=True,
                correlation_id=op.operation_id,
            )
            return StepResult.fail("NAME_EXISTS", f"'{op.new_name}' already exists in AD")

        return StepResult.ok()
