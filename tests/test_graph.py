from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from agent import graph as graph_module
from agent.graph import graph
from api.client import CareerAPIError
from prompts.agent import SYSTEM_PROMPT
from tools import job_search as job_search_module
from tools.job_search import SEARCH_FAILED_MESSAGE


class PlainAnswerModel:
    def invoke(self, messages):
        return AIMessage(content="Hello! How can I help you?")


class ToolCallThenAnswerModel:
    def __init__(self):
        self.calls = 0
        self.received = []

    def invoke(self, messages):
        self.calls += 1
        self.received.append(list(messages))
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


class RecordingModel:
    def __init__(self):
        self.received = []

    def invoke(self, messages):
        self.received.append(list(messages))
        return AIMessage(content="Hello! How can I help you?")


class FailingSearchClient:
    def search_jobs(self, query, location=None):
        raise CareerAPIError("Career API request failed with status 503")

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()


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


def test_model_receives_system_prompt_before_user_message(monkeypatch):
    model = RecordingModel()

    _invoke_graph(monkeypatch, model)

    assert len(model.received) == 1
    received = model.received[0]
    assert [type(m) for m in received] == [SystemMessage, HumanMessage]
    assert received[0].content == SYSTEM_PROMPT
    assert received[1].content == "Find AI Engineer jobs in Berlin."


def test_system_prompt_is_not_stored_in_state(monkeypatch):
    result = _invoke_graph(monkeypatch, RecordingModel())

    assert not any(isinstance(m, SystemMessage) for m in result["messages"])


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


def test_second_model_call_receives_full_tool_loop_history(monkeypatch):
    model = ToolCallThenAnswerModel()

    _invoke_graph(monkeypatch, model)

    assert len(model.received) == 2
    second_call = model.received[1]
    assert [type(m) for m in second_call] == [
        SystemMessage,
        HumanMessage,
        AIMessage,
        ToolMessage,
    ]
    assert second_call[2].tool_calls[0]["name"] == "search_jobs"
    assert second_call[3].tool_call_id == "call_1"


def test_career_api_failure_becomes_tool_error_and_graph_continues(monkeypatch):
    monkeypatch.setattr(job_search_module, "get_search_client", FailingSearchClient)
    model = ToolCallThenAnswerModel()

    result = _invoke_graph(monkeypatch, model)

    messages = result["messages"]
    kinds = [type(m).__name__ for m in messages]
    assert kinds == ["HumanMessage", "AIMessage", "ToolMessage", "AIMessage"]

    tool_message = messages[2]
    assert tool_message.status == "error"
    assert tool_message.content == SEARCH_FAILED_MESSAGE
    assert model.calls == 2
    assert messages[-1].content == "Here are some AI Engineer jobs in Berlin."
