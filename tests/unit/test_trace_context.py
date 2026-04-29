"""Unit tests for TraceContext and TraceCollector."""

import json
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pytest

from src.core.trace.trace_context import TraceContext
from src.core.trace.trace_collector import TraceCollector, get_trace_collector


class TestTraceContext:
    """Test suite for TraceContext class."""

    def test_initialization_default(self):
        """Test TraceContext initialization with default values."""
        trace = TraceContext()
        assert trace.trace_type == "ingestion"
        assert trace.trace_id  # Should have a UUID
        assert trace.started_at  # Should have a timestamp
        assert trace.stages == []
        assert trace.finished_at is None

    def test_initialization_query_type(self):
        """Test TraceContext initialization with query trace type."""
        trace = TraceContext(trace_type="query")
        assert trace.trace_type == "query"
        assert trace.trace_id  # Should have a UUID

    def test_record_stage_basic(self):
        """Test recording a basic stage."""
        trace = TraceContext()
        trace.record_stage("preprocessing", method="simple")
        assert len(trace.stages) == 1
        assert trace.stages[0]["name"] == "preprocessing"
        assert trace.stages[0]["method"] == "simple"

    def test_record_multiple_stages(self):
        """Test recording multiple stages."""
        trace = TraceContext()
        trace.record_stage("load", count=10)
        trace.record_stage("split", chunks=50)
        trace.record_stage("embed", vectors=500)
        assert len(trace.stages) == 3
        assert trace.stages[0]["name"] == "load"
        assert trace.stages[1]["name"] == "split"
        assert trace.stages[2]["name"] == "embed"

    def test_record_stage_with_elapsed_ms(self):
        """Test recording stage with elapsed_ms calculation."""
        trace = TraceContext()
        start = time.perf_counter()
        time.sleep(0.01)
        end = time.perf_counter()
        
        trace.record_stage("processing", started_at=start, finished_at=end)
        stage = trace.stages[0]
        assert "elapsed_ms" in stage
        # Verify elapsed_ms is calculated correctly
        assert stage["elapsed_ms"] > 0  # Should have positive time
        assert stage["elapsed_ms"] <= 1000  # Reasonable upper bound

    def test_finish_sets_timestamp(self):
        """Test that finish() sets the finished_at timestamp."""
        trace = TraceContext()
        assert trace.finished_at is None
        trace.finish()
        assert trace.finished_at is not None

    def test_finish_idempotent(self):
        """Test that finish() is idempotent."""
        trace = TraceContext()
        trace.finish()
        first_finish = trace.finished_at
        time.sleep(0.01)
        trace.finish()  # Should not change finished_at
        assert trace.finished_at == first_finish

    def test_elapsed_ms_total(self):
        """Test getting total elapsed time."""
        trace = TraceContext()
        time.sleep(0.01)
        trace.finish()
        elapsed = trace.elapsed_ms()
        assert elapsed >= 8  # At least ~8ms (accounting for timing variations)

    def test_elapsed_ms_specific_stage(self):
        """Test getting elapsed time for a specific stage."""
        trace = TraceContext()
        start = time.perf_counter()
        time.sleep(0.01)
        end = time.perf_counter()
        
        trace.record_stage("query", started_at=start, finished_at=end)
        elapsed = trace.elapsed_ms("query")
        assert elapsed >= 8  # At least ~8ms (accounting for timing variations)

    def test_elapsed_ms_nonexistent_stage(self):
        """Test getting elapsed time for a stage that doesn't exist."""
        trace = TraceContext()
        trace.record_stage("load", elapsed_ms=5.0)
        elapsed = trace.elapsed_ms("nonexistent")
        assert elapsed == 0.0

    def test_total_latency_ms_property(self):
        """Test total_latency_ms property."""
        trace = TraceContext()
        time.sleep(0.01)
        trace.finish()
        latency = trace.total_latency_ms
        assert latency >= 8  # At least ~8ms (accounting for timing variations)

    def test_to_dict_contains_required_fields(self):
        """Test that to_dict() returns all required fields."""
        trace = TraceContext(trace_type="query")
        trace.record_stage("search", count=100)
        trace.finish()
        
        result = trace.to_dict()
        assert "trace_id" in result
        assert "trace_type" in result
        assert "started_at" in result
        assert "finished_at" in result
        assert "total_elapsed_ms" in result
        assert "stages" in result
        
        assert result["trace_type"] == "query"
        assert result["trace_id"] == trace.trace_id
        assert len(result["stages"]) == 1

    def test_to_dict_json_serializable(self):
        """Test that to_dict() output is JSON serializable."""
        trace = TraceContext()
        trace.record_stage("process", status="success", details={"items": 42})
        trace.finish()
        
        result = trace.to_dict()
        json_str = json.dumps(result)  # Should not raise
        assert json_str

    def test_unique_trace_ids(self):
        """Test that each TraceContext gets a unique trace_id."""
        trace1 = TraceContext()
        trace2 = TraceContext()
        assert trace1.trace_id != trace2.trace_id


class TestTraceCollector:
    """Test suite for TraceCollector class."""

    def test_initialization_with_path(self):
        """Test TraceCollector initialization with output path."""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "traces.jsonl"
            collector = TraceCollector(output_path=str(output_path))
            assert collector.output_path == output_path

    def test_initialization_without_path(self):
        """Test TraceCollector initialization without output path."""
        collector = TraceCollector(output_path=None)
        assert collector.output_path is None

    def test_collect_writes_to_file(self):
        """Test that collect() writes trace to file."""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "traces.jsonl"
            collector = TraceCollector(output_path=str(output_path))
            
            trace = TraceContext(trace_type="query")
            trace.record_stage("search", count=100)
            collector.collect(trace)
            
            # Verify file was created and contains JSON
            assert output_path.exists()
            with open(output_path) as f:
                line = f.readline()
                data = json.loads(line)
                assert data["trace_type"] == "query"
                assert len(data["stages"]) == 1

    def test_collect_multiple_traces(self):
        """Test collecting multiple traces to the same file."""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "traces.jsonl"
            collector = TraceCollector(output_path=str(output_path))
            
            for i in range(3):
                trace = TraceContext(trace_type="query" if i % 2 == 0 else "ingestion")
                trace.record_stage(f"stage_{i}", index=i)
                collector.collect(trace)
            
            # Verify all traces were written
            lines = output_path.read_text().strip().split("\n")
            assert len(lines) == 3
            
            for i, line in enumerate(lines):
                data = json.loads(line)
                expected_type = "query" if i % 2 == 0 else "ingestion"
                assert data["trace_type"] == expected_type

    def test_collect_calls_finish_if_needed(self):
        """Test that collect() finishes the trace if not already finished."""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "traces.jsonl"
            collector = TraceCollector(output_path=str(output_path))
            
            trace = TraceContext()
            assert trace.finished_at is None
            
            collector.collect(trace)
            
            assert trace.finished_at is not None

    def test_collect_without_file_path(self, caplog):
        """Test collecting trace without file path (logging only)."""
        collector = TraceCollector(output_path=None)
        trace = TraceContext(trace_type="query")
        trace.record_stage("test", status="ok")
        
        with caplog.at_level("INFO"):
            collector.collect(trace)
        
        # Should log without raising an error
        assert "Trace collected" in caplog.text or len(caplog.records) > 0

    @patch("src.core.trace.trace_collector.logger")
    def test_collect_logs_trace(self, mock_logger):
        """Test that collect() logs the trace."""
        collector = TraceCollector(output_path=None)
        trace = TraceContext(trace_type="ingestion")
        trace.record_stage("load")
        
        collector.collect(trace)
        
        # Verify logging was called
        assert mock_logger.info.called
        # Check that logger.info was called with trace in the extra dict
        call_args = mock_logger.info.call_args
        if call_args[1]:  # kwargs
            assert "extra" in call_args[1]
            assert "trace" in call_args[1]["extra"]

    def test_collect_handles_write_error(self, caplog):
        """Test that collect() handles file write errors gracefully."""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "traces.jsonl"
            collector = TraceCollector(output_path=str(output_path))
            trace = TraceContext()
            
            # Patch _write_to_file to raise an exception
            original_write = collector._write_to_file
            def raise_error(*args, **kwargs):
                raise Exception("Write failed")
            
            collector._write_to_file = raise_error
            
            with caplog.at_level("ERROR"):
                # Should not raise - errors are caught and logged
                collector.collect(trace)
                # Verify error was logged
                assert any("Failed to write trace" in record.message for record in caplog.records)


class TestTraceCollectorGlobal:
    """Test suite for global trace collector functions."""

    def test_get_trace_collector_singleton(self):
        """Test that get_trace_collector returns the same instance."""
        # Reset global state
        import src.core.trace.trace_collector as tc
        tc._trace_collector = None
        
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "traces.jsonl"
            collector1 = get_trace_collector(output_path=str(output_path))
            collector2 = get_trace_collector()
            
            assert collector1 is collector2

    def test_get_trace_collector_default_path(self):
        """Test that get_trace_collector uses default path."""
        # Reset global state
        import src.core.trace.trace_collector as tc
        tc._trace_collector = None
        
        collector = get_trace_collector()
        assert collector.output_path == Path("data/logs/traces.jsonl")


class TestTraceContextIntegration:
    """Integration tests for TraceContext."""

    def test_query_trace_workflow(self):
        """Test a typical query trace workflow."""
        trace = TraceContext(trace_type="query")
        
        # Simulate query workflow
        trace.record_stage("query_processing", method="keyword_extraction", elapsed_ms=2.5)
        trace.record_stage("dense_retrieval", method="vector_search", elapsed_ms=15.3, results=100)
        trace.record_stage("sparse_retrieval", method="bm25", elapsed_ms=8.2, results=50)
        trace.record_stage("fusion", method="rrf", elapsed_ms=1.2, final_results=75)
        trace.record_stage("rerank", method="cross_encoder", elapsed_ms=20.5, top_k=10)
        
        trace.finish()
        
        result = trace.to_dict()
        assert result["trace_type"] == "query"
        assert len(result["stages"]) == 5
        assert result["finished_at"] is not None
        assert result["total_elapsed_ms"] > 0

    def test_ingestion_trace_workflow(self):
        """Test a typical ingestion trace workflow."""
        trace = TraceContext(trace_type="ingestion")
        
        # Simulate ingestion workflow
        trace.record_stage("load", method="pdf", elapsed_ms=50.0, documents=5)
        trace.record_stage("split", method="recursive", elapsed_ms=120.0, chunks=250)
        trace.record_stage("transform", method="metadata_enrichment", elapsed_ms=80.0, enriched=250)
        trace.record_stage("embed", method="azure_openai", elapsed_ms=400.0, vectors=250)
        trace.record_stage("upsert", method="chroma", elapsed_ms=50.0, upserted=250)
        
        trace.finish()
        
        result = trace.to_dict()
        assert result["trace_type"] == "ingestion"
        assert len(result["stages"]) == 5
        assert result["total_elapsed_ms"] > 0


class TestTraceContextWithCollectorIntegration:
    """Integration tests combining TraceContext and TraceCollector."""

    def test_end_to_end_collection(self):
        """Test end-to-end trace collection workflow."""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "traces.jsonl"
            collector = TraceCollector(output_path=str(output_path))
            
            # Create multiple traces
            for trace_type in ["query", "ingestion"]:
                trace = TraceContext(trace_type=trace_type)
                for i in range(3):
                    trace.record_stage(f"stage_{i}", elapsed_ms=float(i * 10))
                collector.collect(trace)
            
            # Verify all traces persisted
            lines = output_path.read_text().strip().split("\n")
            assert len(lines) == 2
            
            trace_types = [json.loads(line)["trace_type"] for line in lines]
            assert "query" in trace_types
            assert "ingestion" in trace_types
