"""
workflow/steps/register_dns_step.py — Trigger DNS re-registration on renamed host.
"""
from src.workflow.steps.base_step import BaseRenameStep, StepResult


class RegisterDNSStep(BaseRenameStep):
    name = "Register DNS"

    def execute(self, op, services) -> StepResult:
        """Run ipconfig /registerdns on the renamed computer."""
        script = f"Invoke-Command -ComputerName '{op.new_name}' -ScriptBlock {{ ipconfig /registerdns }} -ErrorAction SilentlyContinue; 'OK'"
        try:
            result = services.ps_runner.run_script(script, {}, timeout=30)
            stdout = getattr(result, "stdout", result) if not isinstance(result, str) else result
            op.dns_triggered = "OK" in stdout

            services.audit.log(
                "DNS_REGISTRATION", op.operator,
                f"computer={op.new_name}, triggered={op.dns_triggered}",
                correlation_id=op.operation_id,
            )
        except Exception as e:
            services.audit.log(
                "DNS_REGISTRATION_FAILED", op.operator,
                f"computer={op.new_name}, error={e}",
                is_error=True, correlation_id=op.operation_id,
            )

        return StepResult.ok()  # Non-fatal
