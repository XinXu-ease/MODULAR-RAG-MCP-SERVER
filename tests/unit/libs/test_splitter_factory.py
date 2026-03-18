from src.libs.splitter.splitter_factory import create_splitter
from src.libs.splitter.base import BaseSplitter


def test_create_splitter_is_base():
    splitter = create_splitter()
    assert isinstance(splitter, BaseSplitter)
    assert splitter.split("hello world")
