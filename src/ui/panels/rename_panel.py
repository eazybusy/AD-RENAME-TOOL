"""
ui/panels/rename_panel.py — Rename input panel.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLineEdit, QLabel, QGroupBox,
)
from PySide6.QtCore import Signal


class RenamePanel(QWidget):
    """Input panel for single computer rename."""

    rename_requested = Signal(str, str)  # (old_name, new_name)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        grp = QGroupBox("კომპიუტერის გადარქმევა")
        form = QFormLayout(grp)

        self._edit_current = QLineEdit()
        self._edit_current.setReadOnly(True)
        self._edit_current.setPlaceholderText("სკანიდან ავტომატურად...")
        form.addRow("მიმდინარე სახელი:", self._edit_current)

        self._edit_new = QLineEdit()
        self._edit_new.setPlaceholderText("მაქს. 15 სიმბ., მხოლოდ A-Z 0-9 -")
        self._edit_new.setMaxLength(15)
        form.addRow("ახალი სახელი:", self._edit_new)

        self._lbl_validation = QLabel("")
        self._lbl_validation.setStyleSheet("color: #f38ba8;")
        form.addRow("", self._lbl_validation)

        self._btn_rename = QPushButton("✏️ გადარქმევა")
        self._btn_rename.setObjectName("btn_rename")
        self._btn_rename.setEnabled(False)
        self._btn_rename.clicked.connect(self._on_rename_click)
        form.addRow("", self._btn_rename)

        layout.addWidget(grp)
        layout.addStretch()

        self._edit_new.textChanged.connect(self._validate)

    def set_computer(self, name: str):
        self._edit_current.setText(name)
        self._validate()

    def _validate(self):
        from src.domain.validation import validate_hostname
        new_name = self._edit_new.text().strip()
        current = self._edit_current.text().strip()

        if not current or not new_name:
            self._lbl_validation.setText("")
            self._btn_rename.setEnabled(False)
            return

        ok, msg = validate_hostname(new_name)
        if ok:
            self._lbl_validation.setText("✅ სახელი სწორია")
            self._lbl_validation.setStyleSheet("color: #a6e3a1;")
            self._btn_rename.setEnabled(True)
        else:
            self._lbl_validation.setText(f"❌ {msg}")
            self._lbl_validation.setStyleSheet("color: #f38ba8;")
            self._btn_rename.setEnabled(False)

    def _on_rename_click(self):
        old = self._edit_current.text().strip()
        new = self._edit_new.text().strip()
        if old and new:
            self.rename_requested.emit(old, new)
