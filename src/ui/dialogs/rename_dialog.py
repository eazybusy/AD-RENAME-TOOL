"""
ui/dialogs/rename_dialog.py — Single rename confirmation and progress dialog.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QProgressBar,
)
from PySide6.QtCore import Qt, QTimer


class RenameDialog(QDialog):
    """Shows rename progress, log output, and final result."""

    def __init__(self, old_name: str, new_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"გადარქმევა: {old_name} → {new_name}")
        self.setMinimumWidth(550)
        self.setMinimumHeight(360)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)
        self._setup_ui(old_name, new_name)

    def _setup_ui(self, old_name: str, new_name: str):
        layout = QVBoxLayout(self)

        # Header
        self._lbl_status = QLabel(f"🔄 {old_name}  →  {new_name}")
        self._lbl_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._lbl_status)

        # Step progress bar
        self._progress = QProgressBar()
        self._progress.setMaximum(10)  # 10 workflow steps
        self._progress.setValue(0)
        layout.addWidget(self._progress)

        # Log output
        self._log_box = QTextEdit()
        self._log_box.setReadOnly(True)
        layout.addWidget(self._log_box)

        # Buttons
        btn_row = QHBoxLayout()
        self._btn_close = QPushButton("დახურვა")
        self._btn_close.setEnabled(False)
        self._btn_close.clicked.connect(self.accept)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_close)
        layout.addLayout(btn_row)

    def append_log(self, msg: str):
        self._log_box.append(msg)

    def step_done(self):
        self._progress.setValue(self._progress.value() + 1)

    def mark_success(self, old_name: str, new_name: str):
        self._lbl_status.setText(f"✅ {old_name} → {new_name} — წარმატება!")
        self._lbl_status.setStyleSheet("color: #a6e3a1; font-weight: bold;")
        self._btn_close.setEnabled(True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowCloseButtonHint)

    def mark_failed(self, error_code: str, detail: str = ""):
        self._lbl_status.setText(f"❌ შეცდომა: {error_code}")
        self._lbl_status.setStyleSheet("color: #f38ba8; font-weight: bold;")
        if detail:
            self._log_box.append(f"[ERROR] {detail}")
        self._btn_close.setEnabled(True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowCloseButtonHint)
