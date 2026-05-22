"""
ui/main_window.py — Main window.
Copyright (c) 2024, T. Kharazishvili. All rights reserved.

Changes:
  - Removed header RENAME button (RenamePanel in side panel handles this)
  - Fixed Watch ON/OFF: button now enabled after scan; watches online PCs
  - Online user detection: watcher enabled at startup if cache has data
"""
import threading
import time
import logging

from PySide6.QtCore    import Qt, QObject, Signal, Slot, QTimer
from PySide6.QtGui     import QIcon, QPixmap
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QPlainTextEdit,
    QMessageBox, QInputDialog, QSplitter,
)

from src.config              import get_config
from src.data.cache          import SmartCache
from src.data.audit_logger   import (
    AuditLogger, get_windows_identity,
    EVT_SCAN_START, EVT_SCAN_DONE,
)
from src.data.scan_history   import ScanHistory
from src.infrastructure.ad_repository    import ADRepository
from src.infrastructure.powershell_runner import PSRunner
from src.infrastructure.wmi_client       import WMIClient
from src.infrastructure.notifier         import UserNotifier
from src.infrastructure.spn_manager      import SPNManager
from src.application.rename_service      import RenameService, ServiceContainer
from src.application.scan_service        import ScanService
from src.application.watcher_service     import WatcherService
from src.domain.computer                 import Computer, ComputerStatus
from src.scan_engine                     import Prioritizer
from src.ui.panels.scan_panel            import ScanPanel
from src.ui.panels.rename_panel          import RenamePanel
from src.ui.panels.stats_bar             import StatsBar
from src.ui.models.computer_table_model  import ComputerRow, OfflineRow
from src.ui.styles                       import QSS_STYLE

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════
#  Cross-thread signal bridge
# ════════════════════════════════════════════════════════════

class _Signals(QObject):
    log_sig            = Signal(str, str)       # (message, colour)
    progress_sig       = Signal(int, int)        # (done, total)
    stats_sig          = Signal()
    online_sig         = Signal(object)          # ComputerRow
    offline_sig        = Signal(object)          # OfflineRow
    update_offline_sig = Signal(str)             # name — refresh last-seen
    finish_sig         = Signal(bool)            # success
    came_online_sig    = Signal(str, object, object)  # (name, user, stype)
    watch_badge_sig    = Signal(int, int)        # (count, secs_left)
    rename_done_sig    = Signal(str, str, bool, str)


# ════════════════════════════════════════════════════════════
#  Main Window
# ════════════════════════════════════════════════════════════

class ADRenameApp(QMainWindow):

    def __init__(self):
        super().__init__()

        self._cfg      = get_config()
        self._cache    = SmartCache()
        self._audit    = AuditLogger()
        self._history  = ScanHistory()
        self._operator = get_windows_identity()

        # Infrastructure
        self._ad_repo   = ADRepository(self._cfg)
        self._ps_runner = PSRunner()
        self._wmi       = WMIClient(self._cfg)
        self._notifier  = UserNotifier()
        self._spn_mgr   = SPNManager()

        # Services
        self._svc = ServiceContainer(
            ad_repo=self._ad_repo, ps_runner=self._ps_runner,
            wmi=self._wmi, notifier=self._notifier,
            spn_mgr=self._spn_mgr, audit=self._audit, config=self._cfg,
        )
        prioritizer       = Prioritizer(self._cache)
        self._scan_svc    = ScanService(self._ad_repo, self._wmi, self._cache, self._cfg, prioritizer)
        self._rename_svc  = RenameService(self._svc, self._cfg, self._append_log_str)
        self._watcher_svc = WatcherService(self._wmi, self._cache, self._cfg)

        # Wire scan callbacks
        self._scan_svc.on_computer_online  = self._cb_online
        self._scan_svc.on_computer_offline = self._cb_offline
        self._scan_svc.on_log              = self._cb_log
        self._scan_svc.on_complete         = self._cb_done
        self._scan_svc.on_total_known      = self._cb_total_known
        self._scan_svc.on_progress         = self._cb_progress

        # Counters
        self._lock         = threading.Lock()
        self._cnt_online   = 0
        self._cnt_no_user  = 0
        self._cnt_offline  = 0
        self._cnt_blocked  = 0
        self._scan_total   = 0
        self._scan_done    = 0
        self._scan_running = False
        self._scan_start   = 0.0

        self._watcher_active  = False
        self._watch_interval  = self._cfg.watch_interval

        # Signals
        self._sig = _Signals()
        self._sig.log_sig.connect(self._append_log)
        self._sig.online_sig.connect(self._add_online_ui)
        self._sig.offline_sig.connect(self._add_offline_ui)
        self._sig.update_offline_sig.connect(self._update_offline_last_seen_ui)
        self._sig.finish_sig.connect(self._on_scan_done)
        self._sig.came_online_sig.connect(self._pc_came_online)
        self._sig.watch_badge_sig.connect(self._update_watch_badge)
        self._sig.rename_done_sig.connect(self._on_rename_done_ui)
        self._sig.progress_sig.connect(self._update_progress_ui)

        self._build_ui()
        self._load_cache()

        self._audit.log("APP_START", self._operator,
                        f"version=4.1 config={self._cfg.ad_search_base or 'domain_root'}",
                        event_id=EVT_SCAN_START)
        self.log(f"[~] ოპერატორი: {self._operator}")

    # ── UI Construction ──────────────────────────────────────────────────

    def _build_ui(self):
        self.setWindowTitle("AD Computer Management v4.1")
        self.setGeometry(100, 100, 1380, 900)
        self.setMinimumSize(960, 680)
        self.setStyleSheet(QSS_STYLE)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # ── Header ───────────────────────────────────────────────────────
        header = QWidget()
        header.setObjectName("HeaderFrame")
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(14, 10, 14, 10)
        hlay.setSpacing(10)

        # Title
        title = QLabel("⬡ AD Manager")
        title.setStyleSheet(
            "color: #3b82f6; font-size: 17px; font-weight: bold; background: transparent;"
        )
        hlay.addWidget(title)

        # Buttons — RENAME button removed; rename is in the side panel
        self._btn_scan = QPushButton("⟳  SCAN")
        self._btn_scan.setObjectName("btnScan")
        self._btn_scan.setMinimumWidth(90)
        self._btn_scan.clicked.connect(self._start_scan)

        self._btn_stop = QPushButton("■  STOP")
        self._btn_stop.setObjectName("btnStop")
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop_scan)

        # FIX: watcher button now starts enabled if cache has data
        self._btn_watcher = QPushButton("◉  Watch: OFF")
        self._btn_watcher.setObjectName("btnWatcher")
        self._btn_watcher.setEnabled(False)
        self._btn_watcher.clicked.connect(self._toggle_watcher)

        self._btn_history = QPushButton("📋  ისტორია")
        self._btn_history.setObjectName("btnHistory")
        self._btn_history.clicked.connect(self._show_history)

        for btn in (self._btn_scan, self._btn_stop,
                    self._btn_watcher, self._btn_history):
            hlay.addWidget(btn)

        # Progress badge
        self._lbl_progress = QLabel("")
        self._lbl_progress.setObjectName("ProgressBadge")
        self._lbl_progress.hide()
        hlay.addWidget(self._lbl_progress)

        # Watch badge
        self._lbl_watch_badge = QLabel("")
        self._lbl_watch_badge.setObjectName("WatchBadge")
        self._lbl_watch_badge.hide()
        hlay.addWidget(self._lbl_watch_badge)

        hlay.addStretch()

        # Search
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔎 კომპიუტერი ან მომხმარებელი...")
        self._search.setMinimumWidth(260)
        self._search.textChanged.connect(self._on_search)
        hlay.addWidget(self._search)

        hlay.addStretch()

        # Stats
        self._stats = StatsBar()
        hlay.addWidget(self._stats)

        root.addWidget(header)

        # ── Main panel (scan tables + rename panel) ───────────────────────
        panel = QWidget()
        panel.setObjectName("MainPanelFrame")
        panel_lay = QHBoxLayout(panel)
        panel_lay.setContentsMargins(8, 8, 8, 8)
        panel_lay.setSpacing(8)

        # Scan panel (online + offline tables)
        self._scan_panel = ScanPanel()
        self._scan_panel.computer_selected.connect(self._on_computer_selected)

        # Rename panel (side panel — this is the rename module)
        self._rename_panel = RenamePanel()
        self._rename_panel.rename_requested.connect(self._start_rename)
        self._rename_panel.setMaximumWidth(300)
        self._rename_panel.setMinimumWidth(240)

        panel_lay.addWidget(self._scan_panel, stretch=3)
        panel_lay.addWidget(self._rename_panel, stretch=1)

        root.addWidget(panel, stretch=1)

        # ── Terminal ─────────────────────────────────────────────────────
        term_bar = QWidget()
        term_bar.setObjectName("TerminalBar")
        tbl = QHBoxLayout(term_bar)
        tbl.setContentsMargins(10, 4, 10, 4)
        tbl.addWidget(QLabel("მიმდინარე მოვლენები"))
        tbl.addStretch()
        btn_cl = QPushButton("clear")
        btn_cl.setObjectName("btnClearLog")
        btn_cl.clicked.connect(lambda: self._log_box.clear())
        tbl.addWidget(btn_cl)
        root.addWidget(term_bar)

        self._log_box = QPlainTextEdit()
        self._log_box.setObjectName("TerminalBox")
        self._log_box.setReadOnly(True)
        self._log_box.setMaximumHeight(150)
        root.addWidget(self._log_box)

    def resizeEvent(self, event):
        super().resizeEvent(event)

    # ── Cache load ────────────────────────────────────────────────────────

    def _load_cache(self):
        cached = self._cache.all_pcs()
        if not cached:
            return
        for pc, data in cached.items():
            status    = data.get("status", "unknown")
            user      = data.get("user", "") or "—"
            last_seen = data.get("last_seen", "")[:10]
            if status == "online":
                self._scan_panel.add_online_computer(ComputerRow(
                    name=pc, user=user, session="cache",
                    status=f"📦 {last_seen}", tag="CACHED", is_online=True,
                ))
            else:
                self._scan_panel.add_offline_computer(OfflineRow(
                    name=pc,
                    reason=f"📦 {status}",
                    last_seen=last_seen,
                    tag="OFFLINE",
                ))
        self.log(f"[~] Cache ჩატვირთულია — {len(cached)} PC-ის ისტორია.")

        # FIX: enable watcher immediately if cache has any PCs
        if cached:
            self._btn_watcher.setEnabled(True)

    # ── Scan ──────────────────────────────────────────────────────────────

    def _start_scan(self):
        if self._watcher_active:
            self._stop_watcher()

        self._scan_panel.clear()
        self._stats.reset()
        with self._lock:
            self._cnt_online = self._cnt_no_user = self._cnt_offline = self._cnt_blocked = 0
            self._scan_total = self._scan_done = 0
        self._scan_running = True
        self._scan_start   = time.monotonic()

        self._btn_scan.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._btn_watcher.setEnabled(False)
        self._lbl_progress.show()

        self._audit.log("SCAN_START", self._operator, "", event_id=EVT_SCAN_START)
        self._scan_svc.start()

    def _stop_scan(self):
        self._scan_svc.stop()
        self._btn_stop.setEnabled(False)
        self._lbl_progress.hide()
        self.log("[!] სკანირება შეჩერდა.")

    # ── Scan callbacks (worker threads → signals → main thread) ──────────

    def _cb_total_known(self, total: int):
        with self._lock:
            self._scan_total = total

    def _cb_progress(self, done: int, total: int):
        self._sig.progress_sig.emit(done, total)

    def _cb_online(self, computer: Computer):
        """Called from ScanService thread."""
        with self._lock:
            self._scan_done += 1
            if computer.current_user:
                self._cnt_online += 1
                tag = "ACTIVE"
            else:
                self._cnt_no_user += 1
                tag = "NO_USER"

        row = ComputerRow(
            name=computer.name,
            user=computer.current_user or "— ცარიელია",
            session=computer.session_type or "—",
            status="ONLINE" if computer.current_user else "გამოუყენებელი",
            tag=tag,
            is_online=True,
        )
        self._sig.online_sig.emit(row)

    def _cb_offline(self, computer: Computer):
        """Called from ScanService thread."""
        with self._lock:
            self._scan_done += 1
            if computer.status == ComputerStatus.BLOCKED:
                self._cnt_blocked += 1
                reason = "ACCESS DENIED — შეზღუდული"
                tag    = "BLOCKED"
            else:
                self._cnt_offline += 1
                reason = "OFFLINE — ხაზგარეშე"
                tag    = "OFFLINE"

        row = OfflineRow(name=computer.name, reason=reason, tag=tag)
        self._sig.offline_sig.emit(row)

    def _cb_log(self, msg: str):
        self._sig.log_sig.emit(msg, "#22d3ee")

    def _cb_done(self, success: bool):
        self._sig.finish_sig.emit(success)

    @Slot(object)
    def _add_online_ui(self, row: ComputerRow):
        self._scan_panel.add_online_computer(row)
        if row.tag == "ACTIVE":
            self._stats.set("online", self._cnt_online)
        elif row.tag == "NO_USER":
            self._stats.set("no_user", self._cnt_no_user)
        self._stats.set("total",
            self._cnt_online + self._cnt_no_user + self._cnt_offline + self._cnt_blocked)

    @Slot(object)
    def _add_offline_ui(self, row: OfflineRow):
        self._scan_panel.add_offline_computer(row)
        if row.tag == "BLOCKED":
            self._stats.set("blocked", self._cnt_blocked)
        else:
            self._stats.set("offline", self._cnt_offline)
        self._stats.set("total",
            self._cnt_online + self._cnt_no_user + self._cnt_offline + self._cnt_blocked)

    @Slot(int, int)
    def _update_progress_ui(self, done, total):
        if total > 0:
            self._lbl_progress.setText(f"{done} / {total}")
            self._scan_panel.show_progress(True, done, total)
        else:
            self._lbl_progress.hide()

    @Slot(bool)
    def _on_scan_done(self, success: bool):
        self._scan_running = False
        self._btn_scan.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._lbl_progress.hide()
        self._scan_panel.show_progress(False)

        if success:
            duration = time.monotonic() - self._scan_start
            self._history.record(
                self._cnt_online + self._cnt_no_user + self._cnt_offline + self._cnt_blocked,
                self._cnt_online, self._cnt_offline, self._cnt_blocked, duration, False,
            )
        self._cache.save()
        self._audit.log("SCAN_DONE", self._operator,
                        f"online={self._cnt_online} offline={self._cnt_offline}",
                        event_id=EVT_SCAN_DONE)

        # FIX: enable watcher after any completed scan (not just when offline > 0)
        # Watcher monitors ONLINE PCs for user changes — makes sense after any scan
        total_found = self._cnt_online + self._cnt_no_user + self._cnt_offline + self._cnt_blocked
        if total_found > 0:
            self._btn_watcher.setEnabled(True)

        status = "სკანირება დასრულდა" if success else "სკანირება შეჩერდა"
        self.log(f"[✓] {status}. Online: {self._cnt_online} | Offline: {self._cnt_offline} | Blocked: {self._cnt_blocked}")

    # ── Computer selection → Rename panel ─────────────────────────────────

    def _on_computer_selected(self, name: str):
        """Row selected in online table — pre-fill rename panel."""
        self._rename_panel.set_computer(name)

    # ── Watcher ───────────────────────────────────────────────────────────

    def _toggle_watcher(self):
        if self._watcher_active:
            self._stop_watcher()
        else:
            self._start_watcher()

    def _start_watcher(self):
        if self._watcher_active:
            return
        self._watcher_active = True

        # Wire watcher callbacks before starting
        self._watcher_svc.on_status_change = self._cb_watch_status
        self._watcher_svc.on_log           = self._cb_log
        self._watcher_svc.start()

        # Update button appearance
        self._btn_watcher.setText("◉  Watch: ON")
        self._btn_watcher.setObjectName("btnWatcherOn")
        self._btn_watcher.setStyleSheet("")  # force QSS re-resolve

        # Show badge and start countdown timer
        self._lbl_watch_badge.show()
        self._watch_secs = self._watch_interval
        self._watch_timer_id = self.startTimer(1000)

        online_count = self._scan_panel.online_count()
        self.log(f"[◉] Watch ON — {online_count} online PC პერიოდულად მოწმდება.")

    def _stop_watcher(self):
        if not self._watcher_active:
            return
        self._watcher_active = False
        self._watcher_svc.stop()

        self._btn_watcher.setText("◉  Watch: OFF")
        self._btn_watcher.setObjectName("btnWatcher")
        self._btn_watcher.setStyleSheet("")

        self._lbl_watch_badge.hide()
        if hasattr(self, "_watch_timer_id"):
            self.killTimer(self._watch_timer_id)
            del self._watch_timer_id

        self.log("[◉] Watch OFF.")

    def timerEvent(self, event):
        if not self._watcher_active:
            return
        self._watch_secs -= 1
        if self._watch_secs <= 0:
            self._watch_secs = self._watch_interval
        online_count = self._scan_panel.online_count()
        self._sig.watch_badge_sig.emit(online_count, self._watch_secs)

    def _cb_watch_status(self, pc: str, new_status: str, user):
        if new_status == "online" and user:
            self._sig.came_online_sig.emit(pc, user, None)
        else:
            self._sig.update_offline_sig.emit(pc)

    @Slot(str)
    def _update_offline_last_seen_ui(self, name: str):
        self._scan_panel.update_offline_last_seen(name)

    @Slot(str, object, object)
    def _pc_came_online(self, pc: str, user, stype):
        row = ComputerRow(
            name=pc,
            user=user or "— ცარიელია",
            session=stype or "—",
            status="⚡ ახლა Online",
            tag="CAME_ONLINE",
            is_online=True,
        )
        self._scan_panel.move_offline_to_online(pc, row)
        with self._lock:
            self._cnt_offline = max(0, self._cnt_offline - 1)
            if user:
                self._cnt_online += 1
            else:
                self._cnt_no_user += 1
        self._stats.set("online",  self._cnt_online)
        self._stats.set("no_user", self._cnt_no_user)
        self._stats.set("offline", self._cnt_offline)

    @Slot(int, int)
    def _update_watch_badge(self, count: int, secs: int):
        if secs <= 3:
            self._lbl_watch_badge.setText(f"⟳ {count} pc — შემოწმება...")
        else:
            self._lbl_watch_badge.setText(f"⏱ {count} pc | {secs}წმ")

    # ── Rename ────────────────────────────────────────────────────────────

    def _start_rename(self, old_name: str, new_name: str):
        if self._cfg.require_confirmation:
            reply = QMessageBox.question(
                self,
                "დადასტურება საჭიროა",
                f"გსურთ კომპიუტერის სახელი შეიცვალოს?\n\n"
                f"  {old_name}  →  {new_name}\n\n"
                "ეს ოპერაცია შეუქცევადია.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        from src.ui.dialogs.rename_dialog import RenameDialog
        dlg = RenameDialog(old_name, new_name, self)
        dlg.show()

        def _on_log(msg):
            QTimer.singleShot(0, self, lambda m=msg: (
                dlg.append_log(m),
                dlg.step_done(),
            ))

        def _on_done(op):
            def _ui():
                if op.status.value == "success":
                    dlg.mark_success(op.old_name, op.new_name)
                    self._sig.rename_done_sig.emit(op.old_name, op.new_name, True, "")
                else:
                    dlg.mark_failed(op.error_code or "UNKNOWN", op.error_detail or "")
                    self._sig.rename_done_sig.emit(
                        op.old_name, op.new_name, False, op.error_code or "ERR"
                    )
            QTimer.singleShot(0, self, _ui)

        self._rename_svc.rename_async(
            old_name, new_name, self._operator,
            on_complete=_on_done,
            on_log=_on_log,
        )

    @Slot(str, str, bool, str)
    def _on_rename_done_ui(self, old: str, new: str, success: bool, err: str):
        if success:
            self.log(f"[✓] Rename: {old} ➔ {new}")
        else:
            self.log(f"[-] Rename failed: {old} ({err})")

    # ── History ───────────────────────────────────────────────────────────

    def _show_history(self):
        from src.ui.dialogs.history_dialog import RenameHistoryDialog
        dlg = RenameHistoryDialog(self._cfg.audit_log_path(), self._rename_svc, self)
        dlg.exec()

    # ── Search ────────────────────────────────────────────────────────────

    def _on_search(self, text: str):
        self._scan_panel.set_filter(text.strip())

    # ── Logging ───────────────────────────────────────────────────────────

    @Slot(str, str)
    def _append_log(self, text: str, color: str):
        self._log_box.appendHtml(f"<font color='{color}'>{text}</font>")

    def _append_log_str(self, msg: str):
        """Called from service layer (no colour)."""
        self.log(msg)

    def log(self, message: str):
        if message.startswith(("[✓]", "[+]")):   color = "#22c55e"
        elif message.startswith(("[-]", "[!]")):  color = "#ef4444"
        elif message.startswith(("[*]", "[→]")):  color = "#f59e0b"
        else:                                      color = "#22d3ee"
        self._sig.log_sig.emit(message, color)

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def closeEvent(self, event):
        self._scan_svc.stop()
        self._watcher_svc.stop()
        self._cache.save()
        self._audit.log("APP_EXIT", self._operator, "")
        event.accept()
