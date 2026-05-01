"""Structured JSON Lines logging for traces and system events."""

from __future__ import annotations

import json
import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Any, Dict


class JSONFormatter(logging.Formatter):
    """Custom logging formatter that outputs JSON Lines format.
    
    Each log record is formatted as a single JSON object per line,
    making it suitable for streaming and machine parsing.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON object.
        
        Args:
            record: The log record to format.
            
        Returns:
            A JSON string representation of the log record.
        """
        log_data: Dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "timestamp": record.created,
        }
        
        # Add extra fields if present
        if hasattr(record, "trace"):
            log_data["trace"] = record.trace
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add custom attributes
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName", "relativeCreated",
                "thread", "threadName", "exc_info", "exc_text", "stack_info",
                "trace"
            ]:
                log_data[key] = value
        
        return json.dumps(log_data, ensure_ascii=False)


def get_trace_logger(
    name: str = "trace_logger",
    output_path: Optional[str] = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """Get or create a logger configured for JSON Lines trace output.
    
    Args:
        name: Logger name. Defaults to "trace_logger".
        output_path: Path to write trace logs. If None, defaults to "data/logs/traces.jsonl".
        level: Logging level. Defaults to INFO.
        
    Returns:
        A configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured (avoid duplicate handlers)
    if not logger.handlers:
        logger.setLevel(level)
        
        # Ensure output directory exists
        output_file = Path(output_path or "data/logs/traces.jsonl")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Add file handler with JSON formatting
        file_handler = logging.FileHandler(output_file, mode="a", encoding="utf-8")
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
        
        # Prevent propagation to avoid duplicate logs
        logger.propagate = False
    
    return logger


def write_trace(trace_dict: Dict[str, Any], output_path: Optional[str] = None) -> None:
    """Write a trace dictionary to JSON Lines file.
    
    Args:
        trace_dict: Trace data dictionary to write.
        output_path: Path to write trace file. Defaults to "data/logs/traces.jsonl".
        
    Raises:
        IOError: If writing to file fails.
    """
    output_file = Path(output_path or "data/logs/traces.jsonl")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(output_file, "a", encoding="utf-8") as f:
            json.dump(trace_dict, f, ensure_ascii=False)
            f.write("\n")
    except Exception as e:
        raise IOError(f"Failed to write trace to {output_file}: {e}") from e


# Global trace logger instance
_trace_logger: Optional[logging.Logger] = None


def get_trace_logger_singleton(output_path: Optional[str] = None) -> logging.Logger:
    """Get or create global trace logger instance (singleton pattern).
    
    Args:
        output_path: Path for trace output file. Used only on first call.
        
    Returns:
        Global trace logger instance.
    """
    global _trace_logger
    if _trace_logger is None:
        _trace_logger = get_trace_logger(
            name="trace_logger_global",
            output_path=output_path or "data/logs/traces.jsonl"
        )
    return _trace_logger
