"""
main.py — Application entry point.
"""
import sys
import logging
import traceback

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    from PySide6.QtWidgets import QApplication, QMessageBox
    from PySide6.QtCore import Qt

    app = QApplication(sys.argv)
    app.setApplicationName("AD Computer Management Tool")
    app.setApplicationVersion("2.0")

    try:
        from src.ui.main_window import ADRenameApp
        window = ADRenameApp()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        tb = traceback.format_exc()
        msg = QMessageBox()
        msg.setWindowTitle("Startup Error")
        msg.setText(str(e))
        msg.setDetailedText(tb)
        msg.setIcon(QMessageBox.Critical)
        msg.exec()
        sys.exit(1)


if __name__ == "__main__":
    main()
