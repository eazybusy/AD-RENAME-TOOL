"""
config.py — Centralized Configuration Management (refactored)
Phase 1 additions:
  - LDAP DN validation (TASK 1.4 — injection hardening)
  - ad_search_base property validates DN format before use in PowerShell
"""

import os
import re
import configparser

from src.shared.ldap_utils import validate_ldap_dn  # FIX: single source of truth

_DEFAULTS = {
    "scan": {
        "smb_threads":             "10",
        "wmi_threads":             "10",
        "socket_timeout":          "0.30",
        "wmi_timeout":             "5",
        "watch_interval":          "60",
        "ad_search_base":          "",
        "ad_filter_inactive_days": "90",
    },
    "security": {
        "require_confirmation":         "true",
        "notify_user_before_rename":    "true",
        "notification_grace_seconds":   "60",
        "check_dc_role":                "true",
        "check_duplicate_name":         "true",
        "update_spns_after_rename":     "true",
        "warn_on_reboot_skip":          "true",
    },
    "audit": {
        "write_event_log":          "true",
        "event_log_source":         "AD-Rename-Tool",
        "hmac_key_env":             "ADRENAME_HMAC_KEY",
        "audit_log_retention_days": "365",
        "scan_retention_days":      "90",
        "anonymize_after_days":     "180",
    },
    "paths": {
        "data_dir":     "",
        "audit_log":    "audit.log",
        "cache_file":   "scan_cache.json",
        "scans_folder": "scans",
    },
}



def _app_dir() -> str:
    import sys
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _settings_path() -> str:
    return os.path.join(_app_dir(), "settings.ini")


class AppConfig:
    """Singleton-style config. Reads settings.ini; falls back to _DEFAULTS."""

    def __init__(self):
        self._cfg = configparser.ConfigParser()
        self._cfg.read_dict(_DEFAULTS)
        path = _settings_path()
        if os.path.exists(path):
            self._cfg.read(path, encoding="utf-8")

    def get(self, section: str, key: str) -> str:
        return self._cfg.get(section, key)

    def getint(self, section: str, key: str) -> int:
        return self._cfg.getint(section, key)

    def getfloat(self, section: str, key: str) -> float:
        return self._cfg.getfloat(section, key)

    def getbool(self, section: str, key: str) -> bool:
        return self._cfg.getboolean(section, key)

    # ── scan ─────────────────────────────────────────
    @property
    def smb_threads(self) -> int:
        return max(1, min(50, self.getint("scan", "smb_threads")))
    @property
    def wmi_threads(self) -> int:
        return max(1, min(50, self.getint("scan", "wmi_threads")))
    @property
    def socket_timeout(self) -> float:
        return max(0.05, min(5.0, self.getfloat("scan", "socket_timeout")))
    @property
    def wmi_timeout(self) -> int:
        return max(2, min(60, self.getint("scan", "wmi_timeout")))
    @property
    def watch_interval(self) -> int:
        return max(10, min(3600, self.getint("scan", "watch_interval")))

    @property
    def ad_search_base(self) -> str:
        """FIX: Validates LDAP DN format via shared/ldap_utils (single source of truth)."""
        val = self.get("scan", "ad_search_base").strip()
        try:
            return validate_ldap_dn(val)
        except ValueError:
            raise ValueError(
                f"settings.ini [scan] ad_search_base='{val}' "
                f"is not a valid LDAP Distinguished Name. "
                f"Example: OU=Workstations,DC=corp,DC=local"
            )

    @property
    def ad_filter_inactive_days(self) -> int:
        return max(0, min(3650, self.getint("scan", "ad_filter_inactive_days")))

    # ── security ─────────────────────────────────────
    @property
    def require_confirmation(self) -> bool:
        return self.getbool("security", "require_confirmation")
    @property
    def notify_user_before_rename(self) -> bool:
        return self.getbool("security", "notify_user_before_rename")
    @property
    def notification_grace_seconds(self) -> int:
        return max(0, min(600, self.getint("security", "notification_grace_seconds")))
    @property
    def check_dc_role(self) -> bool:
        return self.getbool("security", "check_dc_role")
    @property
    def check_duplicate_name(self) -> bool:
        return self.getbool("security", "check_duplicate_name")
    @property
    def update_spns_after_rename(self) -> bool:
        return self.getbool("security", "update_spns_after_rename")
    @property
    def warn_on_reboot_skip(self) -> bool:
        return self.getbool("security", "warn_on_reboot_skip")

    # ── audit ────────────────────────────────────────
    @property
    def write_event_log(self) -> bool:
        return self.getbool("audit", "write_event_log")
    @property
    def event_log_source(self) -> str:
        return self.get("audit", "event_log_source")
    @property
    def hmac_key_env(self) -> str:
        return self.get("audit", "hmac_key_env")
    @property
    def audit_log_retention_days(self) -> int:
        return max(0, min(3650, self.getint("audit", "audit_log_retention_days")))
    @property
    def scan_retention_days(self) -> int:
        return max(0, min(3650, self.getint("audit", "scan_retention_days")))
    @property
    def anonymize_after_days(self) -> int:
        return max(0, min(3650, self.getint("audit", "anonymize_after_days")))

    # ── paths ────────────────────────────────────────
    def data_dir(self) -> str:
        override = self.get("paths", "data_dir").strip()
        base = override if override else _app_dir()
        path = os.path.join(base, "data")
        os.makedirs(path, exist_ok=True)
        return path

    def audit_log_path(self) -> str:
        return os.path.join(self.data_dir(), self.get("paths", "audit_log"))

    def cache_path(self) -> str:
        return os.path.join(self.data_dir(), self.get("paths", "cache_file"))

    def scans_dir(self) -> str:
        path = os.path.join(self.data_dir(), self.get("paths", "scans_folder"))
        os.makedirs(path, exist_ok=True)
        return path


_instance: AppConfig | None = None
_instance_lock = __import__("threading").Lock()


def get_config() -> AppConfig:
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = AppConfig()
    return _instance
