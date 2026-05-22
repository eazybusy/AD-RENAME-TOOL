"""
infrastructure/notifier.py — User notification via msg.exe or WMI.
"""
import subprocess
from src.infrastructure.interfaces import IUserNotifier


class UserNotifier(IUserNotifier):
    """
    Sends popup message to logged-on user on remote computer.
    Uses msg.exe (built-in Windows) for RDP/console sessions.
    """

    def notify(self, computer: str, message: str) -> bool:
        """
        Sends a message to all sessions on the remote computer.
        Returns True if msg.exe exited cleanly.
        """
        try:
            result = subprocess.run(
                ["msg", "*", f"/server:{computer}", message],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return result.returncode == 0
        except Exception:
            return False
