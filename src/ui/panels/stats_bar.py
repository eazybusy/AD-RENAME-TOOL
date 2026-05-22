"""
ui/panels/stats_bar.py — Statistics bar matching old project layout.
Shows: ჯამი | Online | ცარიელი | Offline | შეზღ.
"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


def _make_stat_box(label: str, color: str, obj_name: str) -> tuple[QWidget, QLabel]:
    box = QWidget()
    box.setObjectName(obj_name)
    lay = QVBoxLayout(box)
    lay.setContentsMargins(8, 4, 8, 4)
    lay.setSpacing(0)

    lt = QLabel(label)
    lt.setStyleSheet(f"color: {color}; font-size: 11px; background: transparent; border: none;")
    lt.setAlignment(Qt.AlignCenter)

    lv = QLabel("0")
    lv.setStyleSheet(
        f"color: {color}; font-size: 18px; font-weight: bold; background: transparent; border: none;"
    )
    lv.setAlignment(Qt.AlignCenter)

    lay.addWidget(lt)
    lay.addWidget(lv)
    return box, lv


class StatsBar(QWidget):
    """
    Compact stat boxes in the header (matches old project design).
    Keys: total | online | no_user | offline | blocked
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._vals: dict[str, QLabel] = {}

        specs = [
            ("total",   "ჯამი",    "#64748b", "StatBox"),
            ("online",  "Online",  "#22c55e", "StatBoxOnline"),
            ("no_user", "ცარიელი", "#f59e0b", "StatBoxWarn"),
            ("offline", "Offline", "#ef4444", "StatBoxOffline"),
            ("blocked", "შეზღ.",   "#a78bfa", "StatBoxBlocked"),
        ]
        for key, name, color, obj in specs:
            box, val_lbl = _make_stat_box(name, color, obj)
            layout.addWidget(box)
            self._vals[key] = val_lbl

    # ── Public API ───────────────────────────────────────────────────────

    def set(self, key: str, value: int):
        if key in self._vals:
            self._vals[key].setText(str(value))

    def increment(self, key: str):
        if key in self._vals:
            cur = int(self._vals[key].text())
            self._vals[key].setText(str(cur + 1))

    def increment_online(self):
        self.increment("online")
        self._recalc_total()

    def increment_offline(self):
        self.increment("offline")
        self._recalc_total()

    def increment_no_user(self):
        self.increment("no_user")
        self._recalc_total()

    def increment_blocked(self):
        self.increment("blocked")
        self._recalc_total()

    def _recalc_total(self):
        total = sum(
            int(self._vals[k].text())
            for k in ("online", "no_user", "offline", "blocked")
        )
        self._vals["total"].setText(str(total))

    def reset(self):
        for lbl in self._vals.values():
            lbl.setText("0")

    def get(self, key: str) -> int:
        return int(self._vals.get(key, type("X", (), {"text": lambda s: "0"})()).text())
