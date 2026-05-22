"""
application/rename_service.py — Rename orchestration service.
Validates input, creates RenameOperation, runs workflow.
"""
import threading
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from src.domain.computer import Computer
from src.domain.rename_operation import RenameOperation, RenameStatus
from src.domain.validation import validate_hostname
from src.infrastructure.interfaces import (
    IADRepository, IPSRunner, IWMIClient,
    IUserNotifier, ISPNManager, IAuditLogger,
)
from src.config import AppConfig
from src.workflow.rename_workflow import RenameWorkflow

logger = logging.getLogger(__name__)


@dataclass
class ServiceContainer:
    """
    Dependency container passed to all workflow steps.
    FIX: object annotations replaced with typed interfaces — enables mypy,
    IDE autocompletion, and type-safe mocking in tests.
    cancel_event added so steps can honour cancellation requests.
    """
    ad_repo:      IADRepository
    ps_runner:    IPSRunner
    wmi:          IWMIClient
    notifier:     IUserNotifier
    spn_mgr:      ISPNManager
    audit:        IAuditLogger
    config:       AppConfig
    cancel_event: Optional[threading.Event] = field(default=None)


class RenameService:
    """
    High-level rename API consumed by the UI.
    Runs the rename workflow in a background thread.
    """

    def __init__(self, services: ServiceContainer, config,
                 log_callback: Optional[Callable] = None):
        self._svc = services
        self._cfg = config
        self._log_cb = log_callback
        self._lock = threading.Lock()

    def validate(self, new_name: str) -> tuple[bool, str]:
        """Pre-validate new hostname before starting workflow."""
        return validate_hostname(new_name)

    def rename_async(
        self,
        old_name: str,
        new_name: str,
        operator: str,
        on_complete: Optional[Callable] = None,
        on_log: Optional[Callable] = None,
    ) -> threading.Thread:
        """
        Start rename in a background thread.
        on_complete(RenameOperation) — called when finished (success or fail).
        """
        def _run():
            op = self._do_rename(old_name, new_name, operator, on_log)
            if on_complete:
                on_complete(op)

        t = threading.Thread(target=_run, daemon=True, name=f"Rename-{old_name}")
        t.start()
        return t

    def _do_rename(
        self,
        old_name: str,
        new_name: str,
        operator: str,
        on_log: Optional[Callable] = None,
    ) -> RenameOperation:
        # Validate
        ok, err = validate_hostname(new_name)
        if not ok:
            op = RenameOperation(old_name=old_name, new_name=new_name, operator=operator)
            op.mark_failed("VALIDATION_ERROR", err)
            return op

        op = RenameOperation(old_name=old_name, new_name=new_name, operator=operator)
        log_cb = on_log or self._log_cb

        workflow = RenameWorkflow(self._svc, self._cfg, log_cb)
        return workflow.execute(op)

    def rollback(self, original_name: str, current_name: str,
                 operator: str = "ROLLBACK") -> RenameOperation:
        """Rollback: rename current_name → original_name."""
        return self._do_rename(current_name, original_name, operator)
