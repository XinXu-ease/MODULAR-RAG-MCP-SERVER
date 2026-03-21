from src.ingestion.loaders import BaseLoader, PDFLoader, WebLoader, create_loader


def test_create_pdf_loader_is_base_loader():
    loader = create_loader("pdf")
    assert isinstance(loader, BaseLoader)
    assert isinstance(loader, PDFLoader)


def test_create_web_loader_is_base_loader():
    loader = create_loader("web")
    assert isinstance(loader, BaseLoader)
    assert isinstance(loader, WebLoader)
