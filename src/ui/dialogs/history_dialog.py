"""
ui/dialogs/history_dialog.py — Rename history + rollback UI (TASK 3.3).
"""
import json
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTableView, QPushButton,
    QMessageBox, QHBoxLayout,
)
from PySide6.QtCore import Qt

from src.ui.models.history_table_model import HistoryTableModel, HistoryRow


class RenameHistoryDialog(QDialog):
    """
    Shows all rename operations from audit log.
    Allows one-click rollback for recent successful renames.
    TASK 3.3.
    """

    def __init__(self, audit_path: str, rename_svc, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rename ისტორია")
        self.setMinimumSize(700, 450)
        self._audit_path = audit_path
        self._svc = rename_svc
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self._table = QTableView()
        self._model = HistoryTableModel()
        self._table.setModel(self._model)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.setSelectionMode(QTableView.SingleSelection)
        self._table.setEditTriggers(QTableView.NoEditTriggers)
        layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        btn_rollback = QPushButton("↩ Rollback არჩეული")
        btn_rollback.clicked.connect(self._do_rollback)
        btn_close = QPushButton("დახურვა")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_rollback)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _load(self):
        """Parse audit log and extract RENAME_SUCCESS entries."""
        rows = []
        try:
            if not os.path.exists(self._audit_path):
                return
            with open(self._audit_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("op") not in ("RENAME_SUCCESS", "RENAME_START"):
                            continue
                        details = entry.get("details", "")
                        # Parse "old=X, new=Y" from details
                        parts = dict(
                            p.strip().split("=", 1)
                            for p in details.split(",")
                            if "=" in p
                        )
                        rows.append(HistoryRow(
                            operation_id=entry.get("correlation_id", "?"),
                            old_name=parts.get("old", "?"),
                            new_name=parts.get("new", "?"),
                            operator=entry.get("operator", "?"),
                            timestamp=entry.get("ts", ""),
                            status="SUCCESS" if entry.get("op") == "RENAME_SUCCESS" else "STARTED",
                            duration_ms=None,
                            error_code=None,
                        ))
                    except Exception:
                        continue
        except Exception:
            pass
        self._model.load(list(reversed(rows)))  # newest first

    def _do_rollback(self):
        indexes = self._table.selectionModel().selectedRows()
        if not indexes:
            return
        row = self._model.get_row(indexes[0].row())
        if not row or row.status != "SUCCESS":
            QMessageBox.warning(self, "Rollback", "მხოლოდ წარმატებული rename-ის rollback შეიძლება.")
            return
        confirm = QMessageBox.question(
            self, "Rollback დადასტურება",
            f"დავაბრუნოთ:\n  {row.new_name} → {row.old_name}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            self._svc.rollback(row.old_name, row.new_name)
            self.accept()
