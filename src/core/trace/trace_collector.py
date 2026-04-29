"""Trace collector for persistence and processing."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from src.core.trace.trace_context import TraceContext


logger = logging.getLogger(__name__)


class TraceCollector:
    """Collects and persists trace data."""

    def __init__(self, output_path: Optional[str] = None):
        """Initialize trace collector.
        
        Args:
            output_path: Path to write trace JSON Lines. If None, traces are only logged.
        """
        self.output_path = Path(output_path) if output_path else None
        if self.output_path:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def collect(self, trace: TraceContext) -> None:
        """Collect and persist a trace.
        
        Args:
            trace: TraceContext instance to collect and persist.
        """
        if trace.finished_at is None:
            trace.finish()
        
        trace_dict = trace.to_dict()
        
        # Persist to file if output_path is set
        if self.output_path:
            try:
                self._write_to_file(trace_dict)
            except Exception as e:
                logger.error(f"Failed to write trace to {self.output_path}: {e}")
        
        # Always log the trace
        logger.info(f"Trace collected: {trace.trace_type}", extra={"trace": trace_dict})

    def _write_to_file(self, trace_dict: dict) -> None:
        """Write trace to JSON Lines file.
        
        Args:
            trace_dict: Trace dictionary to write.
        """
        try:
            with open(self.output_path, "a") as f:
                json.dump(trace_dict, f, ensure_ascii=False)
                f.write("\n")
        except Exception as e:
            logger.error(f"Failed to write trace to {self.output_path}: {e}")


# Global trace collector instance
_trace_collector: Optional[TraceCollector] = None


def get_trace_collector(output_path: Optional[str] = None) -> TraceCollector:
    """Get or create global trace collector instance.
    
    Args:
        output_path: Path to write trace JSON Lines. Used only on first call.
    
    Returns:
        Global TraceCollector instance.
    """
    global _trace_collector
    if _trace_collector is None:
        _trace_collector = TraceCollector(output_path=output_path or "data/logs/traces.jsonl")
    return _trace_collector
