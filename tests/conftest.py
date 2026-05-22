"""
tests/conftest.py — Shared pytest fixtures.
"""
import pytest
from unittest.mock import MagicMock
from src.config import AppConfig


@pytest.fixture
def mock_config():
    cfg = MagicMock(spec=AppConfig)
    cfg.smb_threads = 5
    cfg.wmi_threads = 5
    cfg.socket_timeout = 0.3
    cfg.wmi_timeout = 5
    cfg.check_dc_role = True
    cfg.check_duplicate_name = True
    cfg.notify_user_before_rename = False
    cfg.notification_grace_seconds = 0
    cfg.update_spns_after_rename = True
    cfg.ad_search_base = ""
    cfg.ad_filter_inactive_days = 0
    cfg.write_event_log = False
    cfg.event_log_source = "AD-Rename-Tool"
    return cfg


@pytest.fixture
def mock_audit():
    return MagicMock()


@pytest.fixture
def mock_ad_repo():
    repo = MagicMock()
    repo.is_domain_controller.return_value = False
    repo.name_exists.return_value = False
    repo.get_distinguished_name.return_value = "CN=PC-001,OU=Workstations,DC=corp,DC=local"
    repo.rename_ad_object.return_value = True
    return repo


@pytest.fixture
def mock_ps_runner():
    runner = MagicMock()
    runner.run_rename_computer.return_value = True
    runner.run_restart_computer.return_value = True
    return runner


@pytest.fixture
def mock_services(mock_config, mock_audit, mock_ad_repo, mock_ps_runner):
    from unittest.mock import MagicMock
    svc = MagicMock()
    svc.config = mock_config
    svc.audit = mock_audit
    svc.ad_repo = mock_ad_repo
    svc.ps_runner = mock_ps_runner
    svc.notifier = MagicMock()
    svc.spn_mgr = MagicMock()
    svc.spn_mgr.update_spns.return_value = True
    return svc
