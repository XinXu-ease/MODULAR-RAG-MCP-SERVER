#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.query_engine import HybridSearch


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query the local knowledge base.")
    parser.add_argument("--query", required=True, help="Natural-language query text")
    parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to return")
    parser.add_argument("--no-rerank", action="store_true", help="Skip reranker stage")
    parser.add_argument("--verbose", action="store_true", help="Print stage latencies")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    engine = HybridSearch()
    result = engine.search(
        query=args.query,
        top_k=args.top_k,
        use_rerank=not args.no_rerank,
    )

    for idx, chunk in enumerate(result.retrieved_chunks, start=1):
        source = chunk.metadata.get("source", "unknown")
        print(f"[{idx}] score={chunk.score:.4f} source={source}")
        print(chunk.content.strip())
        print()

    if args.verbose:
        print(f"trace_id={result.trace_id}")
        for name, latency_ms in result.stage_latencies.items():
            print(f"{name}={latency_ms:.2f}ms")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
