from src.core.query_engine.query_processor import QueryProcessor


def test_query_processor_extracts_keywords_and_filters():
    processor = QueryProcessor()
    processed = processor.process(
        "What is hybrid retrieval in the RAG system?",
        filters={"collection": "spec", "doc_type": "pdf", "unused": None},
    )

    assert processed.normalized_query == "What is hybrid retrieval in the RAG system?"
    assert "hybrid" in processed.keywords
    assert "retrieval" in processed.keywords
    assert processed.filters == {"collection": "spec", "doc_type": "pdf"}


def test_query_processor_empty_query_is_stable():
    processor = QueryProcessor()
    processed = processor.process("   ", filters=None)

    assert processed.normalized_query == ""
    assert processed.keywords == []
    assert processed.filters == {}
