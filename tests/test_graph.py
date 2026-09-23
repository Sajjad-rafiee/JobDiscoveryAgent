from langchain_core.messages import AIMessage

from agent import graph as graph_module
from agent.graph import graph


class FakeModel:
    def __init__(self):
        self.invoked_with = None

    def invoke(self, messages):
        self.invoked_with = messages
        return AIMessage(content="Hello! How can I help you?")


def _invoke_with_fake_model(monkeypatch):
    fake_model = FakeModel()
    monkeypatch.setattr(graph_module, "get_chat_model", lambda: fake_model)
    result = graph.invoke({"messages": [{"role": "user", "content": "Hello"}]})
    return fake_model, result


def test_graph_imports():
    assert graph is not None


def test_graph_calls_the_model(monkeypatch):
    fake_model, _ = _invoke_with_fake_model(monkeypatch)

    assert fake_model.invoked_with is not None


def test_ai_message_is_appended(monkeypatch):
    _, result = _invoke_with_fake_model(monkeypatch)

    messages = result["messages"]
    assert len(messages) == 2
    assert messages[0].content == "Hello"
    assert isinstance(messages[1], AIMessage)


def test_model_output_is_preserved(monkeypatch):
    _, result = _invoke_with_fake_model(monkeypatch)

    assert result["messages"][-1].content == "Hello! How can I help you?"
