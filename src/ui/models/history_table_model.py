"""
ui/models/history_table_model.py — Model for rename history dialog.
"""
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from dataclasses import dataclass
from typing import Optional


@dataclass
class HistoryRow:
    operation_id: str
    old_name:     str
    new_name:     str
    operator:     str
    timestamp:    str
    status:       str
    duration_ms:  Optional[int]
    error_code:   Optional[str]


class HistoryTableModel(QAbstractTableModel):
    HEADERS = ["ID", "ძველი სახელი", "ახალი სახელი", "ოპერატორი", "დრო", "სტატუსი"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[HistoryRow] = []

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        r = self._rows[index.row()]
        if role == Qt.DisplayRole:
            return [r.operation_id, r.old_name, r.new_name,
                    r.operator, r.timestamp, r.status][index.column()]
        if role == Qt.UserRole:
            return r
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return None

    def load(self, rows: list[HistoryRow]):
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def get_row(self, visual_row: int) -> Optional[HistoryRow]:
        if 0 <= visual_row < len(self._rows):
            return self._rows[visual_row]
        return None
