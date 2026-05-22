"""
tests/unit/integration/test_powershell_runner.py
Integration tests — require real Windows + PowerShell.
Marked as 'integration' — skipped in CI, run in AD lab.
"""
import pytest
import sys


@pytest.mark.integration
@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
class TestPSRunnerIntegration:
    def test_run_simple_command(self):
        from src.infrastructure.powershell_runner import PSRunner
        runner = PSRunner()
        result = runner.run_script("Write-Output 'OK'", {})
        assert "OK" in result.stdout

    def test_run_with_params(self):
        from src.infrastructure.powershell_runner import PSRunner
        runner = PSRunner()
        result = runner.run_script(
            "Write-Output $name",
            {"name": "TEST-VALUE"}
        )
        assert "TEST-VALUE" in result.stdout

    def test_timeout_returns_error(self):
        from src.infrastructure.powershell_runner import PSRunner
        runner = PSRunner()
        result = runner.run_script("Start-Sleep -Seconds 10", {}, timeout=1)
        assert result.returncode == -1
        assert "timeout" in result.stderr.lower()
