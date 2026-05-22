"""
ui/styles.py — Application stylesheet (Enhanced Enterprise Dark Theme).
Merges old project's rich QSS with improved visuals.
"""

QSS_STYLE = r"""
/* ═══════════════════════════════════════════════
   BASE
═══════════════════════════════════════════════ */
QMainWindow {
    background: #0d0f14;
}
QWidget {
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 9pt;
    color: #cbd5e1;
}

/* ═══════════════════════════════════════════════
   HEADER / PANEL FRAMES
═══════════════════════════════════════════════ */
#HeaderFrame {
    background-color: rgba(15, 20, 30, 200);
    border: 1px solid rgba(59, 130, 246, 40);
    border-radius: 10px;
}
#MainPanelFrame {
    background-color: rgba(10, 14, 22, 140);
    border: 1px solid rgba(42, 51, 71, 180);
    border-radius: 10px;
}
#OnlineFrame {
    background-color: rgba(10, 20, 10, 60);
    border: 1px solid rgba(34, 197, 94, 30);
    border-radius: 8px;
}
#OfflineFrame {
    background-color: rgba(20, 10, 10, 60);
    border: 1px solid rgba(239, 68, 68, 30);
    border-radius: 8px;
}

/* ═══════════════════════════════════════════════
   TABLES  (QTableView + QTableWidget)
═══════════════════════════════════════════════ */
QTableView, QTableWidget {
    background-color: transparent;
    alternate-background-color: rgba(30, 38, 54, 60);
    color: #cbd5e1;
    gridline-color: rgba(42, 51, 71, 80);
    border: none;
    border-radius: 6px;
    font-family: "Consolas", monospace;
    font-size: 12px;
    selection-background-color: transparent;
    outline: none;
}
QTableView::item, QTableWidget::item {
    padding: 6px 10px;
    border: none;
    border-bottom: 1px solid rgba(42, 51, 71, 50);
}
QTableView::item:hover, QTableWidget::item:hover {
    background-color: rgba(59, 130, 246, 25);
    color: #e2e8f0;
}
QTableView::item:selected, QTableWidget::item:selected {
    background-color: rgba(37, 99, 235, 90);
    color: #93c5fd;
    border-left: 2px solid #3b82f6;
}

/* ═══════════════════════════════════════════════
   HEADER VIEW
═══════════════════════════════════════════════ */
QHeaderView {
    background-color: transparent;
}
QHeaderView::section {
    background-color: rgba(15, 23, 42, 200);
    color: #475569;
    padding: 8px 10px;
    font-weight: bold;
    font-size: 11px;
    border: none;
    border-bottom: 1px solid rgba(59, 130, 246, 60);
    border-right: 1px solid rgba(42, 51, 71, 60);
}
QHeaderView::section:hover {
    background-color: rgba(30, 41, 59, 220);
    color: #94a3b8;
}

/* ═══════════════════════════════════════════════
   SCROLLBAR
═══════════════════════════════════════════════ */
QScrollBar:vertical {
    background: rgba(10, 14, 22, 80);
    width: 8px;
    border-radius: 4px;
    margin: 0;
    border: none;
}
QScrollBar::handle:vertical {
    background: rgba(59, 130, 246, 120);
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(96, 165, 250, 210);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    background: none;
}
QScrollBar:horizontal {
    background: rgba(10, 14, 22, 80);
    height: 8px;
    border-radius: 4px;
    margin: 0;
    border: none;
}
QScrollBar::handle:horizontal {
    background: rgba(59, 130, 246, 120);
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: rgba(96, 165, 250, 210);
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
    background: none;
}

/* ═══════════════════════════════════════════════
   TERMINAL
═══════════════════════════════════════════════ */
#TerminalBar {
    background-color: rgba(15, 20, 30, 200);
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid rgba(42, 51, 71, 180);
    border-bottom: none;
}
#TerminalBox {
    background-color: rgba(5, 8, 14, 220);
    color: #22d3ee;
    font-family: "Consolas", monospace;
    font-size: 12px;
    border-bottom-left-radius: 6px;
    border-bottom-right-radius: 6px;
    border: 1px solid rgba(42, 51, 71, 180);
    border-top: none;
}

/* ═══════════════════════════════════════════════
   INPUTS
═══════════════════════════════════════════════ */
QLineEdit {
    background-color: rgba(15, 23, 42, 200);
    color: #e2e8f0;
    border: 1px solid rgba(42, 51, 71, 220);
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}
QLineEdit:focus {
    border: 1px solid rgba(59, 130, 246, 200);
    background-color: rgba(20, 30, 50, 220);
}
QLineEdit:read-only {
    background-color: rgba(10, 14, 22, 160);
    color: #64748b;
}

/* ═══════════════════════════════════════════════
   BUTTONS
═══════════════════════════════════════════════ */
QPushButton {
    color: #e2e8f0;
    font-weight: bold;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 12px;
    border: 1px solid rgba(255, 255, 255, 10);
    background-color: rgba(30, 41, 59, 200);
}
QPushButton:hover {
    background-color: rgba(51, 65, 85, 240);
    border: 1px solid rgba(59, 130, 246, 80);
}
QPushButton:pressed {
    padding-top: 8px;
    padding-bottom: 6px;
    background-color: rgba(30, 58, 138, 200);
}
QPushButton:disabled {
    background-color: rgba(30, 41, 59, 80);
    color: #334155;
    border: 1px solid rgba(42, 51, 71, 60);
}
QPushButton#btnScan {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #2563eb, stop:1 #1d4ed8);
    border: 1px solid rgba(96, 165, 250, 60);
    color: #fff;
}
QPushButton#btnScan:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #3b82f6, stop:1 #2563eb);
}
QPushButton#btnStop {
    background: rgba(49, 18, 18, 200);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 40);
}
QPushButton#btnStop:hover {
    background: rgba(69, 28, 28, 220);
}
QPushButton#btnRename {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #2563eb, stop:1 #1d4ed8);
    color: #fff;
    border: 1px solid rgba(96, 165, 250, 60);
}
QPushButton#btnRename:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #3b82f6, stop:1 #2563eb);
}
QPushButton#btnRename:disabled {
    background: rgba(30, 41, 59, 80);
    color: #334155;
    border: 1px solid rgba(42, 51, 71, 60);
}
QPushButton#btnWatcher {
    background: rgba(12, 48, 64, 200);
    color: #22d3ee;
    border: 1px solid rgba(34, 211, 238, 40);
}
QPushButton#btnWatcherOn {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #0e7490, stop:1 #0891b2);
    color: #fff;
    border: 1px solid rgba(34, 211, 238, 80);
}
QPushButton#btnHistory {
    background: rgba(40, 20, 60, 200);
    color: #a78bfa;
    border: 1px solid rgba(167, 139, 250, 40);
}
QPushButton#btnHistory:hover {
    background: rgba(60, 30, 90, 220);
}
QPushButton#btnClearLog {
    background: transparent;
    color: #475569;
    border: none;
    font-family: "Consolas";
    padding: 0;
    font-size: 11px;
}
QPushButton#btnClearLog:hover {
    color: #94a3b8;
}

/* ═══════════════════════════════════════════════
   STAT BOXES
═══════════════════════════════════════════════ */
#StatBox {
    background-color: rgba(15, 23, 42, 160);
    border: 1px solid rgba(42, 51, 71, 180);
    border-radius: 8px;
    padding: 4px 10px;
}
#StatBoxOnline {
    background-color: rgba(5, 40, 10, 140);
    border: 1px solid rgba(34, 197, 94, 50);
    border-radius: 8px;
    padding: 4px 10px;
}
#StatBoxOffline {
    background-color: rgba(40, 5, 5, 140);
    border: 1px solid rgba(239, 68, 68, 50);
    border-radius: 8px;
    padding: 4px 10px;
}
#StatBoxWarn {
    background-color: rgba(40, 30, 0, 140);
    border: 1px solid rgba(245, 158, 11, 50);
    border-radius: 8px;
    padding: 4px 10px;
}
#StatBoxBlocked {
    background-color: rgba(30, 10, 50, 140);
    border: 1px solid rgba(167, 139, 250, 50);
    border-radius: 8px;
    padding: 4px 10px;
}

/* ═══════════════════════════════════════════════
   BADGE LABELS
═══════════════════════════════════════════════ */
#ProgressBadge {
    color: #3b82f6;
    font-weight: bold;
    background: rgba(30, 58, 95, 200);
    padding: 4px 10px;
    border-radius: 5px;
    font-family: "Consolas";
    font-size: 12px;
}
#WatchBadge {
    color: #22d3ee;
    font-weight: bold;
    background: rgba(12, 48, 64, 200);
    padding: 4px 10px;
    border-radius: 5px;
    font-family: "Consolas";
    font-size: 12px;
}

/* ═══════════════════════════════════════════════
   GROUP BOX  (rename panel)
═══════════════════════════════════════════════ */
QGroupBox {
    border: 1px solid rgba(42, 51, 71, 200);
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 6px;
    background-color: rgba(10, 14, 22, 100);
}
QGroupBox::title {
    color: #3b82f6;
    subcontrol-origin: margin;
    left: 10px;
    font-weight: bold;
    font-size: 12px;
}

/* ═══════════════════════════════════════════════
   SECTION LABELS (Online / Offline titles)
═══════════════════════════════════════════════ */
#LblOnlineTitle {
    color: #22c55e;
    font-weight: bold;
    font-size: 13px;
}
#LblOfflineTitle {
    color: #ef4444;
    font-weight: bold;
    font-size: 13px;
}
#LblSectionCount {
    color: #475569;
    font-size: 11px;
}

/* ═══════════════════════════════════════════════
   DIALOGS / MESSAGEBOXES
═══════════════════════════════════════════════ */
QMessageBox, QInputDialog {
    background-color: #0f172a;
    color: #e2e8f0;
}
QMessageBox QLabel, QInputDialog QLabel {
    color: #e2e8f0;
    font-size: 13px;
}
QMessageBox QPushButton, QInputDialog QPushButton {
    background-color: #1e3a5f;
    color: #93c5fd;
    min-width: 80px;
    border: 1px solid rgba(59, 130, 246, 60);
}
QMessageBox QPushButton:hover, QInputDialog QPushButton:hover {
    background-color: #2563eb;
    color: #fff;
}
QInputDialog QLineEdit {
    background-color: rgba(15, 23, 42, 220);
    border: 1px solid rgba(59, 130, 246, 120);
    color: #e2e8f0;
    border-radius: 4px;
    padding: 6px;
}

/* ═══════════════════════════════════════════════
   STATUS BAR
═══════════════════════════════════════════════ */
QStatusBar {
    background-color: rgba(5, 8, 14, 200);
    color: #475569;
    font-size: 11px;
    border-top: 1px solid rgba(42, 51, 71, 120);
}

/* ═══════════════════════════════════════════════
   SPLITTER
═══════════════════════════════════════════════ */
QSplitter::handle {
    background: rgba(42, 51, 71, 160);
    width: 2px;
    margin: 4px 0;
}
QSplitter::handle:hover {
    background: rgba(59, 130, 246, 120);
}

/* ═══════════════════════════════════════════════
   PROGRESS BAR
═══════════════════════════════════════════════ */
QProgressBar {
    background-color: rgba(15, 23, 42, 180);
    border: none;
    border-radius: 3px;
    height: 5px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #2563eb, stop:1 #22d3ee);
    border-radius: 3px;
}

/* ═══════════════════════════════════════════════
   VALIDATION LABELS
═══════════════════════════════════════════════ */
#LblValidOk  { color: #22c55e; font-size: 12px; }
#LblValidErr { color: #ef4444; font-size: 12px; }
"""

# Backward compat alias
DARK_STYLESHEET = QSS_STYLE
