"""Unit tests for JSON Lines logging functionality."""

import json
import logging
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

import pytest

from src.observability.logger import (
    JSONFormatter,
    get_trace_logger,
    write_trace,
    get_trace_logger_singleton,
)


@pytest.fixture(autouse=True)
def cleanup_loggers():
    """Clean up all loggers after each test."""
    yield
    # Get all loggers and remove their handlers
    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(logger_name)
        for handler in logger.handlers[:]:
            handler.flush()
            handler.close()
            logger.removeHandler(handler)


class TestJSONFormatter:
    """Test suite for JSONFormatter class."""

    def test_format_basic_record(self):
        """Test formatting a basic log record."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        data = json.loads(result)
        
        assert data["level"] == "INFO"
        assert data["logger"] == "test_logger"
        assert data["message"] == "Test message"
        assert "timestamp" in data

    def test_format_with_trace_extra(self):
        """Test formatting a record with trace in extra fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        # Simulate extra fields
        record.trace = {"trace_id": "abc123", "duration": 1.5}
        
        result = formatter.format(record)
        data = json.loads(result)
        
        assert "trace" in data
        assert data["trace"]["trace_id"] == "abc123"

    def test_format_with_exception(self):
        """Test formatting a record with exception info."""
        formatter = JSONFormatter()
        try:
            raise ValueError("Test error")
        except ValueError:
            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=True,
            )
            import sys
            record.exc_info = sys.exc_info()
            
            result = formatter.format(record)
            data = json.loads(result)
            
            assert data["level"] == "ERROR"
            assert "exception" in data

    def test_format_json_serializable(self):
        """Test that formatted output is valid JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=5,
            msg="Debug message with args: %s",
            args=("value",),
            exc_info=None,
        )
        result = formatter.format(record)
        
        # Should be valid JSON
        data = json.loads(result)
        assert isinstance(data, dict)


class TestGetTraceLogger:
    """Test suite for get_trace_logger function."""

    def test_get_trace_logger_creates_logger(self):
        """Test that get_trace_logger creates a logger with JSON handler."""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.jsonl"
            logger = get_trace_logger(
                name="test_trace_logger_unique_1",
                output_path=str(output_path),
            )
            
            assert logger is not None
            assert logger.name == "test_trace_logger_unique_1"
            assert len(logger.handlers) > 0
            
            # Close handlers before deleting temp directory
            for handler in logger.handlers[:]:
                handler.flush()
                handler.close()
                logger.removeHandler(handler)

    def test_get_trace_logger_with_default_path(self):
        """Test that get_trace_logger uses default path."""
        logger = get_trace_logger(name="default_test_logger_unique")
        assert logger is not None
        # Should have created handlers
        assert len(logger.handlers) > 0

    def test_get_trace_logger_idempotent(self):
        """Test that calling get_trace_logger twice returns same logger."""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.jsonl"
            logger1 = get_trace_logger(
                name="idempotent_test_unique",
                output_path=str(output_path),
            )
            logger2 = get_trace_logger(
                name="idempotent_test_unique",
                output_path=str(output_path),
            )
            
            # Same instance
            assert logger1 is logger2
            
            # Close handlers before deleting temp directory
            for handler in logger1.handlers[:]:
                handler.flush()
                handler.close()
                logger1.removeHandler(handler)

    def test_get_trace_logger_writes_json(self):
        """Test that trace logger writes valid JSON lines."""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.jsonl"
            logger = get_trace_logger(
                name="json_write_test_unique",
                output_path=str(output_path),
            )
            
            # Log a message with trace data
            logger.info("Test trace", extra={"trace": {"id": "123"}})
            
            # Close handlers before reading
            for handler in logger.handlers[:]:
                handler.flush()
                handler.close()
            
            # Verify file contains valid JSON
            lines = output_path.read_text().strip().split("\n")
            assert len(lines) > 0
            
            data = json.loads(lines[0])
            assert data["message"] == "Test trace"
            assert data["trace"]["id"] == "123"
            
            # Remove handlers
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)


class TestWriteTrace:
    """Test suite for write_trace function."""

    def test_write_trace_creates_file(self):
        """Test that write_trace creates the output file."""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "traces.jsonl"
            trace_dict = {
                "trace_id": "test123",
                "trace_type": "query",
                "elapsed_ms": 100.5,
            }
            write_trace(trace_dict, output_path=str(output_path))
            
            assert output_path.exists()

    def test_write_trace_json_format(self):
        """Test that write_trace outputs valid JSON."""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "traces.jsonl"
            trace_dict = {
                "trace_id": "abc123",
                "trace_type": "ingestion",
                "stages": ["load", "split"],
                "elapsed_ms": 50.0,
            }
            write_trace(trace_dict, output_path=str(output_path))
            
            line = output_path.read_text().strip()
            data = json.loads(line)
            
            assert data["trace_id"] == "abc123"
            assert data["trace_type"] == "ingestion"

    def test_write_trace_appends(self):
        """Test that write_trace appends to existing file."""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "traces.jsonl"
            
            trace1 = {"trace_id": "1", "type": "query"}
            trace2 = {"trace_id": "2", "type": "ingestion"}
            
            write_trace(trace1, output_path=str(output_path))
            write_trace(trace2, output_path=str(output_path))
            
            lines = output_path.read_text().strip().split("\n")
            assert len(lines) == 2
            
            data1 = json.loads(lines[0])
            data2 = json.loads(lines[1])
            assert data1["trace_id"] == "1"
            assert data2["trace_id"] == "2"

    def test_write_trace_default_path(self):
        """Test that write_trace uses default path when not provided."""
        trace_dict = {"trace_id": "test", "type": "query"}
        
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.write = MagicMock()
            # Mock Path.mkdir to avoid creating real directories
            with patch("pathlib.Path.mkdir"):
                write_trace(trace_dict)
                # Should not raise

    def test_write_trace_creates_parent_dirs(self):
        """Test that write_trace creates parent directories."""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "deep" / "nested" / "traces.jsonl"
            trace_dict = {"trace_id": "test"}
            
            write_trace(trace_dict, output_path=str(output_path))
            
            assert output_path.exists()
            assert output_path.parent.exists()

    def test_write_trace_handles_unicode(self):
        """Test that write_trace handles Unicode characters."""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "traces.jsonl"
            trace_dict = {
                "trace_id": "test",
                "message": "测试中文 テスト 🎉",
            }
            write_trace(trace_dict, output_path=str(output_path))
            
            line = output_path.read_text(encoding="utf-8").strip()
            data = json.loads(line)
            assert "测试中文" in data["message"]


class TestTraceLoggerSingleton:
    """Test suite for get_trace_logger_singleton function."""

    def test_singleton_pattern(self):
        """Test that singleton returns same instance."""
        # Reset global state by deleting the module
        import sys
        import importlib
        
        # Get two instances
        logger1 = get_trace_logger_singleton()
        logger2 = get_trace_logger_singleton()
        
        assert logger1 is logger2

    def test_singleton_with_path_first_call(self):
        """Test that output_path only affects first call."""
        with TemporaryDirectory() as tmpdir:
            output_path1 = Path(tmpdir) / "first.jsonl"
            # Reset by creating a new logger with unique name
            logger = get_trace_logger_singleton(output_path=str(output_path1))
            assert logger is not None


class TestIntegration:
    """Integration tests combining logger and formatter."""

    def test_end_to_end_trace_logging(self):
        """Test complete trace logging workflow."""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "e2e_test.jsonl"
            
            # Create logger
            logger = get_trace_logger(
                name="e2e_test_logger_unique",
                output_path=str(output_path),
            )
            
            # Log trace data
            trace_data = {
                "trace_id": "e2e_test_123",
                "trace_type": "query",
                "elapsed_ms": 250.5,
                "stages": [
                    {"name": "retrieval", "elapsed_ms": 150},
                    {"name": "rerank", "elapsed_ms": 100.5},
                ],
            }
            logger.info("Trace completed", extra={"trace": trace_data})
            
            # Close handlers before reading
            for handler in logger.handlers[:]:
                handler.flush()
                handler.close()
            
            # Verify file content
            lines = output_path.read_text().strip().split("\n")
            data = json.loads(lines[0])
            
            assert data["trace"]["trace_type"] == "query"
            assert data["trace"]["elapsed_ms"] == 250.5
            
            # Remove handlers
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)

    def test_multiple_traces_workflow(self):
        """Test writing multiple traces."""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "multiple.jsonl"
            
            # Write multiple traces directly
            for i in range(5):
                trace_dict = {
                    "trace_id": f"trace_{i}",
                    "trace_type": "query" if i % 2 == 0 else "ingestion",
                    "elapsed_ms": 50.0 * (i + 1),
                }
                write_trace(trace_dict, output_path=str(output_path))
            
            # Verify all traces were written
            lines = output_path.read_text().strip().split("\n")
            assert len(lines) == 5
            
            # Verify content
            for i, line in enumerate(lines):
                data = json.loads(line)
                assert data["trace_id"] == f"trace_{i}"
