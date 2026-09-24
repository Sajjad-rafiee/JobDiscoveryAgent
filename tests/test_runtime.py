import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent import graph as graph_module
from agent import runtime as runtime_module
from agent.runtime import invoke_agent

USER_REQUEST = {"role": "user", "content": "Find AI Engineer jobs in Berlin."}


class FakeGraph:
    def __init__(self, result):
        self.result = result
        self.received = []

    def invoke(self, state):
        self.received.append(state)
        return self.result


class PlainAnswerModel:
    def invoke(self, messages):
        return AIMessage(content="Hello! How can I help you?")


class ToolCallThenAnswerModel:
    def __init__(self):
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_jobs",
                        "args": {"query": "AI Engineer", "location": "Berlin"},
                        "id": "call_1",
                    }
                ],
            )
        return AIMessage(content="Here are some AI Engineer jobs in Berlin.")


def _use_model(monkeypatch, model):
    monkeypatch.setattr(graph_module, "get_tool_enabled_chat_model", lambda: model)


def test_runtime_imports():
    assert callable(invoke_agent)


def test_runtime_delegates_to_graph_with_messages(monkeypatch):
    fake_graph = FakeGraph({"messages": []})
    monkeypatch.setattr(runtime_module, "graph", fake_graph)
    messages = [USER_REQUEST, HumanMessage(content="Remote roles are fine too.")]

    invoke_agent(messages)

    assert fake_graph.received == [{"messages": messages}]


def test_runtime_returns_graph_result_unchanged(monkeypatch):
    graph_result = {"messages": [AIMessage(content="deterministic")]}
    monkeypatch.setattr(runtime_module, "graph", FakeGraph(graph_result))

    result = invoke_agent([USER_REQUEST])

    assert result is graph_result


def test_runtime_accepts_tuple_input(monkeypatch):
    fake_graph = FakeGraph({"messages": []})
    monkeypatch.setattr(runtime_module, "graph", fake_graph)

    invoke_agent((USER_REQUEST,))

    assert fake_graph.received == [{"messages": [USER_REQUEST]}]


def test_runtime_rejects_bare_string(monkeypatch):
    fake_graph = FakeGraph({"messages": []})
    monkeypatch.setattr(runtime_module, "graph", fake_graph)

    with pytest.raises(TypeError):
        invoke_agent("Find AI Engineer jobs in Berlin.")

    assert fake_graph.received == []


def test_runtime_runs_real_graph_end_to_end(monkeypatch):
    _use_model(monkeypatch, PlainAnswerModel())

    result = invoke_agent([USER_REQUEST])

    messages = result["messages"]
    assert [type(m) for m in messages] == [HumanMessage, AIMessage]
    assert messages[0].content == "Find AI Engineer jobs in Berlin."
    assert messages[-1].content == "Hello! How can I help you?"


def test_runtime_runs_tool_loop_end_to_end(monkeypatch):
    _use_model(monkeypatch, ToolCallThenAnswerModel())

    result = invoke_agent([USER_REQUEST])

    messages = result["messages"]
    assert [type(m) for m in messages] == [HumanMessage, AIMessage, ToolMessage, AIMessage]
    assert messages[1].tool_calls[0]["name"] == "search_jobs"
    assert messages[2].tool_call_id == "call_1"
    assert "AI Engineer" in messages[2].content
    assert messages[-1].content == "Here are some AI Engineer jobs in Berlin."
