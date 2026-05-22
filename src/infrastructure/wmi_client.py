"""
infrastructure/wmi_client.py — WMI user session detection.
Wraps scan_engine logic in the infrastructure layer.
"""
from typing import Optional, Tuple
from src.infrastructure.interfaces import IWMIClient


class WMIClient(IWMIClient):
    """
    Concrete WMI client — delegates to scan_engine for actual WMI calls.
    Isolated here so scan_service depends on IWMIClient, not scan_engine directly.
    """

    def __init__(self, config=None):
        self._cfg = config
        self._startupinfo = _get_startupinfo()

    def get_active_users(self, computer: str) -> list:
        """Returns list of UserSession namedtuples."""
        try:
            from src.scan_engine import get_active_users
            return get_active_users(computer, self._startupinfo)
        except Exception:
            return []

    def get_active_user(self, computer: str) -> Tuple[Optional[str], Optional[str]]:
        """Returns (username, session_type) or (None, None)."""
        try:
            from src.scan_engine import get_active_user
            return get_active_user(computer, self._startupinfo)
        except Exception:
            return None, None


def _get_startupinfo():
    try:
        import subprocess
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        return si
    except Exception:
        return None
