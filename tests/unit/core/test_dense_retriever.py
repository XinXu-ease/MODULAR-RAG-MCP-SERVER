from src.core.query_engine.dense_retriever import DenseRetriever


class DummyEmbedding:
    def __init__(self):
        self.calls = []

    def embed(self, texts, **kwargs):
        self.calls.append(list(texts))
        return [[0.1, 0.2, 0.3]]


class DummyVectorStore:
    def __init__(self):
        self.calls = []

    def add(self, embeddings, metadatas, ids=None, documents=None):
        return None

    def upsert(self, embeddings, metadatas, ids, documents=None):
        return None

    def query(self, query_embedding, top_k=10):
        self.calls.append((list(query_embedding), top_k))
        return [
            {"id": "c1", "distance": 0.2, "text": "dense text 1", "metadata": {"collection": "spec"}},
            {"id": "c2", "distance": 0.4, "text": "dense text 2", "metadata": {"collection": "other"}},
        ]

    def get_by_ids(self, ids):
        return []


def test_dense_retriever_calls_embedding_and_vector_store(sample_settings):
    emb = DummyEmbedding()
    store = DummyVectorStore()
    retriever = DenseRetriever(settings=sample_settings, embedding_client=emb, vector_store=store)

    results = retriever.retrieve("hybrid search", top_k=2)

    assert emb.calls == [["hybrid search"]]
    assert store.calls[0][1] == 2
    assert len(results) == 2
    assert results[0].chunk_id == "c1"
    assert results[0].content == "dense text 1"


def test_dense_retriever_respects_filters(sample_settings):
    retriever = DenseRetriever(
        settings=sample_settings,
        embedding_client=DummyEmbedding(),
        vector_store=DummyVectorStore(),
    )

    results = retriever.retrieve("hybrid search", top_k=2, filters={"collection": "spec"})

    assert len(results) == 1
    assert results[0].chunk_id == "c1"
