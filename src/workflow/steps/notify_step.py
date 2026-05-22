"""
workflow/steps/notify_step.py — Notify logged-on user before rename.
"""
from src.workflow.steps.base_step import BaseRenameStep, StepResult


class NotifyUserStep(BaseRenameStep):
    name = "Notify User"

    def execute(self, op, services) -> StepResult:
        if not services.config.notify_user_before_rename:
            return StepResult.ok()

        grace = services.config.notification_grace_seconds
        msg = (
            f"ВНІМАНІЄ: Цей комп'ютер буде перейменований з '{op.old_name}' "
            f"на '{op.new_name}' через {grace} секунд.\n"
            f"Будь ласка, збережіть свою роботу.\n"
            f"Адміністратор: {op.operator}"
        )
        # Georgian-friendly message
        msg_ka = (
            f"გაფრთხილება: კომპიუტერი '{op.old_name}' "
            f"გადარქმევა → '{op.new_name}' {grace} წამში.\n"
            f"შეინახეთ სამუშაო. ადმინი: {op.operator}"
        )

        try:
            success = services.notifier.notify(op.old_name, msg_ka)
            services.audit.log(
                "NOTIFY_USER", op.operator,
                f"computer={op.old_name}, grace={grace}s, delivered={success}",
                correlation_id=op.operation_id,
            )
        except Exception as e:
            # Non-critical — continue even if notification fails
            services.audit.log(
                "NOTIFY_USER_FAILED", op.operator,
                f"computer={op.old_name}, error={e}",
                is_error=True, correlation_id=op.operation_id,
            )

        return StepResult.ok()
