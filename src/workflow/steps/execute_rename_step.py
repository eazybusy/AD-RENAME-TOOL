"""
workflow/steps/execute_rename_step.py — Execute the actual computer rename.
"""
from src.workflow.steps.base_step import BaseRenameStep, StepResult
from src.data.audit_logger import EVT_RENAME_START, EVT_RENAME_OK, EVT_RENAME_FAIL


class ExecuteRenameStep(BaseRenameStep):
    name = "Execute Rename"

    def execute(self, op, services) -> StepResult:
        services.audit.log(
            "RENAME_START", op.operator,
            f"old={op.old_name}, new={op.new_name}",
            event_id=EVT_RENAME_START,
            correlation_id=op.operation_id,
        )

        success = services.ps_runner.run_rename_computer(op.old_name, op.new_name)

        if not success:
            services.audit.log(
                "RENAME_FAILED", op.operator,
                f"old={op.old_name}, new={op.new_name}",
                event_id=EVT_RENAME_FAIL, is_error=True,
                correlation_id=op.operation_id,
            )
            return StepResult.fail("RENAME_FAILED", "PowerShell Rename-Computer failed", rollback=True)

        services.audit.log(
            "RENAME_SUCCESS", op.operator,
            f"old={op.old_name}, new={op.new_name}",
            event_id=EVT_RENAME_OK,
            correlation_id=op.operation_id,
        )
        return StepResult.ok()

    def rollback(self, op, services):
        """
        Attempt to rename back to original name.
        FIX: use Rename-Computer (SAM + NetBIOS) FIRST, then Rename-ADObject
        (LDAP CN sync).  Previously only Rename-ADObject was called, which
        updates only the LDAP CN and leaves SAMAccountName / NetBIOS broken.
        """
        ps_ok = False
        try:
            # Step 1: NetBIOS + SAMAccountName via Rename-Computer
            ps_ok = services.ps_runner.run_rename_computer(op.new_name, op.old_name)
        except Exception as e:
            services.audit.log(
                "RENAME_ROLLBACK_PS_FAILED", op.operator,
                f"Rename-Computer rollback error: {e}", is_error=True,
                correlation_id=op.operation_id,
            )

        # Step 2: LDAP CN sync via Rename-ADObject (if we have the pre-rename DN)
        ad_ok = False
        if op.pre_dn:
            try:
                ad_ok = services.ad_repo.rename_ad_object(op.pre_dn, op.old_name)
            except Exception as e:
                services.audit.log(
                    "RENAME_ROLLBACK_AD_FAILED", op.operator,
                    f"Rename-ADObject rollback error: {e}", is_error=True,
                    correlation_id=op.operation_id,
                )

        services.audit.log(
            "RENAME_ROLLBACK_STATUS", op.operator,
            f"restored={op.old_name}, ps_rename={ps_ok}, ad_rename={ad_ok}",
            correlation_id=op.operation_id,
        )
