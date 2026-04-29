"""Integration tests for multimodal response assembler."""

import base64
import os
import tempfile
from pathlib import Path

import pytest

from src.core.response.multimodal_assembler import MultimodalAssembler
from src.core.types import RetrievalResult


@pytest.fixture
def temp_image_dir():
    """Create temporary directory for test images."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_png_image():
    """Create a minimal PNG image for testing."""
    # Minimal valid PNG (1x1 red pixel)
    png_data = bytes.fromhex(
        "89504e470d0a1a0a0000000d494844520000000100000001"
        "0806000000001f15c4890000000a49444154785e63f80f00"
        "00010001015c77e90d0000000049454e44ae426082"
    )
    return png_data


@pytest.fixture
def sample_jpg_image():
    """Create a minimal JPEG image for testing."""
    # Minimal valid JPEG (1x1 pixel)
    jpg_data = bytes.fromhex(
        "ffd8ffe000104a46494600010100000100010000ffdb43"
        "00080606070605080707070909080a0c140d0c0b0b0c19"
        "12130f141d1a1f1e1d1a1c1c20242e2720222c231c1c28"
        "37292c30313434341f27393d38323c2e333432ffc00011"
        "080001000101011100021101031101ffc4001f00000105"
        "0101010101010100000000000000000102030405060708"
        "090a0bffc400b51000020102040403040705040404000002"
        "7d010203000411052122313141061371132232328108144"
        "2a191a1082342b1c11552d1f0249362728293c171a1091"
        "b2c1139141517273f02a282918191a25262728292a3435"
        "36373839393a434445464748494a535455565758595a63"
        "646566676869696a737475767778797a838485868788898"
        "a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6"
        "b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2"
        "e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffda000c03010"
        "002110311003f00f7fa28a2800a28a2800ffd9"
    )
    return jpg_data


class TestMultimodalAssembler:
    """Test MultimodalAssembler functionality."""

    def test_assembler_initializes(self, temp_image_dir):
        """Test that assembler initializes with custom image directory."""
        assembler = MultimodalAssembler(image_base_dir=temp_image_dir)
        assert assembler.image_base_dir == temp_image_dir

    def test_assembler_creates_image_dir(self):
        """Test that assembler creates image directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = os.path.join(tmpdir, "new_images")
            assert not os.path.exists(new_dir)

            MultimodalAssembler(image_base_dir=new_dir)
            assert os.path.exists(new_dir)

    def test_assemble_text_only(self):
        """Test assembling retrieval results with text only (no images)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assembler = MultimodalAssembler(image_base_dir=tmpdir)

            results = [
                RetrievalResult(
                    chunk_id="c1",
                    content="Sample text content",
                    metadata={"source": "test.txt"},
                    score=0.95,
                ),
                RetrievalResult(
                    chunk_id="c2",
                    content="Another text content",
                    metadata={"source": "test2.txt"},
                    score=0.88,
                ),
            ]

            content = assembler.assemble(results)

            assert len(content) == 2
            assert all(item["type"] == "text" for item in content)
            assert content[0]["text"] == "Sample text content"
            assert content[1]["text"] == "Another text content"

    def test_assemble_text_with_image(self, temp_image_dir, sample_png_image):
        """Test assembling text with associated image."""
        # Create a test image file
        image_path = os.path.join(temp_image_dir, "test_image.png")
        with open(image_path, "wb") as f:
            f.write(sample_png_image)

        assembler = MultimodalAssembler(image_base_dir=temp_image_dir)

        results = [
            RetrievalResult(
                chunk_id="c1",
                content="Text with image",
                metadata={"source": "test.txt"},
                score=0.95,
                image_refs=["test_image.png"],
            ),
        ]

        content = assembler.assemble(results)

        assert len(content) == 2
        assert content[0]["type"] == "text"
        assert content[0]["text"] == "Text with image"
        assert content[1]["type"] == "image"
        assert "data" in content[1]
        assert content[1]["mimeType"] == "image/png"

        # Verify base64 encoding
        decoded = base64.b64decode(content[1]["data"])
        assert decoded == sample_png_image

    def test_assemble_multiple_images_per_chunk(self, temp_image_dir, sample_png_image, sample_jpg_image):
        """Test assembling chunk with multiple images."""
        # Create test image files
        png_path = os.path.join(temp_image_dir, "test1.png")
        jpg_path = os.path.join(temp_image_dir, "test2.jpg")

        with open(png_path, "wb") as f:
            f.write(sample_png_image)
        with open(jpg_path, "wb") as f:
            f.write(sample_jpg_image)

        assembler = MultimodalAssembler(image_base_dir=temp_image_dir)

        results = [
            RetrievalResult(
                chunk_id="c1",
                content="Text with multiple images",
                metadata={"source": "test.txt"},
                score=0.95,
                image_refs=["test1.png", "test2.jpg"],
            ),
        ]

        content = assembler.assemble(results)

        assert len(content) == 3
        assert content[0]["type"] == "text"
        assert content[1]["type"] == "image"
        assert content[1]["mimeType"] == "image/png"
        assert content[2]["type"] == "image"
        assert content[2]["mimeType"] == "image/jpeg"

    def test_assemble_missing_image_ignored(self, temp_image_dir):
        """Test that missing images are gracefully handled."""
        assembler = MultimodalAssembler(image_base_dir=temp_image_dir)

        results = [
            RetrievalResult(
                chunk_id="c1",
                content="Text with missing image",
                metadata={"source": "test.txt"},
                score=0.95,
                image_refs=["nonexistent.png"],
            ),
        ]

        # Should not raise an exception
        content = assembler.assemble(results)

        # Should only contain text (image load failed)
        assert len(content) == 1
        assert content[0]["type"] == "text"
        assert content[0]["text"] == "Text with missing image"

    def test_mime_type_detection(self, temp_image_dir, sample_png_image):
        """Test MIME type detection for different file types."""
        # Create PNG image
        png_path = os.path.join(temp_image_dir, "image.png")
        with open(png_path, "wb") as f:
            f.write(sample_png_image)

        assembler = MultimodalAssembler(image_base_dir=temp_image_dir)

        results = [
            RetrievalResult(
                chunk_id="c1",
                content="Test",
                metadata={},
                score=0.9,
                image_refs=["image.png"],
            ),
        ]

        content = assembler.assemble(results)

        image_content = content[1]
        assert image_content["mimeType"] == "image/png"

    def test_path_traversal_prevention(self, temp_image_dir):
        """Test that path traversal attacks are prevented."""
        assembler = MultimodalAssembler(image_base_dir=temp_image_dir)

        # Try to reference a file outside the image directory
        results = [
            RetrievalResult(
                chunk_id="c1",
                content="Malicious",
                metadata={},
                score=0.9,
                image_refs=["../../../etc/passwd"],
            ),
        ]

        content = assembler.assemble(results)

        # Should only contain text (image path blocked)
        assert len(content) == 1
        assert content[0]["type"] == "text"

    def test_assemble_with_fallback(self, temp_image_dir):
        """Test fallback behavior when assembly encounters errors."""
        # Use invalid directory to trigger error
        assembler = MultimodalAssembler(image_base_dir="/nonexistent/path")

        results = [
            RetrievalResult(
                chunk_id="c1",
                content="Fallback test",
                metadata={},
                score=0.9,
            ),
        ]

        # Should not raise exception, returns text-only content
        content = assembler.assemble_with_fallback(results)

        assert len(content) == 1
        assert content[0]["type"] == "text"
        assert content[0]["text"] == "Fallback test"

    def test_supported_extensions(self):
        """Test getting list of supported file extensions."""
        extensions = MultimodalAssembler.get_supported_extensions()

        assert ".png" in extensions
        assert ".jpg" in extensions
        assert ".jpeg" in extensions
        assert ".gif" in extensions
        assert ".webp" in extensions

    def test_mime_type_validation(self):
        """Test MIME type validation."""
        assert MultimodalAssembler.is_mime_type_valid("image/png")
        assert MultimodalAssembler.is_mime_type_valid("image/jpeg")
        assert MultimodalAssembler.is_mime_type_valid("image/gif")
        assert not MultimodalAssembler.is_mime_type_valid("text/plain")
        assert not MultimodalAssembler.is_mime_type_valid("application/pdf")

    def test_empty_retrieval_results(self):
        """Test assembling empty retrieval results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assembler = MultimodalAssembler(image_base_dir=tmpdir)
            content = assembler.assemble([])

            assert content == []

    def test_image_with_nested_directory_path(self, temp_image_dir, sample_png_image):
        """Test handling images in nested directory structure."""
        # Create nested directory
        nested_dir = os.path.join(temp_image_dir, "subdir", "nested")
        os.makedirs(nested_dir, exist_ok=True)

        # Create image in nested directory
        image_path = os.path.join(nested_dir, "image.png")
        with open(image_path, "wb") as f:
            f.write(sample_png_image)

        assembler = MultimodalAssembler(image_base_dir=temp_image_dir)

        results = [
            RetrievalResult(
                chunk_id="c1",
                content="Test",
                metadata={},
                score=0.9,
                image_refs=["subdir/nested/image.png"],
            ),
        ]

        content = assembler.assemble(results)

        assert len(content) == 2
        assert content[1]["type"] == "image"
        assert content[1]["mimeType"] == "image/png"

    def test_base64_encoding_correctness(self, temp_image_dir, sample_png_image):
        """Test that base64 encoding is done correctly."""
        # Create test image
        image_path = os.path.join(temp_image_dir, "test.png")
        with open(image_path, "wb") as f:
            f.write(sample_png_image)

        assembler = MultimodalAssembler(image_base_dir=temp_image_dir)

        results = [
            RetrievalResult(
                chunk_id="c1",
                content="Test",
                metadata={},
                score=0.9,
                image_refs=["test.png"],
            ),
        ]

        content = assembler.assemble(results)

        # Verify base64 data can be decoded back to original
        image_content = content[1]
        decoded_data = base64.b64decode(image_content["data"])
        assert decoded_data == sample_png_image
