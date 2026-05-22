"""
application/scan_service.py — AD network scan orchestration.
Extracted from ADRenameApp.scan_network() and _phase2_wmi().
UI-independent: communicates via callbacks/signals.
"""
import threading
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional

from src.domain.computer import Computer, ComputerStatus
from src.infrastructure.interfaces import IADRepository, IWMIClient

logger = logging.getLogger(__name__)


class ScanService:
    def __init__(self, ad_repo: IADRepository, wmi_client: IWMIClient,
                 cache, config, prioritizer):
        self._ad = ad_repo
        self._wmi = wmi_client
        self._cache = cache
        self._cfg = config
        self._prio = prioritizer
        self._stop_event = threading.Event()
        self._scan_id: Optional[str] = None

        # Callbacks — set by UI layer
        self.on_computer_online:  Optional[Callable] = None  # (Computer)
        self.on_computer_offline: Optional[Callable] = None  # (Computer)
        self.on_progress:         Optional[Callable] = None  # (done, total)
        self.on_total_known:      Optional[Callable] = None  # (total) — called once
        self.on_log:              Optional[Callable] = None  # (msg)
        self.on_complete:         Optional[Callable] = None  # (success)

    def start(self) -> threading.Thread:
        self._stop_event.clear()
        self._scan_id = str(uuid.uuid4())[:8]
        t = threading.Thread(target=self._run, daemon=True, name="ScanService")
        t.start()
        return t

    def stop(self):
        self._stop_event.set()

    def _run(self):
        self._log(f"[*] AD-დან კომპიუტერების სია იტვირთება...")
        try:
            computers = self._ad.get_all_computer_names()
        except Exception as e:
            self._log(f"[-] AD query failed: {e}")
            self._complete(False)
            return

        total = len(computers)
        self._log(f"[+] ნაპოვნია {total} კომპ. (Phase 1 — SMB check)...")

        # Notify UI of total count for progress bar
        if self.on_total_known:
            self.on_total_known(total)

        reachable, unreachable = self._phase1_smb(computers)

        done = 0
        for pc_name in unreachable:
            if self._stop_event.is_set():
                break
            c = Computer(name=pc_name, status=ComputerStatus.OFFLINE)
            self._cache.update(pc_name, "offline")
            if self.on_computer_offline:
                self.on_computer_offline(c)
            done += 1
            if self.on_progress:
                self.on_progress(done, total)

        if self._stop_event.is_set():
            self._complete(False)
            return

        self._log(f"[*] Phase 2 — WMI user detection ({len(reachable)} კომპ.)...")
        self._phase2_wmi(reachable, done, total)
        self._complete(not self._stop_event.is_set())

    def _phase1_smb(self, computers: list[str]):
        """AsyncIO SMB scanner with thread pool fallback."""
        try:
            from src.infrastructure.async_scanner import scan_smb_async
            results = scan_smb_async(computers, timeout=self._cfg.socket_timeout)
            reachable   = [h for h, ok in results.items() if ok]
            unreachable = [h for h, ok in results.items() if not ok]
            return reachable, unreachable
        except Exception:
            reachable, unreachable = [], []
            lock = threading.Lock()

            def check(pc):
                if self._stop_event.is_set():
                    return
                strategy = self._prio.get_strategy(pc)
                if strategy == "wmi_direct":
                    with lock: reachable.append(pc)
                else:
                    try:
                        from src.scan_engine import socket_check
                        ok = socket_check(pc, self._cfg.socket_timeout)
                        with lock: (reachable if ok else unreachable).append(pc)
                    except Exception:
                        with lock: unreachable.append(pc)

            with ThreadPoolExecutor(max_workers=self._cfg.smb_threads) as ex:
                ex.map(check, computers)
            return reachable, unreachable

    def _phase2_wmi(self, computers: list[str], done_offset: int, total: int):
        done_ref = [done_offset]
        lock = threading.Lock()

        def query_one(pc):
            if self._stop_event.is_set():
                return
            try:
                user, stype = self._wmi.get_active_user(pc)
            except Exception:
                user, stype = None, None

            if user is None and stype is None:
                c = Computer(name=pc, status=ComputerStatus.BLOCKED)
                self._cache.update(pc, "blocked")
                if self.on_computer_offline:
                    self.on_computer_offline(c)
            elif user:
                c = Computer(name=pc, status=ComputerStatus.ONLINE,
                             current_user=user, session_type=stype)
                self._cache.update(pc, "online", user)
                if self.on_computer_online:
                    self.on_computer_online(c)
            else:
                c = Computer(name=pc, status=ComputerStatus.ONLINE)
                self._cache.update(pc, "online", None)
                if self.on_computer_online:
                    self.on_computer_online(c)

            with lock:
                done_ref[0] += 1
            if self.on_progress:
                self.on_progress(done_ref[0], total)

        with ThreadPoolExecutor(max_workers=self._cfg.wmi_threads) as ex:
            ex.map(query_one, computers)

    def _log(self, msg):
        if self.on_log:
            self.on_log(msg)
        else:
            logger.info(msg)

    def _complete(self, success: bool):
        if self.on_complete:
            self.on_complete(success)
