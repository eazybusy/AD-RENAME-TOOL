"""
infrastructure/ad_repository.py — AD operations via PowerShell.
TASK 1.1: LDAP Pagination fix — ResultPageSize 500.
"""
import re
import logging
from typing import Optional

from src.infrastructure.interfaces import IADRepository
from src.shared.ldap_utils import validate_ldap_dn  # FIX: single source of truth

logger = logging.getLogger(__name__)


class ADRepository(IADRepository):

    def __init__(self, config):
        self._cfg = config
        self._runner = None

    def _get_runner(self):
        if self._runner is None:
            from src.infrastructure.powershell_runner import PSRunner
            self._runner = PSRunner()
        return self._runner

    def get_all_computer_names(self) -> list[str]:
        """
        TASK 1.1: -ResultPageSize 500 ensures pagination for 1,001+ objects.

        FIX: Get-ADComputer -Filter does NOT support ScriptBlock with $_ pipeline
        variable. Replaced with -Filter * and Where-Object in the pipeline.
        LastLogonDate must be explicitly requested in -Properties for filtering.
        """
        try:
            search_base = validate_ldap_dn(self._cfg.ad_search_base)
        except ValueError as e:
            logger.error(f"SearchBase validation error: {e}")
            raise

        inactive_days = self._cfg.ad_filter_inactive_days

        # FIX: use -Filter * + Where-Object instead of broken -Filter $sb ScriptBlock
        if inactive_days > 0:
            ps_prefix = f"$cutoff = (Get-Date).AddDays(-{inactive_days}); "
            ps_where = (
                "| Where-Object { $_.LastLogonDate -ge $cutoff "
                "-or $_.LastLogonDate -eq $null } "
            )
        else:
            ps_prefix = ""
            ps_where = ""

        ps_query = (
            ps_prefix
            + "Get-ADComputer -Filter * "
            + "-ResultPageSize 500 "
            + "-Properties Name,LastLogonDate "   # LastLogonDate needed for Where-Object
            + (f"-SearchBase '{search_base}' -SearchScope Subtree " if search_base else "")
            + ps_where
            + "| Select-Object -ExpandProperty Name"
        )

        runner = self._get_runner()
        result = runner.run_script(ps_query, {}, timeout=120)

        logger.info(f"AD query returncode: {result.returncode}")
        if result.stderr:
            logger.error(f"AD query stderr: {result.stderr}")
        if result.stdout:
            logger.info(f"AD query stdout (first 500): {result.stdout[:500]}")
        else:
            logger.warning("AD query stdout: EMPTY")

        if result.returncode != 0:
            raise RuntimeError(
                f"Get-ADComputer failed (exit {result.returncode}):\n{result.stderr}"
            )

        names = [n.strip() for n in result.stdout.splitlines() if n.strip()]
        logger.info(f"Parsed {len(names)} computer names from AD")
        return names

    def is_domain_controller(self, name: str) -> Optional[bool]:
        # FIX: name passed as PS variable — no f-string interpolation
        script = (
            "$c = Get-ADComputer $Name -Properties PrimaryGroupID -ErrorAction SilentlyContinue; "
            "if ($c) { $c.PrimaryGroupID -eq 516 -or $c.PrimaryGroupID -eq 521 } else { 'ERROR' }"
        )
        try:
            result = self._get_runner().run_script(script, {"Name": name})
            out = result.stdout.strip().lower()
            if out == "true":  return True
            if out == "false": return False
            return None
        except Exception:
            return None

    def name_exists(self, name: str) -> Optional[bool]:
        # FIX: name passed as PS variable — no f-string interpolation
        script = (
            "$c = Get-ADComputer -Filter {Name -eq $Name} -ErrorAction SilentlyContinue; "
            "if ($c) { 'EXISTS' } else { 'NOT_EXISTS' }"
        )
        try:
            result = self._get_runner().run_script(script, {"Name": name})
            out = result.stdout.strip()
            if out == "EXISTS":     return True
            if out == "NOT_EXISTS": return False
            return None
        except Exception:
            return None

    def get_distinguished_name(self, name: str) -> Optional[str]:
        # FIX: name passed as PS variable — no f-string interpolation
        script = "(Get-ADComputer $Name -ErrorAction SilentlyContinue).DistinguishedName"
        try:
            result = self._get_runner().run_script(script, {"Name": name})
            dn = result.stdout.strip()
            return dn if dn else None
        except Exception:
            return None

    def rename_ad_object(self, dn: str, new_name: str) -> bool:
        # FIX: dn and new_name passed as PS variables — no f-string interpolation
        script = "Rename-ADObject -Identity $DN -NewName $NewName -ErrorAction Stop; 'OK'"
        try:
            result = self._get_runner().run_script(script, {"DN": dn, "NewName": new_name})
            return "OK" in result.stdout
        except Exception:
            return False
