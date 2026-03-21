from src.core.types import Document
from src.ingestion.chunking import DocumentChunker


class FakeSplitter:
    def split(self, text: str):
        return ["chunk one", "chunk two"]


def test_document_chunker_contract():
    doc = Document(
        id="doc_1",
        text="chunk one\n\nchunk two",
        metadata={"source": "tests/sample.pdf", "doc_type": "pdf", "title": "Sample"},
    )
    chunker = DocumentChunker(splitter=FakeSplitter())

    chunks = chunker.split_document(doc)
    assert len(chunks) == 2
    assert chunks[0].id.startswith("doc_1_0000_")
    assert chunks[0].metadata["chunk_index"] == 0
    assert chunks[0].metadata["source_ref"] == "doc_1"
    assert chunks[1].metadata["title"] == "Sample"
