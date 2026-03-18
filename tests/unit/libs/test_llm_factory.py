import pytest

from src.libs.llm_client.llm_factory import create_llm
from src.libs.llm_client.base import BaseLLM


def test_create_llm_is_base():
    settings = None
    llm = create_llm(settings)
    assert isinstance(llm, BaseLLM)
    assert callable(llm.chat)
    assert callable(llm.generate)


def test_llm_chat_and_generate_mocked(mocker):
    llm = create_llm()
    # patch openai methods used by OpenAILLM
    import openai
    from types import SimpleNamespace

    mocker.patch.object(openai.ChatCompletion, 'create', return_value=SimpleNamespace(choices=[SimpleNamespace(message={"content": "hi"})]))
    mocker.patch.object(openai.Completion, 'create', return_value=SimpleNamespace(choices=[SimpleNamespace(text="hi")]))

    resp = llm.chat([{"role": "user", "content": "hello"}])
    assert resp == "hi"
    resp2 = llm.generate("hello")
    assert resp2 == "hi"
