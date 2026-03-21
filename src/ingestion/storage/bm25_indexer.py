from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Dict, List


class BM25Indexer:
    token_pattern = re.compile(r"\b\w+\b", flags=re.UNICODE)

    def __init__(self, index_dir: str = "data/db/bm25"):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.index_dir / "index.json"
        self.index: Dict[str, Dict[str, object]] = {}
        self.doc_lengths: Dict[str, float] = {}

    def build(self, sparse_vectors: Dict[str, Dict[str, float]], rebuild: bool = True) -> None:
        if rebuild:
            self.index = {}
            self.doc_lengths = {}

        doc_count = len(sparse_vectors)
        if doc_count == 0:
            self.persist()
            return

        df: Dict[str, int] = {}
        for chunk_id, weights in sparse_vectors.items():
            self.doc_lengths[chunk_id] = float(sum(weights.values())) or 1.0
            for term in weights:
                df[term] = df.get(term, 0) + 1

        for term, freq in df.items():
            idf = math.log((doc_count - freq + 0.5) / (freq + 0.5) + 1)
            postings = []
            for chunk_id, weights in sparse_vectors.items():
                tf = weights.get(term)
                if tf is None:
                    continue
                postings.append(
                    {
                        "chunk_id": chunk_id,
                        "tf": tf,
                        "doc_length": self.doc_lengths.get(chunk_id, 1.0),
                    }
                )
            self.index[term] = {"idf": idf, "postings": postings}

        self.persist()

    def query(self, query_text: str, top_k: int = 5) -> List[str]:
        tokens = [t.lower() for t in self.token_pattern.findall(query_text)]
        if not tokens:
            return []

        k1 = 1.5
        b = 0.75
        avg_dl = sum(self.doc_lengths.values()) / max(len(self.doc_lengths), 1)
        scores: Dict[str, float] = {}

        for term in tokens:
            term_info = self.index.get(term)
            if not term_info:
                continue
            idf = float(term_info.get("idf", 0.0))
            postings = term_info.get("postings", [])
            for posting in postings:
                chunk_id = posting["chunk_id"]
                tf = float(posting["tf"])
                dl = float(posting.get("doc_length", 1.0))
                denom = tf + k1 * (1 - b + b * (dl / max(avg_dl, 1e-9)))
                score = idf * ((tf * (k1 + 1)) / max(denom, 1e-9))
                scores[chunk_id] = scores.get(chunk_id, 0.0) + score

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        return [chunk_id for chunk_id, _ in ranked[:top_k]]

    def persist(self) -> None:
        payload = {"index": self.index, "doc_lengths": self.doc_lengths}
        self.index_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def load(self) -> None:
        if not self.index_path.exists():
            self.index = {}
            self.doc_lengths = {}
            return
        payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        self.index = payload.get("index", {})
        self.doc_lengths = payload.get("doc_lengths", {})
