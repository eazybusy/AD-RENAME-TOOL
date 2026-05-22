"""
tests/unit/application/test_rename_service.py
"""
import pytest
from unittest.mock import MagicMock, patch
from src.application.rename_service import RenameService, ServiceContainer
from src.domain.rename_operation import RenameStatus


def _make_service(mock_config, mock_ad_repo, mock_ps_runner, mock_audit):
    svc_container = ServiceContainer(
        ad_repo=mock_ad_repo,
        ps_runner=mock_ps_runner,
        wmi=MagicMock(),
        notifier=MagicMock(),
        spn_mgr=MagicMock(),
        audit=mock_audit,
        config=mock_config,
    )
    svc_container.spn_mgr.update_spns.return_value = True
    return RenameService(svc_container, mock_config)


class TestRenameServiceValidation:
    def test_valid_name_passes(self, mock_config, mock_audit, mock_ad_repo, mock_ps_runner):
        svc = _make_service(mock_config, mock_ad_repo, mock_ps_runner, mock_audit)
        ok, msg = svc.validate("PC-001")
        assert ok

    def test_too_long_name_fails(self, mock_config, mock_audit, mock_ad_repo, mock_ps_runner):
        svc = _make_service(mock_config, mock_ad_repo, mock_ps_runner, mock_audit)
        ok, msg = svc.validate("A" * 16)
        assert not ok

    def test_reserved_name_fails(self, mock_config, mock_audit, mock_ad_repo, mock_ps_runner):
        svc = _make_service(mock_config, mock_ad_repo, mock_ps_runner, mock_audit)
        ok, msg = svc.validate("CON")
        assert not ok


class TestRenameServiceWorkflow:
    def test_successful_rename(self, mock_config, mock_audit, mock_ad_repo, mock_ps_runner):
        mock_config.notify_user_before_rename = False
        mock_config.notification_grace_seconds = 0
        mock_ad_repo.is_domain_controller.return_value = False
        mock_ad_repo.name_exists.return_value = False
        mock_ad_repo.get_distinguished_name.return_value = "CN=PC-001,DC=corp,DC=local"
        mock_ps_runner.run_rename_computer.return_value = True
        mock_ad_repo.name_exists.side_effect = [False, True]  # dup check=False, verify=True

        svc = _make_service(mock_config, mock_ad_repo, mock_ps_runner, mock_audit)
        done_ops = []
        t = svc.rename_async("PC-001", "PC-002", "CORP\\admin",
                             on_complete=done_ops.append)
        t.join(timeout=10)

        assert done_ops
        assert done_ops[0].status == RenameStatus.SUCCESS

    def test_blocked_by_validation(self, mock_config, mock_audit, mock_ad_repo, mock_ps_runner):
        svc = _make_service(mock_config, mock_ad_repo, mock_ps_runner, mock_audit)
        done_ops = []
        t = svc.rename_async("PC-001", "A" * 16, "admin", on_complete=done_ops.append)
        t.join(timeout=5)
        assert done_ops[0].status == RenameStatus.FAILED
        assert done_ops[0].error_code == "VALIDATION_ERROR"
