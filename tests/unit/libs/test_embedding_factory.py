import pytest

from src.libs.embedding.embedding_factory import create_embedding
from src.libs.embedding.base import BaseEmbedding


def test_create_embedding_is_base():
    emb = create_embedding()
    assert isinstance(emb, BaseEmbedding)
    assert callable(emb.embed)


def test_embedding_mocked(mocker):
    emb = create_embedding()
    import openai
    from types import SimpleNamespace

    mocker.patch.object(openai.Embedding, 'create', return_value=SimpleNamespace(data=[{"embedding": [0.1, 0.2]}]))
    vectors = emb.embed(["a", "b"])
    assert vectors == [[0.1, 0.2]]
