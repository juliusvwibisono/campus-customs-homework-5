"""Append-only audit trail for agent, delegation, and MCP activity."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any


_AUDIT_FILE_LOCK = Lock()


class AuditTrail:
    def __init__(self, path: Path, run_id: str):
        self.path = path
        self.run_id = run_id
        self._lock = _AUDIT_FILE_LOCK
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]\n", encoding="utf-8")

    def append(self, event: str, **details: Any) -> dict[str, Any]:
        with self._lock:
            try:
                existing = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise RuntimeError("audit_trail.json is not valid JSON; refusing to overwrite it") from exc
            if not isinstance(existing, list):
                raise RuntimeError("audit_trail.json must contain a JSON list")

            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "run_id": self.run_id,
                "event": event,
                **details,
            }
            existing.append(record)
            self.path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
            return record
