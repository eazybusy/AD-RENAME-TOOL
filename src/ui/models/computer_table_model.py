"""
ui/models/computer_table_model.py — Virtual QAbstractTableModel (TASK 1.2).
Replaces QTableWidget — handles 100,000+ rows without freeze.
Contains both OnlineComputerModel (4-col) and OfflineComputerModel (3-col).
"""
import time
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor, QBrush, QFont
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ComputerRow:
    name:      str
    user:      str
    session:   str
    status:    str
    tag:       str    # CACHED | ACTIVE | NO_USER | CAME_ONLINE
    is_online: bool


@dataclass
class OfflineRow:
    name:      str
    reason:    str
    last_seen: str = field(default_factory=lambda: time.strftime("%H:%M:%S"))
    tag:       str = "OFFLINE"


# ═══════════════════════════════════════════════════════
#  Online Table Model  (კომპიუტერი | მომხმარებელი | სესია | სტატუსი)
# ═══════════════════════════════════════════════════════

class OnlineComputerModel(QAbstractTableModel):
    HEADERS = ["კომპიუტერი", "მომხმარებელი", "სესია", "სტატუსი"]

    # tag → (foreground hex, bold?)
    _TAG_STYLE = {
        "ACTIVE":      ("#e2e8f0", False),
        "NO_USER":     ("#f59e0b", False),
        "CAME_ONLINE": ("#22d3ee", True),
        "CACHED":      ("#475569", False),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source:   list[ComputerRow] = []
        self._filtered: list[ComputerRow] = []
        self._query = ""

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._filtered)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 4

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._filtered[index.row()]

        if role == Qt.DisplayRole:
            return [row.name, row.user, row.session, row.status][index.column()]

        if role == Qt.ForegroundRole:
            col = index.column()
            fg, _ = self._TAG_STYLE.get(row.tag, ("#cbd5e1", False))
            if col == 1 and row.tag == "NO_USER":
                return QBrush(QColor("#f59e0b"))
            if col == 0 and row.tag == "CAME_ONLINE":
                return QBrush(QColor("#22d3ee"))
            if row.tag == "CACHED":
                return QBrush(QColor("#475569"))
            return QBrush(QColor(fg))

        if role == Qt.FontRole:
            _, bold = self._TAG_STYLE.get(row.tag, ("#cbd5e1", False))
            f = QFont("Consolas", 9)
            f.setBold(bold)
            return f

        if role == Qt.UserRole:
            return row

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return None

    def add_or_update(self, row: ComputerRow):
        for i, existing in enumerate(self._source):
            if existing.name == row.name:
                self._source[i] = row
                self._refilter()
                return
        self.beginInsertRows(QModelIndex(), len(self._source), len(self._source))
        self._source.append(row)
        self.endInsertRows()
        self._refilter()

    def remove_by_name(self, name: str):
        self._source = [r for r in self._source if r.name != name]
        self._refilter()

    def set_filter(self, query: str):
        self._query = query.lower().strip()
        self._refilter()

    def _refilter(self):
        self.beginResetModel()
        q = self._query
        if q:
            self._filtered = [
                r for r in self._source
                if q in r.name.lower() or q in r.user.lower()
            ]
        else:
            self._filtered = list(self._source)
        self.endResetModel()

    def clear(self):
        self.beginResetModel()
        self._source.clear()
        self._filtered.clear()
        self.endResetModel()

    def get_row(self, visual_row: int) -> Optional[ComputerRow]:
        if 0 <= visual_row < len(self._filtered):
            return self._filtered[visual_row]
        return None

    def all_rows(self) -> list[ComputerRow]:
        return list(self._source)

    def count(self) -> int:
        return len(self._source)


# ═══════════════════════════════════════════════════════
#  Offline Table Model  (კომპიუტერი | მიზეზი | ბოლო ping)
# ═══════════════════════════════════════════════════════

class OfflineComputerModel(QAbstractTableModel):
    HEADERS = ["კომპიუტერი", "მიზეზი", "ბოლო ping"]

    _REASON_COLOR = {
        "OFFLINE":      "#ef4444",
        "ACCESS_DENIED": "#a78bfa",
        "BLOCKED":      "#a78bfa",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source:   list[OfflineRow] = []
        self._filtered: list[OfflineRow] = []
        self._query = ""

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._filtered)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 3

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._filtered[index.row()]

        if role == Qt.DisplayRole:
            return [row.name, row.reason, row.last_seen][index.column()]

        if role == Qt.ForegroundRole:
            col = index.column()
            if col == 0:
                return QBrush(QColor("#fca5a5"))   # light red for pc name
            if col == 1:
                color = self._REASON_COLOR.get(row.tag, "#94a3b8")
                return QBrush(QColor(color))
            # col 2 — last seen time
            return QBrush(QColor("#475569"))

        if role == Qt.FontRole:
            f = QFont("Consolas", 9)
            return f

        if role == Qt.UserRole:
            return row

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return None

    def add_or_update(self, row: OfflineRow):
        for i, existing in enumerate(self._source):
            if existing.name == row.name:
                self._source[i] = row
                self._refilter()
                return
        self.beginInsertRows(QModelIndex(), len(self._source), len(self._source))
        self._source.append(row)
        self.endInsertRows()
        self._refilter()

    def update_last_seen(self, name: str):
        now = time.strftime("%H:%M:%S")
        for i, r in enumerate(self._source):
            if r.name == name:
                self._source[i] = OfflineRow(r.name, r.reason, now, r.tag)
                self._refilter()
                return

    def remove_by_name(self, name: str):
        self._source = [r for r in self._source if r.name != name]
        self._refilter()

    def set_filter(self, query: str):
        self._query = query.lower().strip()
        self._refilter()

    def _refilter(self):
        self.beginResetModel()
        q = self._query
        if q:
            self._filtered = [r for r in self._source if q in r.name.lower()]
        else:
            self._filtered = list(self._source)
        self.endResetModel()

    def clear(self):
        self.beginResetModel()
        self._source.clear()
        self._filtered.clear()
        self.endResetModel()

    def get_row(self, visual_row: int) -> Optional[OfflineRow]:
        if 0 <= visual_row < len(self._filtered):
            return self._filtered[visual_row]
        return None

    def count(self) -> int:
        return len(self._source)
