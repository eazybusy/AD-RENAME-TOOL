"""
data/scan_history.py — Scan history storage and retrieval.
"""
import os
import json
import time
from typing import Optional


class ScanHistory:
    """Stores scan session summaries in the scans directory."""

    def __init__(self, config=None):
        if config is None:
            from src.config import get_config
            config = get_config()
        self._cfg = config

    def save_scan(self, scan_id: str, summary: dict) -> None:
        scans_dir = self._cfg.scans_dir()
        fname = f"scan_{scan_id}.json"
        path = os.path.join(scans_dir, fname)
        summary["scan_id"] = scan_id
        summary["saved_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def list_scans(self) -> list[dict]:
        scans_dir = self._cfg.scans_dir()
        results = []
        try:
            for fname in sorted(os.listdir(scans_dir), reverse=True):
                if fname.startswith("scan_") and fname.endswith(".json"):
                    path = os.path.join(scans_dir, fname)
                    try:
                        with open(path, encoding="utf-8") as f:
                            results.append(json.load(f))
                    except Exception:
                        pass
        except Exception:
            pass
        return results

    def purge_old(self, retention_days: int) -> None:
        if retention_days <= 0:
            return
        scans_dir = self._cfg.scans_dir()
        cutoff = time.time() - retention_days * 86400
        try:
            for fname in os.listdir(scans_dir):
                path = os.path.join(scans_dir, fname)
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
        except Exception:
            pass
