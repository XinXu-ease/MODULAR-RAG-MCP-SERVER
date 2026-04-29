from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass 
class TraceContext: 
    """Lightweight trace container for ingestion/query flows."""

    trace_type: str = "ingestion" # Default trace type is "ingestion", but it can be set to "query" or other types as needed.
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4())) # Generate a unique trace ID using UUID4 for each trace context instance.
    started_at: float = field(default_factory=time.perf_counter)
    stages: List[Dict[str, Any]] = field(default_factory=list)
    finished_at: Optional[float] = None

    def record_stage(self, name: str, **data: Any) -> None:
        """Record a stage in the trace with elapsed time calculation."""
        stage_entry = {"name": name, **data}
        # Auto-calculate elapsed_ms if not provided
        if "elapsed_ms" not in stage_entry and "started_at" in stage_entry:
            if "finished_at" in stage_entry:
                stage_entry["elapsed_ms"] = (stage_entry["finished_at"] - stage_entry["started_at"]) * 1000
        self.stages.append(stage_entry)

    def finish(self) -> None:
        """Mark trace as finished and capture end timestamp."""
        if self.finished_at is None:
            self.finished_at = time.perf_counter()

    def elapsed_ms(self, stage_name: Optional[str] = None) -> float:
        """Get elapsed time in milliseconds for a specific stage or total elapsed time.
        
        Args:
            stage_name: Optional stage name. If provided, returns elapsed time for that stage.
                       If None, returns total elapsed time.
        
        Returns:
            Elapsed time in milliseconds.
        """
        if stage_name is not None:
            # Find the stage and return its elapsed_ms
            for stage in self.stages:
                if stage.get("name") == stage_name:
                    return stage.get("elapsed_ms", 0.0)
            return 0.0
        else:
            # Return total elapsed time
            end = self.finished_at if self.finished_at is not None else time.perf_counter()
            return (end - self.started_at) * 1000

    @property
    def total_latency_ms(self) -> float: # Returns total 延迟latency in milliseconds
        end = self.finished_at if self.finished_at is not None else time.perf_counter()
        return (end - self.started_at) * 1000

    def to_dict(self) -> Dict[str, Any]:
        """Serialize trace context to a dictionary suitable for JSON encoding."""
        return {
            "trace_id": self.trace_id,
            "trace_type": self.trace_type,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_elapsed_ms": self.total_latency_ms,
            "stages": self.stages,
        }
