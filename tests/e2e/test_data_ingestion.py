from scripts import ingest


class DummyPipeline:
    def run(self, source: str, collection: str, force: bool):
        class Result:
            success = True
            error = None

            class Metrics:
                total_chunks = 1
                skipped_chunks = 0

            metrics = Metrics()

        return Result()


def test_ingest_main_single_file(monkeypatch, tmp_path):
    f = tmp_path / "a.pdf"
    f.write_bytes(b"%PDF")

    monkeypatch.setattr(ingest, "IngestionPipeline", lambda: DummyPipeline())
    rc = ingest.main(["--path", str(f), "--collection", "test"])
    assert rc == 0
