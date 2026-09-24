from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate

from prompts.agent import SYSTEM_PROMPT, build_agent_prompt


def _render(messages):
    return build_agent_prompt().invoke({"messages": messages}).to_messages()


def test_build_agent_prompt_returns_chat_prompt_template():
    prompt = build_agent_prompt()

    assert isinstance(prompt, ChatPromptTemplate)
    assert prompt.input_variables == ["messages"]


def test_rendered_prompt_starts_with_system_message():
    rendered = _render([HumanMessage(content="Hello")])

    assert isinstance(rendered[0], SystemMessage)
    assert rendered[0].content == SYSTEM_PROMPT


def test_system_prompt_contains_behavioral_rules():
    prompt = SYSTEM_PROMPT.lower()

    assert "job-search assistant" in prompt
    assert "search_jobs" in prompt
    assert "answer directly" in prompt
    assert "never invent" in prompt
    assert "tool output" in prompt
    assert "unavailable" in prompt
    assert "clarification" in prompt
    assert "never reveal" in prompt
    assert "api keys" in prompt


def test_system_prompt_does_not_mention_temporary_implementation_details():
    prompt = SYSTEM_PROMPT.lower()

    for detail in ("demo", "mock", "fake", "test endpoint", "example"):
        assert detail not in prompt


def test_message_history_is_preserved_in_order():
    history = [
        HumanMessage(content="Hi"),
        AIMessage(content="Hello! How can I help?"),
        HumanMessage(content="What does a data engineer do?"),
    ]

    rendered = _render(history)

    assert rendered[1:] == history


def test_tool_messages_are_preserved():
    history = [
        HumanMessage(content="Find AI Engineer jobs in Berlin."),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_jobs",
                    "args": {"query": "AI Engineer", "location": "Berlin"},
                    "id": "call_1",
                }
            ],
        ),
        ToolMessage(content="Found jobs for query='AI Engineer'", tool_call_id="call_1"),
    ]

    rendered = _render(history)

    assert [type(m) for m in rendered] == [SystemMessage, HumanMessage, AIMessage, ToolMessage]
    assert rendered[1:] == history
    assert rendered[2].tool_calls[0]["name"] == "search_jobs"
    assert rendered[3].tool_call_id == "call_1"
