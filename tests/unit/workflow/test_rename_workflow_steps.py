"""
tests/unit/workflow/test_rename_workflow_steps.py — TASK 2.6: Step unit tests.
"""
import pytest
from unittest.mock import MagicMock
from src.domain.rename_operation import RenameOperation
from src.workflow.steps.dc_check_step import DCCheckStep
from src.workflow.steps.duplicate_check_step import DuplicateCheckStep
from src.workflow.steps.snapshot_step import SnapshotADStep
from src.workflow.steps.execute_rename_step import ExecuteRenameStep
from src.workflow.steps.lock_step import LockStep


def _make_op():
    return RenameOperation(old_name="PC-001", new_name="PC-002", operator="CORP\\admin")


def _make_services(mock_config=None):
    svc = MagicMock()
    cfg = mock_config or MagicMock()
    cfg.check_dc_role = True
    cfg.check_duplicate_name = True
    cfg.notify_user_before_rename = False
    cfg.update_spns_after_rename = True
    svc.config = cfg
    svc.audit = MagicMock()
    svc.ad_repo = MagicMock()
    svc.ps_runner = MagicMock()
    return svc


class TestDCCheckStep:
    def test_passes_when_not_dc(self):
        step = DCCheckStep()
        svc = _make_services()
        svc.ad_repo.is_domain_controller.return_value = False
        result = step.execute(_make_op(), svc)
        assert result.success

    def test_fails_when_is_dc(self):
        step = DCCheckStep()
        svc = _make_services()
        svc.ad_repo.is_domain_controller.return_value = True
        result = step.execute(_make_op(), svc)
        assert not result.success
        assert result.error_code == "IS_DC"

    def test_fails_when_check_errors(self):
        step = DCCheckStep()
        svc = _make_services()
        svc.ad_repo.is_domain_controller.return_value = None
        result = step.execute(_make_op(), svc)
        assert not result.success
        assert result.error_code == "DC_CHECK_FAILED"

    def test_skipped_when_config_disabled(self):
        step = DCCheckStep()
        svc = _make_services()
        svc.config.check_dc_role = False
        result = step.execute(_make_op(), svc)
        assert result.success
        svc.ad_repo.is_domain_controller.assert_not_called()


class TestDuplicateCheckStep:
    def test_passes_when_name_free(self):
        step = DuplicateCheckStep()
        svc = _make_services()
        svc.ad_repo.name_exists.return_value = False
        result = step.execute(_make_op(), svc)
        assert result.success

    def test_fails_when_name_exists(self):
        step = DuplicateCheckStep()
        svc = _make_services()
        svc.ad_repo.name_exists.return_value = True
        result = step.execute(_make_op(), svc)
        assert not result.success
        assert result.error_code == "NAME_EXISTS"

    def test_skipped_when_config_disabled(self):
        step = DuplicateCheckStep()
        svc = _make_services()
        svc.config.check_duplicate_name = False
        result = step.execute(_make_op(), svc)
        assert result.success
        svc.ad_repo.name_exists.assert_not_called()


class TestSnapshotStep:
    def test_captures_dn(self):
        step = SnapshotADStep()
        svc = _make_services()
        svc.ad_repo.get_distinguished_name.return_value = "CN=PC-001,DC=corp,DC=local"
        op = _make_op()
        result = step.execute(op, svc)
        assert result.success
        assert op.pre_dn == "CN=PC-001,DC=corp,DC=local"

    def test_fails_when_dn_not_found(self):
        step = SnapshotADStep()
        svc = _make_services()
        svc.ad_repo.get_distinguished_name.return_value = None
        result = step.execute(_make_op(), svc)
        assert not result.success
        assert result.error_code == "SNAPSHOT_FAILED"


class TestExecuteRenameStep:
    def test_success(self):
        step = ExecuteRenameStep()
        svc = _make_services()
        svc.ps_runner.run_rename_computer.return_value = True
        op = _make_op()
        op.mark_started()
        result = step.execute(op, svc)
        assert result.success

    def test_fail_triggers_rollback(self):
        step = ExecuteRenameStep()
        svc = _make_services()
        svc.ps_runner.run_rename_computer.return_value = False
        result = step.execute(_make_op(), svc)
        assert not result.success
        assert result.should_rollback

    def test_rollback_calls_ad_repo(self):
        step = ExecuteRenameStep()
        svc = _make_services()
        op = _make_op()
        op.pre_dn = "CN=PC-001,DC=corp,DC=local"
        step.rollback(op, svc)
        svc.ad_repo.rename_ad_object.assert_called_once_with(op.pre_dn, op.old_name)


class TestLockStep:
    def test_first_acquire_succeeds(self):
        import src.workflow.steps.lock_step as ls
        # Reset the module-level lock
        import threading
        ls._rename_lock = threading.Lock()
        step = LockStep()
        result = step.execute(_make_op(), MagicMock())
        assert result.success
        # cleanup
        step.rollback(_make_op(), MagicMock())

    def test_second_acquire_fails(self):
        import src.workflow.steps.lock_step as ls
        import threading
        ls._rename_lock = threading.Lock()

        step1 = LockStep()
        step2 = LockStep()
        step1.execute(_make_op(), MagicMock())

        result = step2.execute(_make_op(), MagicMock())
        assert not result.success
        assert result.error_code == "LOCK_BUSY"
        # cleanup
        step1.rollback(_make_op(), MagicMock())
