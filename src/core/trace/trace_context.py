from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TraceContext:
    """Lightweight trace container for ingestion/query flows."""

    trace_type: str = "ingestion"
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: float = field(default_factory=time.perf_counter)
    stages: List[Dict[str, Any]] = field(default_factory=list)
    finished_at: Optional[float] = None

    def record_stage(self, name: str, **data: Any) -> None:
        self.stages.append({"name": name, **data})

    def finish(self) -> None:
        if self.finished_at is None:
            self.finished_at = time.perf_counter()

    @property
    def total_latency_ms(self) -> float:
        end = self.finished_at if self.finished_at is not None else time.perf_counter()
        return (end - self.started_at) * 1000

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "trace_type": self.trace_type,
            "stages": self.stages,
            "total_latency_ms": self.total_latency_ms,
        }
