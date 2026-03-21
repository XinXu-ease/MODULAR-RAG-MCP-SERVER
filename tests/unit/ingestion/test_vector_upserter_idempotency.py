from src.core.types import Chunk
from src.ingestion.storage.vector_upserter import VectorUpserter


class DummyStore:
    def __init__(self):
        self.calls = []

    def add(self, embeddings, metadatas, ids=None, documents=None):
        return None

    def upsert(self, embeddings, metadatas, ids, documents=None):
        self.calls.append((list(ids), list(embeddings), list(metadatas), list(documents or [])))

    def query(self, query_embedding, top_k=10):
        return []


def _chunk(content: str) -> Chunk:
    return Chunk(id="cid", content=content, source="doc.pdf", chunk_index=0, metadata={"source": "doc.pdf"})


def test_vector_upserter_idempotent_id():
    store = DummyStore()
    upserter = VectorUpserter(vector_store=store)

    chunk = _chunk("same content")
    ids1 = upserter.upsert([chunk], {"cid": [0.1, 0.2]})
    ids2 = upserter.upsert([chunk], {"cid": [0.1, 0.2]})
    assert ids1 == ids2


def test_vector_upserter_id_changes_on_content_change():
    store = DummyStore()
    upserter = VectorUpserter(vector_store=store)

    id1 = upserter.upsert([_chunk("a")], {"cid": [0.1, 0.2]})[0]
    id2 = upserter.upsert([_chunk("b")], {"cid": [0.1, 0.2]})[0]
    assert id1 != id2
