"""
domain/computer.py — Core Computer entity.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ComputerStatus(Enum):
    ONLINE  = "online"
    OFFLINE = "offline"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@dataclass
class Computer:
    name: str
    status: ComputerStatus = ComputerStatus.UNKNOWN
    current_user: Optional[str] = None
    session_type: Optional[str] = None
    last_seen: Optional[datetime] = None
    score: int = 50  # Prioritizer score 0-100

    def __post_init__(self):
        self.name = self.name.upper()

    def is_renameable(self) -> bool:
        return self.status == ComputerStatus.ONLINE

    def to_cache_dict(self) -> dict:
        return {
            "status": self.status.value,
            "user": self.current_user or "",
            "last_seen": self.last_seen.isoformat() if self.last_seen else "",
            "score": self.score,
        }

    @classmethod
    def from_cache_dict(cls, name: str, d: dict) -> "Computer":
        ls = None
        if d.get("last_seen"):
            try:
                ls = datetime.fromisoformat(d["last_seen"])
            except ValueError:
                pass
        return cls(
            name=name,
            status=ComputerStatus(d.get("status", "unknown")),
            current_user=d.get("user") or None,
            last_seen=ls,
            score=d.get("score", 50),
        )
