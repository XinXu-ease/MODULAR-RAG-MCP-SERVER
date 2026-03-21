import hashlib

import pytest

from src.ingestion.loaders.pdf_loader import PDFLoader

"""These tests focus on the PDFLoader's ability to load and parse PDF documents, # as well as its validation logic for accepting only PDF sources. 
 The tests use a dummy parser function that simulates extracting structured content from a PDF file, 
 allowing us to verify that the loader correctly populates the Document metadata and text fields based on the parser's output. 
 Additionally, we test that the loader raises an error when given a non-PDF source, 
 ensuring that it enforces the expected input format."""

def test_pdf_loader_loads_document(tmp_path): 
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test payload")

    loader = PDFLoader(
        parser=lambda source: "# Brew Guide\n\n<!-- Page 1 -->\n\nText\n\n![img](figure.png)"
    )
    document = loader.load(str(pdf_path))

    assert document.metadata["doc_type"] == "pdf"
    assert document.metadata["source"] == str(pdf_path)
    assert document.metadata["title"] == "Brew Guide"
    assert document.metadata["page_count"] == 1
    assert document.metadata["images"] == ["figure.png"]
    assert document.id.startswith("pdf_")
    assert document.metadata["source_hash"] == hashlib.sha256(pdf_path.read_bytes()).hexdigest()


def test_pdf_loader_rejects_invalid_source(tmp_path):
    txt_path = tmp_path / "not_a_pdf.txt"
    txt_path.write_text("hello", encoding="utf-8")

    loader = PDFLoader(parser=lambda source: "ignored")
    with pytest.raises(ValueError):
        loader.load(str(txt_path))
