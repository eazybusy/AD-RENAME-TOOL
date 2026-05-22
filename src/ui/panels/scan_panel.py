"""
ui/panels/scan_panel.py — Dual-table scan results panel.
Online computers (left/top) + Offline/Blocked (right/bottom).
Matches old project's side-by-side layout with full column info.
"""
import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTableView, QLabel, QSplitter, QHeaderView, QAbstractItemView,
    QProgressBar,
)
from PySide6.QtCore import Signal, Qt

from src.ui.models.computer_table_model import (
    OnlineComputerModel, OfflineComputerModel,
    ComputerRow, OfflineRow,
)


class ScanPanel(QWidget):
    """
    Dual-table panel:
      Left  — Online computers  (კომპიუტერი | მომხმარებელი | სესია | სტატუსი)
      Right — Offline/Blocked   (კომპიუტერი | მიზეზი        | ბოლო ping)
    """

    computer_selected = Signal(str)   # emits computer name on selection

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    # ── UI construction ──────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # Horizontal splitter: online | offline
        splitter = QSplitter(Qt.Horizontal)

        # ── Online panel ─────────────────────────────────────────────────
        online_widget = QWidget()
        online_widget.setObjectName("OnlineFrame")
        online_layout = QVBoxLayout(online_widget)
        online_layout.setContentsMargins(8, 8, 8, 8)
        online_layout.setSpacing(4)

        on_header = QHBoxLayout()
        lbl_on = QLabel("● ONLINE კომპიუტერები")
        lbl_on.setObjectName("LblOnlineTitle")
        self._lbl_online_count = QLabel("0 ჩანაწერი")
        self._lbl_online_count.setObjectName("LblSectionCount")
        on_header.addWidget(lbl_on)
        on_header.addStretch()
        on_header.addWidget(self._lbl_online_count)
        online_layout.addLayout(on_header)

        self._online_model = OnlineComputerModel()
        self.tree_online = QTableView()
        self.tree_online.setModel(self._online_model)
        self._style_table(self.tree_online)
        self.tree_online.doubleClicked.connect(self._on_online_double_click)
        self.tree_online.selectionModel().selectionChanged.connect(self._on_online_selection)
        online_layout.addWidget(self.tree_online)

        # ── Offline panel ────────────────────────────────────────────────
        offline_widget = QWidget()
        offline_widget.setObjectName("OfflineFrame")
        offline_layout = QVBoxLayout(offline_widget)
        offline_layout.setContentsMargins(8, 8, 8, 8)
        offline_layout.setSpacing(4)

        off_header = QHBoxLayout()
        lbl_off = QLabel("● OFFLINE / შეზღუდული")
        lbl_off.setObjectName("LblOfflineTitle")
        self._lbl_offline_count = QLabel("0 ჩანაწერი")
        self._lbl_offline_count.setObjectName("LblSectionCount")
        off_header.addWidget(lbl_off)
        off_header.addStretch()
        off_header.addWidget(self._lbl_offline_count)
        offline_layout.addLayout(off_header)

        self._offline_model = OfflineComputerModel()
        self.tree_offline = QTableView()
        self.tree_offline.setModel(self._offline_model)
        self._style_table(self.tree_offline)
        # Offline table: no selection for rename (read-only info)
        self.tree_offline.setSelectionMode(QAbstractItemView.NoSelection)
        offline_layout.addWidget(self.tree_offline)

        splitter.addWidget(online_widget)
        splitter.addWidget(offline_widget)
        splitter.setSizes([620, 380])

        root.addWidget(splitter, stretch=1)

        # Progress bar (slim, shown during scan)
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setMaximumHeight(5)
        self._progress.setTextVisible(False)
        root.addWidget(self._progress)

    @staticmethod
    def _style_table(view: QTableView):
        view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        view.setSelectionBehavior(QAbstractItemView.SelectRows)
        view.setSelectionMode(QAbstractItemView.SingleSelection)
        view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        view.setAlternatingRowColors(True)
        view.setShowGrid(False)
        view.verticalHeader().setVisible(False)
        view.verticalHeader().setDefaultSectionSize(34)
        view.horizontalHeader().setHighlightSections(False)
        view.setFrameShape(QTableView.NoFrame)

    # ── Signal handlers ──────────────────────────────────────────────────

    def _on_online_double_click(self, index):
        row = self._online_model.get_row(index.row())
        if row and row.is_online:
            self.computer_selected.emit(row.name)

    def _on_online_selection(self):
        indexes = self.tree_online.selectionModel().selectedRows()
        if indexes:
            row = self._online_model.get_row(indexes[0].row())
            if row and row.is_online:
                self.computer_selected.emit(row.name)

    # ── Public API ───────────────────────────────────────────────────────

    def add_online_computer(self, row: ComputerRow):
        self._online_model.add_or_update(row)
        self._lbl_online_count.setText(f"{self._online_model.count()} ჩანაწერი")

    def add_offline_computer(self, row: OfflineRow):
        self._offline_model.add_or_update(row)
        self._lbl_offline_count.setText(f"{self._offline_model.count()} ჩანაწერი")

    def move_offline_to_online(self, name: str, row: ComputerRow):
        """PC came online — remove from offline table, add to online."""
        self._offline_model.remove_by_name(name)
        self._lbl_offline_count.setText(f"{self._offline_model.count()} ჩანაწერი")
        self._online_model.add_or_update(row)
        self._lbl_online_count.setText(f"{self._online_model.count()} ჩანაწერი")

    def update_offline_last_seen(self, name: str):
        self._offline_model.update_last_seen(name)

    def set_filter(self, query: str):
        self._online_model.set_filter(query)
        self._offline_model.set_filter(query)

    def clear(self):
        self._online_model.clear()
        self._offline_model.clear()
        self._lbl_online_count.setText("0 ჩანაწერი")
        self._lbl_offline_count.setText("0 ჩანაწერი")

    def show_progress(self, visible: bool, value: int = 0, maximum: int = 100):
        self._progress.setVisible(visible)
        self._progress.setMaximum(max(maximum, 1))
        self._progress.setValue(value)

    def get_selected_name(self) -> str | None:
        indexes = self.tree_online.selectionModel().selectedRows()
        if indexes:
            row = self._online_model.get_row(indexes[0].row())
            return row.name if row else None
        return None

    def online_count(self) -> int:
        return self._online_model.count()

    def offline_count(self) -> int:
        return self._offline_model.count()

    # ── Backward compat (used by old ScanPanel callers) ──────────────────
    def add_computer(self, row: ComputerRow):
        """Compat: routes by is_online flag."""
        if row.is_online:
            self.add_online_computer(row)
        else:
            self.add_offline_computer(OfflineRow(
                name=row.name,
                reason=row.status,
                tag="BLOCKED" if "DENIED" in row.status.upper() else "OFFLINE",
            ))
