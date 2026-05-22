"""
data/audit_logger.py — Structured JSON audit log with HMAC chain (TASK 3.1).
TASK 3.2: Correlation IDs on every operation.
Extracted and refactored from data_layer.py.
"""
import os
import json
import time
import hmac
import hashlib
import threading
import subprocess
from typing import Optional

from src.infrastructure.interfaces import IAuditLogger


def _safe_log_error(msg: str):
    try:
        import logging
        logging.getLogger(__name__).error(msg)
    except Exception:
        pass


def get_windows_identity() -> str:
    """Returns DOMAIN\\Username from the actual Windows process token."""
    try:
        import win32security
        import win32api
        token = win32security.OpenProcessToken(
            win32api.GetCurrentProcess(),
            win32security.TOKEN_QUERY,
        )
        sid = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
        name, domain, _ = win32security.LookupAccountSid(None, sid)
        return f"{domain}\\{name}"
    except ImportError:
        pass
    except Exception:
        pass

    try:
        r = subprocess.run(["whoami"], capture_output=True, text=True, timeout=3)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip().upper()
    except Exception:
        pass

    return f"(env){os.environ.get('USERNAME', 'unknown')}"


def _get_hmac_key() -> bytes:
    """
    Returns a 32-byte HMAC key.
    Priority: 1. GPO env var  2. key file (persisted)  3. Generate + persist
    FIX: os.urandom fallback replaced with file-persisted key so the HMAC
    chain is not broken on every restart (audit integrity).
    """
    import stat
    import base64
    from src.config import get_config
    cfg = get_config()

    # Priority 1: GPO / environment variable
    b64 = os.environ.get(cfg.hmac_key_env, "").strip()
    if b64:
        try:
            key = base64.b64decode(b64)
            if len(key) >= 16:
                return key
        except Exception:
            _safe_log_error("HMAC key: env var base64 decode failed — falling back")

    # Priority 2 & 3: file-persisted key
    key_path = os.path.join(cfg.data_dir(), ".hmac_key")
    try:
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                key = f.read()
            if len(key) >= 16:
                return key
    except Exception as e:
        _safe_log_error(f"HMAC key: failed to read key file ({e}) — regenerating")

    # Generate new key and persist it
    key = os.urandom(32)
    try:
        with open(key_path, "wb") as f:
            f.write(key)
        # Owner read/write only — no group/other access
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception as e:
        _safe_log_error(f"HMAC key: failed to persist key file ({e}) — session key only")

    return key


# Event IDs for SIEM correlation
EVT_SCAN_START   = 1000
EVT_SCAN_DONE    = 1001
EVT_RENAME_START = 1010
EVT_RENAME_OK    = 1011
EVT_RENAME_FAIL  = 1012
EVT_BLOCKED_DC   = 1013
EVT_BLOCKED_DUP  = 1014
EVT_SPN_UPDATE   = 1015
EVT_NOTIFY_USER  = 1016


class AuditLogger(IAuditLogger):
    """
    TASK 3.1: Structured JSON audit log with HMAC-SHA256 chain.
    Each entry: {ts, op, operator, details, event_id, hmac, prev_hmac}
    Chain: each entry's prev_hmac = previous entry's hmac → tampering detection.
    """

    def __init__(self, log_path: Optional[str] = None, config=None):
        if log_path:
            self._path = log_path
        else:
            from src.config import get_config
            cfg = config or get_config()
            self._path = cfg.audit_log_path()

        self._lock = threading.Lock()
        self._key = _get_hmac_key()
        self._prev_hmac = self._read_last_hmac()

        # Config for Windows Event Log
        self._cfg = config
        if config is None:
            try:
                from src.config import get_config
                self._cfg = get_config()
            except Exception:
                self._cfg = None

    def _read_last_hmac(self) -> str:
        """Read the last HMAC from existing log for chain continuity."""
        try:
            if not os.path.exists(self._path):
                return "0" * 64
            with open(self._path, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]
            if lines:
                last = json.loads(lines[-1])
                return last.get("hmac", "0" * 64)
        except Exception:
            pass
        return "0" * 64

    def _compute_hmac(self, payload: str) -> str:
        return hmac.new(self._key, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def log(self, operation: str, operator: str, details: str,
            event_id: int = None, is_error: bool = False,
            correlation_id: Optional[str] = None) -> None:
        """
        Write a structured JSON audit entry with HMAC chain.
        TASK 3.2: correlation_id threads through all steps of one operation.
        """
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        entry = {
            "ts":         now,
            "op":         operation,
            "operator":   operator,
            "details":    details,
            "event_id":   event_id,
            "is_error":   is_error,
            "prev_hmac":  self._prev_hmac,
        }
        if correlation_id:
            entry["correlation_id"] = correlation_id

        payload = json.dumps(entry, ensure_ascii=False, sort_keys=True)
        entry["hmac"] = self._compute_hmac(payload)
        line = json.dumps(entry, ensure_ascii=False)

        with self._lock:
            try:
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
                self._prev_hmac = entry["hmac"]
            except OSError as e:
                _safe_log_error(f"AuditLogger FAILED: {e}")

        # Windows Event Log (secondary)
        if self._cfg and getattr(self._cfg, "write_event_log", False) and event_id:
            self._write_event_log(event_id, f"{operation}: {details}", is_error)

    def _write_event_log(self, event_id: int, message: str, is_error: bool):
        try:
            import win32evtlogutil
            import win32evtlog
            source = getattr(self._cfg, "event_log_source", "AD-Rename-Tool")
            etype = win32evtlog.EVENTLOG_ERROR_TYPE if is_error else win32evtlog.EVENTLOG_INFORMATION_TYPE
            win32evtlogutil.ReportEvent(
                appName=source,
                eventID=event_id,
                eventCategory=0,
                eventType=etype,
                strings=[message],
            )
        except Exception:
            pass
