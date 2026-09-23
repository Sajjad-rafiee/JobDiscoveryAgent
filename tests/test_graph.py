from langchain_core.messages import AIMessage, ToolMessage

from agent import graph as graph_module
from agent.graph import graph


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


def _invoke_graph(monkeypatch, model):
    monkeypatch.setattr(graph_module, "get_tool_enabled_chat_model", lambda: model)
    return graph.invoke(
        {"messages": [{"role": "user", "content": "Find AI Engineer jobs in Berlin."}]}
    )


def test_graph_imports():
    assert graph is not None


def test_graph_without_tool_call_ends_after_chat(monkeypatch):
    result = _invoke_graph(monkeypatch, PlainAnswerModel())

    messages = result["messages"]
    assert len(messages) == 2
    assert messages[0].content == "Find AI Engineer jobs in Berlin."
    assert isinstance(messages[1], AIMessage)
    assert not any(isinstance(m, ToolMessage) for m in messages)


def test_graph_with_tool_call_executes_tool_node(monkeypatch):
    result = _invoke_graph(monkeypatch, ToolCallThenAnswerModel())

    tool_messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_messages) == 1
    assert "AI Engineer" in tool_messages[0].content
    assert "Berlin" in tool_messages[0].content


def test_complete_tool_loop_produces_final_answer(monkeypatch):
    result = _invoke_graph(monkeypatch, ToolCallThenAnswerModel())

    messages = result["messages"]
    kinds = [type(m).__name__ for m in messages]

    assert kinds == ["HumanMessage", "AIMessage", "ToolMessage", "AIMessage"]
    assert messages[-1].content == "Here are some AI Engineer jobs in Berlin."
