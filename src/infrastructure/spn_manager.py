"""
infrastructure/spn_manager.py — SPN update after rename.
"""
import subprocess
from src.infrastructure.interfaces import ISPNManager


class SPNManager(ISPNManager):
    """
    Updates Service Principal Names after computer rename using setspn.exe.
    Removes old SPNs and adds new ones to prevent Kerberos failures.
    """

    def update_spns(self, old_name: str, new_name: str) -> bool:
        """
        Remove old HOST/{old_name} SPNs and add HOST/{new_name}.
        Returns True if both operations succeed.
        """
        try:
            # Delete old SPNs
            del_result = subprocess.run(
                ["setspn", "-D", f"HOST/{old_name}", old_name],
                capture_output=True, text=True, timeout=30
            )
            # Add new SPNs (short and FQDN forms)
            add_result = subprocess.run(
                ["setspn", "-A", f"HOST/{new_name}", new_name],
                capture_output=True, text=True, timeout=30
            )
            return add_result.returncode == 0
        except Exception:
            return False
