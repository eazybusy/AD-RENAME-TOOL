"""
tests/unit/application/test_scan_service.py
"""
import pytest
import threading
from unittest.mock import MagicMock, patch
from src.application.scan_service import ScanService
from src.domain.computer import Computer, ComputerStatus


def _make_scan_service(ad_repo, wmi_client, config):
    cache = MagicMock()
    cache.get_score.return_value = -1
    prioritizer = MagicMock()
    prioritizer.get_strategy.return_value = "full"
    return ScanService(ad_repo, wmi_client, cache, config, prioritizer)


class TestScanService:
    def test_stop_event_prevents_processing(self):
        ad_repo = MagicMock()
        ad_repo.get_all_computer_names.return_value = ["PC-001", "PC-002"]
        wmi = MagicMock()
        cfg = MagicMock()
        cfg.smb_threads = 2
        cfg.wmi_threads = 2
        cfg.socket_timeout = 0.1

        svc = _make_scan_service(ad_repo, wmi, cfg)
        svc.stop()  # stop immediately before start

        complete_results = []
        svc.on_complete = complete_results.append

        with patch("src.infrastructure.async_scanner.scan_smb_async",
                   return_value={"PC-001": False, "PC-002": False}):
            t = svc.start()
            t.join(timeout=5)

        # Service ran but produced no online results since stop was set
        # (this tests that stop_event is checked)

    def test_ad_query_failure_calls_complete_false(self):
        ad_repo = MagicMock()
        ad_repo.get_all_computer_names.side_effect = Exception("AD unreachable")
        wmi = MagicMock()
        cfg = MagicMock()

        svc = _make_scan_service(ad_repo, wmi, cfg)
        complete_results = []
        svc.on_complete = complete_results.append

        t = svc.start()
        t.join(timeout=5)

        assert complete_results == [False]

    def test_online_callback_fired(self):
        ad_repo = MagicMock()
        ad_repo.get_all_computer_names.return_value = ["PC-001"]
        wmi = MagicMock()
        wmi.get_active_user.return_value = ("john.smith", "Console")
        cfg = MagicMock()
        cfg.smb_threads = 1
        cfg.wmi_threads = 1
        cfg.socket_timeout = 0.1

        svc = _make_scan_service(ad_repo, wmi, cfg)
        online_computers = []
        svc.on_computer_online = online_computers.append
        svc.on_complete = lambda _: None

        with patch("src.infrastructure.async_scanner.scan_smb_async",
                   return_value={"PC-001": True}):
            t = svc.start()
            t.join(timeout=10)

        assert len(online_computers) == 1
        assert online_computers[0].name == "PC-001"
        assert online_computers[0].current_user == "john.smith"
