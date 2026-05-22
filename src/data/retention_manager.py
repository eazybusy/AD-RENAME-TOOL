"""
data/retention_manager.py — GDPR audit log retention + anonymization (TASK 1.3).
CRITICAL FIX: HMAC-protected originals are NEVER modified.
Anonymization creates a SEPARATE *_anon.log.gz copy.
"""
import os
import time
import gzip
import re as _re
import threading
import json
import hashlib

_user_re = _re.compile(r'([A-Za-z0-9\-]+\\)[A-Za-z0-9\.\-_]+')


def _safe_log_error(msg: str):
    try:
        import logging
        logging.getLogger(__name__).error(msg)
    except Exception:
        pass


class RetentionManager:
    """
    Manages audit log lifecycle:
      - Rotate + compress daily logs older than 1 day
      - Delete compressed logs older than retention_days
      - GDPR anonymization: create *_anon.log.gz COPY (never modify original)
    """

    def __init__(self, config=None):
        if config is None:
            from src.config import get_config
            config = get_config()
        self._cfg = config

    def run(self) -> None:
        """Run all retention tasks."""
        self._compress_old_logs()
        self._delete_expired_archives()
        self._anonymize_old_archives()

    def _compress_old_logs(self):
        """Compress daily log files older than 1 day."""
        data_dir = self._cfg.data_dir()
        cutoff = time.time() - 86400  # 1 day

        for fname in os.listdir(data_dir):
            if not fname.endswith(".log") or fname.endswith(".log.gz"):
                continue
            # Skip the current active log
            if fname == os.path.basename(self._cfg.audit_log_path()):
                continue
            fpath = os.path.join(data_dir, fname)
            if os.path.getmtime(fpath) >= cutoff:
                continue

            gz_path = fpath + ".gz"
            try:
                with open(fpath, "rb") as f_in:
                    with gzip.open(gz_path, "wb") as f_out:
                        f_out.write(f_in.read())
                os.remove(fpath)
            except Exception as e:
                _safe_log_error(f"RetentionManager: compress failed for {fname}: {e}")

    def _delete_expired_archives(self):
        """Delete .log.gz files older than audit_log_retention_days."""
        days = self._cfg.audit_log_retention_days
        if days <= 0:
            return
        data_dir = self._cfg.data_dir()
        cutoff = time.time() - days * 86400

        for fname in os.listdir(data_dir):
            if not fname.endswith(".log.gz"):
                continue
            fpath = os.path.join(data_dir, fname)
            try:
                if os.path.getmtime(fpath) < cutoff:
                    os.remove(fpath)
            except Exception as e:
                _safe_log_error(f"RetentionManager: delete failed for {fname}: {e}")

    def _anonymize_old_archives(self) -> None:
        """
        TASK 1.3 CRITICAL FIX:
        GDPR anonymization — creates SEPARATE anonymized copy.
        NEVER modifies the original HMAC-protected archive.

        Original:    audit_20260101.log.gz  (HMAC intact, restricted access)
        Anonymized:  audit_20260101_anon.log.gz  (no HMAC, GDPR-compliant)
        """
        days = self._cfg.anonymize_after_days
        if days <= 0:
            return

        data_dir = self._cfg.data_dir()
        cutoff = time.time() - days * 86400

        for fname in os.listdir(data_dir):
            # Only process originals — skip already-anonymized files
            if not fname.endswith('.log.gz') or fname.endswith('_anon.log.gz'):
                continue
            fpath = os.path.join(data_dir, fname)
            anon_path = fpath.replace('.log.gz', '_anon.log.gz')

            try:
                if os.path.getmtime(fpath) >= cutoff:
                    continue
                if os.path.exists(anon_path):
                    continue  # already anonymized

                with gzip.open(fpath, 'rt', encoding='utf-8', errors='replace') as f:
                    content = f.read()

                anonymized = _user_re.sub(r'\1[redacted]', content)

                # Write anonymized COPY — original is UNTOUCHED
                tmp = anon_path + '.tmp'
                with gzip.open(tmp, 'wt', encoding='utf-8') as f:
                    f.write(anonymized)
                os.replace(tmp, anon_path)

                _safe_log_error(
                    f"DataRetention: anonymized copy created: {anon_path} "
                    f"(original preserved for audit integrity)"
                )
            except Exception as e:
                _safe_log_error(f"DataRetention: anonymization failed for {fname}: {e}")
