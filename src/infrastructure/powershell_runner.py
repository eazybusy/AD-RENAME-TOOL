"""
infrastructure/powershell_runner.py — PowerShell execution wrapper.
"""
import subprocess
import os
from dataclasses import dataclass
from typing import Optional

from src.infrastructure.interfaces import IPSRunner


@dataclass
class PSResult:
    stdout: str
    stderr: str
    returncode: int

    @property
    def success(self) -> bool:
        return self.returncode == 0


def _get_startupinfo():
    """Hide PowerShell console window."""
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        return si
    except AttributeError:
        return None  # Non-Windows


class PSRunner(IPSRunner):
    """Runs PowerShell scripts with parameter injection (no string interpolation)."""

    def run_script(self, script: str, params: dict, timeout: int = 30) -> PSResult:
        """
        Execute a PowerShell script string.
        params: dict of PS variable names to values (injected safely).
        """
        # Build parameter setup block
        param_block = ""
        for k, v in params.items():
            # Escape single quotes in values
            safe_v = str(v).replace("'", "''")
            param_block += f"${k} = '{safe_v}'; "

        full_script = param_block + script

        cmd = [
            "powershell.exe",
            "-NonInteractive",
            "-NoProfile",
            "-WindowStyle", "Hidden",
            "-Command", full_script,
        ]

        try:
            r = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                startupinfo=_get_startupinfo(),
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            return PSResult(
                stdout=r.stdout.strip(),
                stderr=r.stderr.strip(),
                returncode=r.returncode,
            )
        except subprocess.TimeoutExpired:
            return PSResult(stdout="", stderr="PowerShell timeout", returncode=-1)
        except Exception as e:
            return PSResult(stdout="", stderr=str(e), returncode=-2)

    def run_rename_computer(self, old_name: str, new_name: str) -> bool:
        """
        Rename a remote computer via PowerShell Rename-Computer.
        FIX: names passed as PS variables — no f-string interpolation (injection hardening).
        """
        script = (
            "Rename-Computer -ComputerName $OldName "
            "-NewName $NewName -Force -ErrorAction Stop; 'OK'"
        )
        result = self.run_script(script, {"OldName": old_name, "NewName": new_name}, timeout=60)
        return result.success and "OK" in result.stdout

    def run_restart_computer(self, name: str) -> bool:
        """
        Schedule a restart of the remote computer.
        FIX: name passed as PS variable — no f-string interpolation (injection hardening).
        """
        script = "Restart-Computer -ComputerName $ComputerName -Force -ErrorAction Stop; 'OK'"
        result = self.run_script(script, {"ComputerName": name}, timeout=30)
        return result.success
