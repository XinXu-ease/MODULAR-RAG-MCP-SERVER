from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class TraceSummary:
    trace_id: str
    trace_type: str
    started_at: Any = None
    finished_at: Any = None
    total_elapsed_ms: float = 0.0
    stage_count: int = 0
    source: str = ""
    collection: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TraceService:
    """Read and summarize JSON Lines trace output."""

    def __init__(self, traces_path: Optional[str] = None):
        self.traces_path = Path(traces_path or "logs/traces.jsonl")

    def read_traces(self) -> List[Dict[str, Any]]:
        if not self.traces_path.exists():
            return []

        traces: List[Dict[str, Any]] = []
        for line in self.traces_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                traces.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return traces

    def list_traces(self, trace_type: Optional[str] = None) -> List[Dict[str, Any]]:
        traces = self.read_traces()
        if trace_type:
            traces = [trace for trace in traces if str(trace.get("trace_type")) == trace_type]
        traces.sort(key=lambda item: str(item.get("started_at", "")), reverse=True)
        return traces

    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        for trace in self.read_traces():
            if str(trace.get("trace_id")) == str(trace_id):
                return trace
        return None

    def summarize(self, trace_type: Optional[str] = None) -> Dict[str, Any]:
        traces = self.list_traces(trace_type)
        stage_count = 0
        total_latency = 0.0
        for trace in traces:
            stages = trace.get("stages") or []
            stage_count += len(stages)
            total_latency += float(trace.get("total_elapsed_ms") or trace.get("elapsed_ms") or 0.0)
        return {
            "trace_count": len(traces),
            "stage_count": stage_count,
            "total_latency_ms": total_latency,
        }

    def iter_summaries(self, trace_type: Optional[str] = None) -> Iterable[TraceSummary]:
        for trace in self.list_traces(trace_type):
            yield TraceSummary(
                trace_id=str(trace.get("trace_id", "")),
                trace_type=str(trace.get("trace_type", "")),
                started_at=trace.get("started_at"),
                finished_at=trace.get("finished_at"),
                total_elapsed_ms=float(trace.get("total_elapsed_ms") or trace.get("elapsed_ms") or 0.0),
                stage_count=len(trace.get("stages") or []),
                source=str(trace.get("source") or trace.get("source_path") or ""),
                collection=str(trace.get("collection") or ""),
            )
