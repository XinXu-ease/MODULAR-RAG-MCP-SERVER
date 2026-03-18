import os

from src.libs.vector_store.vector_store_factory import create_vector_store
from src.libs.vector_store.base import BaseVectorStore


def test_create_vector_store_is_base(tmp_path):
    # override settings to use a temporary directory
    os.environ["SETTING_VECTOR_STORE_PERSIST_DIRECTORY"] = str(tmp_path)
    store = create_vector_store()
    assert isinstance(store, BaseVectorStore)
    # test add and query minimal functionality
    store.add(embeddings=[[0.1, 0.2]], metadatas=[{"foo": "bar"}], ids=["id1"])
    results = store.query([0.1, 0.2], top_k=1)
    assert isinstance(results, list)
    assert results[0]["id"] == "id1"
