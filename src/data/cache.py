"""
data/cache.py — SQLite-backed computer cache (TASK 4.2).
- WAL mode: concurrent reads, atomic writes
- Indexed queries: O(log n) vs O(n) for JSON scan
- Migration: auto-imports existing scan_cache.json
- Corruption recovery: auto-recreates DB on disk-image errors
"""
import sqlite3
import threading
import os
import json
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS computers (
    name        TEXT PRIMARY KEY,
    status      TEXT NOT NULL,
    username    TEXT,
    last_seen   TEXT,
    score       INTEGER DEFAULT 50,
    updated_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_status ON computers(status);
CREATE INDEX IF NOT EXISTS idx_score  ON computers(score);
"""


class SmartCache:
    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self._path = db_path
        else:
            from src.config import get_config
            cfg = get_config()
            self._path = os.path.join(cfg.data_dir(), "scan_cache.db")
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None  # FIX: persistent connection
        self._init_db()
        self._migrate_from_json()

    def _init_db(self):
        """Initialize DB, auto-recover if corrupted."""
        try:
            self._setup_db()
            # Verify integrity — catches silent corruption
            result = self._conn.execute("PRAGMA integrity_check").fetchone()
            if result[0] != "ok":
                raise sqlite3.DatabaseError(f"Integrity check failed: {result[0]}")
        except sqlite3.DatabaseError as e:
            logger.warning(f"Cache DB corrupted ({e}), recreating: {self._path}")
            self._recreate_db()

    def _setup_db(self):
        # FIX: persistent connection reused across all operations (5-10× faster)
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def _recreate_db(self):
        """Delete corrupted DB and create a fresh one."""
        try:
            if os.path.exists(self._path):
                os.replace(self._path, self._path + ".corrupt")
                logger.info(f"Corrupted DB backed up as {self._path}.corrupt")
            # Also remove WAL/SHM sidecar files
            for ext in ("-wal", "-shm"):
                p = self._path + ext
                if os.path.exists(p):
                    os.remove(p)
        except OSError as e:
            logger.error(f"Could not remove corrupt DB: {e}")
        self._setup_db()

    def _migrate_from_json(self):
        """One-time import of legacy scan_cache.json."""
        try:
            from src.config import get_config
            cfg = get_config()
            old_path = os.path.join(cfg.data_dir(), "scan_cache.json")
        except Exception:
            return

        if not os.path.exists(old_path):
            return
        try:
            with open(old_path, encoding="utf-8") as f:
                data = json.load(f)
            for name, entry in data.items():
                self._conn.execute(
                    "INSERT OR IGNORE INTO computers "
                    "(name, status, username, last_seen, score) "
                    "VALUES (?,?,?,?,?)",
                    (name.upper(), entry.get("status", "unknown"),
                     entry.get("user", ""), entry.get("last_seen", ""),
                     entry.get("score", 50))
                )
            self._conn.commit()
            os.rename(old_path, old_path + ".migrated")
        except Exception:
            pass

    def update(self, pc: str, status: str, user: str = None) -> None:
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._lock:
            try:
                self._do_update(pc, status, user, now)
            except sqlite3.DatabaseError as e:
                logger.warning(f"Cache update failed ({e}), recreating DB and retrying")
                self._recreate_db()
                try:
                    self._do_update(pc, status, user, now)
                except sqlite3.DatabaseError as e2:
                    logger.error(f"Cache update failed after recovery: {e2}")

    def _do_update(self, pc: str, status: str, user: Optional[str], now: str):
        # FIX: reuse persistent connection — no open/close per call
        self._conn.execute(
            "INSERT INTO computers (name,status,username,last_seen,score,updated_at) "
            "VALUES (?,?,?,?,50,?) "
            "ON CONFLICT(name) DO UPDATE SET "
            "  status=excluded.status, "
            "  username=excluded.username, "
            "  last_seen=excluded.last_seen, "
            "  updated_at=excluded.updated_at, "
            "  score=CASE "
            "    WHEN excluded.status='online' THEN MIN(100, score+15) "
            "    WHEN excluded.status IN ('offline','blocked') THEN MAX(0, score-10) "
            "    ELSE score END",
            (pc.upper(), status, user or "", now, now)
        )
        self._conn.commit()

    def get_score(self, pc: str) -> int:
        try:
            with self._lock:
                row = self._conn.execute(
                    "SELECT score FROM computers WHERE name=?", (pc.upper(),)
                ).fetchone()
            return row[0] if row else -1
        except sqlite3.DatabaseError:
            return -1

    def all_pcs(self) -> dict:
        try:
            with self._lock:
                rows = self._conn.execute(
                    "SELECT name,status,username,last_seen,score FROM computers"
                ).fetchall()
            return {
                r[0]: {"status": r[1], "user": r[2], "last_seen": r[3], "score": r[4]}
                for r in rows
            }
        except sqlite3.DatabaseError:
            return {}

    def save(self):
        pass  # SQLite auto-commits — no explicit save needed
