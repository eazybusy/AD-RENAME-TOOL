"""
application/signals.py — PySide6 signals for cross-thread communication.
"""
from PySide6.QtCore import QObject, Signal


class ScanSignals(QObject):
    computer_online  = Signal(object)   # Computer domain object
    computer_offline = Signal(object)   # Computer domain object
    progress         = Signal(int, int) # (current, total)
    log_message      = Signal(str)
    scan_complete    = Signal(bool)     # success flag


class RenameSignals(QObject):
    step_started  = Signal(str)         # step name
    step_done     = Signal(str, bool)   # (step name, success)
    log_message   = Signal(str)
    rename_done   = Signal(object)      # RenameOperation result
