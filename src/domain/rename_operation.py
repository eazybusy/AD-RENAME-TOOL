"""
domain/rename_operation.py — Rename operation value object.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class RenameStatus(Enum):
    PENDING     = "pending"
    RUNNING     = "running"
    SUCCESS     = "success"
    FAILED      = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class RenameOperation:
    old_name: str
    new_name: str
    operator: str
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: RenameStatus = RenameStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_code: Optional[str] = None
    error_detail: Optional[str] = None
    pre_dn: Optional[str] = None        # AD DN snapshot for rollback
    ad_verified: bool = False
    spn_updated: bool = False
    dns_triggered: bool = False
    rollback_attempted: bool = False
    rollback_ok: bool = False

    def mark_started(self):
        self.status = RenameStatus.RUNNING
        self.started_at = datetime.utcnow()

    def mark_success(self):
        self.status = RenameStatus.SUCCESS
        self.completed_at = datetime.utcnow()

    def mark_failed(self, code: str, detail: str = ""):
        self.status = RenameStatus.FAILED
        self.error_code = code
        self.error_detail = detail
        self.completed_at = datetime.utcnow()

    @property
    def duration_ms(self) -> Optional[int]:
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds() * 1000)
        return None
