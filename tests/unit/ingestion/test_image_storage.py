from pathlib import Path

from src.ingestion.storage.image_storage import ImageStorage


def test_image_storage_persist_and_lookup(tmp_path):
    storage = ImageStorage(
        image_root=str(tmp_path / "images"),
        db_path=str(tmp_path / "db" / "image_index.db"),
    )

    image_id = storage.save_image(
        image_bytes=b"abc123",
        collection="test",
        doc_hash="doc-hash",
        page_num=1,
        extension=".png",
    )

    path = storage.get_path(image_id)
    assert path is not None
    assert Path(path).exists()

    rows = storage.list_images(collection="test", doc_hash="doc-hash")
    assert len(rows) == 1
    assert rows[0]["image_id"] == image_id
