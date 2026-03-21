#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.pipeline import IngestionPipeline


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ingestion pipeline for files/URLs.")
    parser.add_argument("--path", required=True, help="Path to a PDF file, directory, or URL")
    parser.add_argument("--collection", default="default", help="Target collection name")
    parser.add_argument("--force", action="store_true", help="Force re-ingestion even if unchanged")
    return parser.parse_args(argv)


def iter_sources(path_arg: str):
    if path_arg.startswith("http://") or path_arg.startswith("https://"):
        yield path_arg
        return

    path = Path(path_arg)
    if path.is_file():
        yield str(path)
        return

    if path.is_dir():
        for pdf in sorted(path.rglob("*.pdf")):
            yield str(pdf)
        return

    raise FileNotFoundError(f"Path not found: {path_arg}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    pipeline = IngestionPipeline()

    success = True
    for source in iter_sources(args.path):
        result = pipeline.run(source=source, collection=args.collection, force=args.force)
        if result.success:
            print(f"OK  {source} chunks={result.metrics.total_chunks} skipped={result.metrics.skipped_chunks}")
        else:
            success = False
            print(f"ERR {source} error={result.error}")

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
