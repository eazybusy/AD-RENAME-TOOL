"""
tests/unit/data/test_audit_logger.py — TASK 3.4: AuditLogger unit tests.
"""
import pytest
import json
import os
from src.data.audit_logger import AuditLogger


class TestAuditLogger:
    def test_log_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ADRENAME_HMAC_KEY", "")
        al = AuditLogger(log_path=str(tmp_path / "audit.log"))
        al.log("TEST_OP", "CORP\\admin", "test detail")
        assert os.path.exists(str(tmp_path / "audit.log"))

    def test_log_entry_is_valid_json(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ADRENAME_HMAC_KEY", "")
        al = AuditLogger(log_path=str(tmp_path / "audit.log"))
        al.log("TEST_OP", "CORP\\admin", "detail")
        with open(str(tmp_path / "audit.log")) as f:
            entry = json.loads(f.readline())
        assert entry["op"] == "TEST_OP"
        assert entry["operator"] == "CORP\\admin"
        assert "hmac" in entry
        assert "ts" in entry

    def test_hmac_chain_valid(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ADRENAME_HMAC_KEY", "")
        al = AuditLogger(log_path=str(tmp_path / "audit.log"))
        al.log("OP1", "user", "d1")
        al.log("OP2", "user", "d2")
        al.log("OP3", "user", "d3")
        with open(str(tmp_path / "audit.log")) as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert len(lines) == 3
        # Each entry's prev_hmac == previous entry's hmac
        for i in range(1, len(lines)):
            assert lines[i]["prev_hmac"] == lines[i - 1]["hmac"]

    def test_correlation_id_stored(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ADRENAME_HMAC_KEY", "")
        al = AuditLogger(log_path=str(tmp_path / "audit.log"))
        al.log("OP", "user", "detail", correlation_id="abc123")
        with open(str(tmp_path / "audit.log")) as f:
            entry = json.loads(f.readline())
        assert entry.get("correlation_id") == "abc123"

    def test_multiple_logs_append(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ADRENAME_HMAC_KEY", "")
        al = AuditLogger(log_path=str(tmp_path / "audit.log"))
        for i in range(5):
            al.log(f"OP_{i}", "user", f"detail_{i}")
        with open(str(tmp_path / "audit.log")) as f:
            lines = [l for l in f if l.strip()]
        assert len(lines) == 5

    def test_error_flag_stored(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ADRENAME_HMAC_KEY", "")
        al = AuditLogger(log_path=str(tmp_path / "audit.log"))
        al.log("ERR_OP", "user", "error detail", is_error=True)
        with open(str(tmp_path / "audit.log")) as f:
            entry = json.loads(f.readline())
        assert entry["is_error"] is True
