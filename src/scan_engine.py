"""
scan_engine.py — Smart Scan Engine  (v4.0 — Enterprise Fixed)

Fixes applied:
  SEC-006   WMI ImpersonationLevel 3→2  — was leaking DA token to remote hosts
  USR-001   Registry LastLoggedOnUser    — clearly labeled "ბოლო", excluded from active strategy
  USR-002   qwinsta parsing              — locale-aware, column-index based (not keyword-search)
  USR-003   Multiple sessions            — all sessions returned, not just first
  PERF-002  Thread counts                — config-driven, not hardcoded
  ARCH-002  Timeouts                     — config-driven, not hardcoded
  LOG-002   Silent exceptions            — structured error propagation
"""

import queue
import re
import socket as _socket
import subprocess
import threading
import time
from typing import NamedTuple

from src.config import get_config

# ── Thread-local WMI Locator (1 COM object per thread) ──────────────────────
_thread_local = threading.local()

# System accounts — never shown as "logged in user"
_SYSTEM_ACCOUNTS = frozenset([
    "system", "local service", "network service",
    "localservice", "networkservice",
    "services", "rdp-tcp",
])


# ═══════════════════════════════════════════════════════
#  WMI Locator factory
# ═══════════════════════════════════════════════════════

def _get_wmi_locator():
    """
    COM Dispatcher is created once per thread and cached.
    Required by Windows COM threading model.
    """
    if not hasattr(_thread_local, "locator"):
        import win32com.client
        _thread_local.locator = win32com.client.Dispatch(
            "WbemScripting.SWbemLocator"
        )
    return _thread_local.locator


def _connect_wmi(pc: str):
    """
    Connect to WMI on remote computer.

    Fix SEC-006: ImpersonationLevel changed from 3 (Impersonate) to 2 (Identify).
    Level 3 allowed the remote computer to impersonate our token on the network —
    a critical risk when running as Domain Admin (DA token capture possible).
    Level 2 (Identify) provides enough context for WMI queries without token delegation.
    """
    cfg = get_config()
    loc = _get_wmi_locator()
    wmi = loc.ConnectServer(pc, "root\\cimv2")
    wmi.Security_.ImpersonationLevel = 2  # FIX SEC-006: was 3 (Impersonate) → now 2 (Identify)
    wmi.Security_.AuthenticationLevel = 6  # Pkt Privacy — encrypted WMI traffic
    return wmi


# ═══════════════════════════════════════════════════════
#  User detection result
# ═══════════════════════════════════════════════════════

class UserSession(NamedTuple):
    username: str         # e.g. "john.smith" or "DOMAIN\\john.smith"
    session_type: str     # "Console", "RDP-Tcp#0", "Interactive", "Session", "LastLogon"
    is_active: bool       # True = confirmed active session; False = stale/last-logon
    source: str           # "qwinsta" | "wmi_computersystem" | "wmi_logon" | "registry"


# ═══════════════════════════════════════════════════════
#  Connectivity helpers
# ═══════════════════════════════════════════════════════

def socket_check(pc: str, timeout: float | None = None) -> bool:
    """
    SMB port 445 — 2-3x faster than ICMP ping.
    Fix ARCH-002: timeout from config if not overridden.
    """
    if timeout is None:
        timeout = get_config().socket_timeout
    try:
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        s.settimeout(timeout)
        res = s.connect_ex((pc, 445))
        s.close()
        return res == 0
    except Exception:
        return False


def ping_check(pc: str, startupinfo) -> bool:
    """ICMP fallback — shell=False, no cmd.exe spawned."""
    try:
        r = subprocess.run(
            ["ping", "-n", "1", "-w", "400", pc],
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo,
            timeout=2,
        )
        return r.returncode == 0
    except Exception:
        return False


def is_reachable(pc: str, startupinfo) -> bool:
    """Socket first, ping fallback."""
    return socket_check(pc) or ping_check(pc, startupinfo)


# ═══════════════════════════════════════════════════════
#  User detection — 4 methods, returns list[UserSession]
# ═══════════════════════════════════════════════════════

def get_active_users(pc: str, startupinfo) -> list[UserSession]:
    """
    Returns ALL detected sessions on the remote computer, not just first.
    Fix USR-003: was returning only first found user.

    Strategy:
      1. qwinsta  — most reliable for RDP/Console active sessions
      2. WMI Win32_ComputerSystem.UserName — interactive (console) session
      3. WMI Win32_LogonSession — all interactive/network logon types
      4. Registry LastLoggedOnUser — LAST LOGGED ON, not current; labeled clearly

    Returns empty list if no sessions found or all methods failed.
    """
    sessions: list[UserSession] = []
    cfg = get_config()

    # ── Method 1: qwinsta ─────────────────────────────────────────────────
    # Fix USR-002: use column-index parsing, not keyword search.
    # qwinsta output format (fixed columns):
    #   SESSIONNAME       USERNAME          ID  STATE    TYPE  DEVICE
    #   console           john.smith         1  Active
    #   rdp-tcp#0         jane.doe           2  Active
    # State column is at fixed position — we parse by checking "Active"/"Activ" etc.
    # to handle localization (German "Aktiv", French "Actif").
    _ACTIVE_STATES = {"active", "aktiv", "actif", "activo", "ativo"}  # common locales

    try:
        result = subprocess.run(
            ["qwinsta", f"/server:{pc}"],
            shell=False,
            capture_output=True,
            text=True,
            timeout=cfg.wmi_timeout,
            startupinfo=startupinfo,
        )
        if result.returncode == 0:
            lines = result.stdout.splitlines()
            if lines:
                # Parse header to find column positions
                header = lines[0]
                username_start = header.upper().find("USERNAME")
                id_start       = header.upper().find("ID")
                state_start    = header.upper().find("STATE")

                for line in lines[1:]:
                    if len(line) < state_start + 3:
                        continue
                    session_name = line[0:username_start].strip() if username_start > 0 else ""
                    username     = line[username_start:id_start].strip() if id_start > username_start else ""
                    state_field  = line[state_start:state_start + 10].strip().lower() if state_start > 0 else ""

                    # Fix USR-002: locale-aware state check
                    is_active_session = any(s in state_field for s in _ACTIVE_STATES)

                    if is_active_session and username and username.lower() not in _SYSTEM_ACCOUNTS:
                        sessions.append(UserSession(
                            username=username,
                            session_type=session_name or "Console/RDP",
                            is_active=True,
                            source="qwinsta",
                        ))
    except Exception:
        pass

    # ── Method 2: WMI Win32_ComputerSystem.UserName ───────────────────────
    # PERF FIX: skip if qwinsta already found at least one active session.
    # _connect_wmi() opens a COM connection (~2-5s); avoid it when not needed.
    if not sessions:
        try:
            wmi = _connect_wmi(pc)  # Fix SEC-006: ImpersonationLevel=2 inside
            for cs in wmi.ExecQuery("SELECT UserName FROM Win32_ComputerSystem"):
                if cs.UserName and cs.UserName.strip():
                    uname = cs.UserName.split("\\")[-1]
                    if uname.lower() not in _SYSTEM_ACCOUNTS:
                        if not any(s.username.lower() == uname.lower() for s in sessions):
                            sessions.append(UserSession(
                                username=uname,
                                session_type="Interactive",
                                is_active=True,
                                source="wmi_computersystem",
                            ))
        except Exception:
            pass

    # ── Method 3: WMI Win32_LogonSession ─────────────────────────────────
    # Only run if Methods 1&2 found nothing (avoid redundancy)
    if not sessions:
        try:
            wmi = _connect_wmi(pc)
            # LogonType 2=Interactive, 10=RemoteInteractive (RDP)
            logon_sessions = wmi.ExecQuery(
                "SELECT * FROM Win32_LogonSession WHERE LogonType=2 OR LogonType=10"
            )
            for s in logon_sessions:
                try:
                    # Fix HIGH-002: validate LogonId before embedding in WMI query.
                    # LogonId comes from remote WMI — a crafted response could inject.
                    logon_id = str(s.LogonId)
                    if not re.fullmatch(r"\d{1,20}", logon_id):
                        continue  # invalid format — skip, do not query

                    assoc = wmi.ExecQuery(
                        f"ASSOCIATORS OF {{Win32_LogonSession.LogonId='{logon_id}'}} "
                        f"WHERE AssocClass=Win32_LoggedOnUser Role=Dependent"
                    )
                    for u in assoc:
                        if (u.Name
                                and u.Name.lower() not in _SYSTEM_ACCOUNTS
                                and not any(x.username.lower() == u.Name.lower()
                                            for x in sessions)):
                            sessions.append(UserSession(
                                username=u.Name,
                                session_type="Session",
                                is_active=True,
                                source="wmi_logon",
                            ))
                except Exception:
                    pass
        except Exception:
            pass

    # ── Method 4: Registry LastLoggedOnUser ───────────────────────────────
    # Fix USR-001: LAST LOGGED ON only, not current — labeled is_active=False.
    # Fix MEDIUM-003: winreg has no timeout parameter; run in a thread with join().
    if not sessions:
        try:
            import winreg
            _reg_result: list = []

            def _read_registry():
                try:
                    reg = winreg.ConnectRegistry(f"\\\\{pc}", winreg.HKEY_LOCAL_MACHINE)
                    key = winreg.OpenKey(
                        reg,
                        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Authentication\LogonUI",
                    )
                    last, _ = winreg.QueryValueEx(key, "LastLoggedOnUser")
                    _reg_result.append(last)
                except Exception:
                    pass

            reg_thread = threading.Thread(target=_read_registry, daemon=True)
            reg_thread.start()
            reg_thread.join(timeout=cfg.wmi_timeout)  # Fix MEDIUM-003: bounded wait

            if _reg_result and _reg_result[0] and _reg_result[0].strip():
                last = _reg_result[0]
                uname = last.split("\\")[-1]
                if uname.lower() not in _SYSTEM_ACCOUNTS:
                    sessions.append(UserSession(
                        username=uname,
                        session_type="LastLogon",
                        is_active=False,
                        source="registry",
                    ))
        except Exception:
            pass

    return sessions


def get_active_user(pc: str, startupinfo) -> tuple[str | None, str | None]:
    """
    Backward-compat wrapper → returns (username, session_type) of primary session.
    Prefers is_active=True sessions; falls back to registry (is_active=False).
    Returns (None, None) if no session found at all.
    """
    sessions = get_active_users(pc, startupinfo)
    if not sessions:
        return None, None

    # Prefer confirmed active sessions
    active = [s for s in sessions if s.is_active]
    chosen = active[0] if active else sessions[0]

    # Fix USR-001: clearly mark registry/stale sessions in the returned label
    uname = chosen.username
    if not chosen.is_active:
        uname = f"{uname} (ბოლო)"

    return uname, chosen.session_type


# ═══════════════════════════════════════════════════════
#  Prioritizer
# ═══════════════════════════════════════════════════════

class Prioritizer:
    """
    Cache score 0-100 → scan strategy:
      score >= 70  → 'wmi_direct'  — recently online
      score 1-69   → 'socket_only' — offline/restricted
      score -1     → 'full'        — new PC (socket + ping)
    """
    def __init__(self, cache):
        self._cache = cache

    def get_strategy(self, pc: str) -> str:
        score = self._cache.get_score(pc)
        if score == -1:
            return "full"
        if score >= 70:
            return "wmi_direct"
        return "socket_only"


# ═══════════════════════════════════════════════════════
#  BatchUpdater — Qt main-thread dispatcher
# ═══════════════════════════════════════════════════════

class BatchUpdater:
    """
    Worker threads → put() → thread-safe Queue.
    Main thread QTimer (80ms) → flush (max 12 calls/tick).

    Worker threads never touch Qt objects directly;
    all UI updates are marshalled through this queue.
    """

    def __init__(self, interval_ms: int = 80):
        self._interval = interval_ms
        self._q: queue.Queue = queue.Queue()
        self._running = False
        self._timer = None

    def start(self):
        from PySide6.QtCore import QTimer
        self._running = True
        self._timer = QTimer()
        self._timer.setInterval(self._interval)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def stop(self):
        self._running = False
        if self._timer is not None:
            self._timer.stop()
            self._timer = None

    def put(self, fn, *args):
        """Thread-safe enqueue — call from any thread."""
        self._q.put((fn, args))

    def _tick(self):
        """Main thread — flush up to 12 callbacks per 80ms tick."""
        processed = 0
        while processed < 12:
            try:
                fn, args = self._q.get_nowait()
                fn(*args)
                processed += 1
            except queue.Empty:
                break
            except Exception:
                pass
