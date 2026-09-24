from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from scripts import demo_agent


def _tool_call_message(query="AI Engineer", location="Berlin"):
    return AIMessage(
        content="",
        tool_calls=[{"name": "search_jobs", "args": {"query": query, "location": location}, "id": "call_1"}],
    )


def test_demo_agent_imports():
    assert callable(demo_agent.run_demo)
    assert callable(demo_agent.main)


def test_print_tool_call_shows_query_and_location(capsys):
    demo_agent._print_tool_call(_tool_call_message())

    out = capsys.readouterr().out
    assert "Tool: search_jobs" in out
    assert "Query: AI Engineer" in out
    assert "Location: Berlin" in out


def test_print_tool_call_shows_none_for_missing_location(capsys):
    demo_agent._print_tool_call(_tool_call_message(location=None))

    assert "Location: (none)" in capsys.readouterr().out


def test_print_tool_result_summarizes_success(capsys):
    content = (
        "Found 2 opportunities for 'AI Engineer Berlin':\n"
        "1. AI Engineer — ExampleTech\n"
        "   Type: job | Source: demo | Relevance score: 0.90\n"
        "   Posted: not provided | Deadline: not provided\n"
        "   URL: https://example.com/demo/0\n"
        "2. AI Engineer — ExampleLabs\n"
        "   Type: job | Source: demo | Relevance score: 0.80\n"
        "   Posted: not provided | Deadline: not provided\n"
        "   URL: https://example.com/demo/1"
    )
    tool_message = ToolMessage(content=content, name="search_jobs", tool_call_id="call_1")

    demo_agent._print_tool_result(tool_message)

    out = capsys.readouterr().out
    assert "Status: success" in out
    assert "Results: 2" in out
    assert "Example titles:" in out
    assert "- AI Engineer — ExampleTech" in out
    assert "- AI Engineer — ExampleLabs" in out


def test_print_tool_result_truncates_to_example_limit(capsys):
    lines = ["Found 5 opportunities for 'Engineer':"]
    for i in range(1, 6):
        lines.append(f"{i}. Role {i} — Org {i}")
    tool_message = ToolMessage(content="\n".join(lines), name="search_jobs", tool_call_id="call_1")

    demo_agent._print_tool_result(tool_message)

    out = capsys.readouterr().out
    assert out.count("- Role") == demo_agent._EXAMPLE_TITLE_LIMIT


def test_print_tool_result_shows_error_message_not_raw_exception(capsys):
    tool_message = ToolMessage(
        content="Job search failed: the Career API request could not be completed. "
        "No job results are available for this search.",
        name="search_jobs",
        tool_call_id="call_1",
        status="error",
    )

    demo_agent._print_tool_result(tool_message)

    out = capsys.readouterr().out
    assert "Status: error" in out
    assert "Job search failed" in out
    assert "Results:" not in out


def test_run_demo_prints_full_trace_and_final_response(monkeypatch, capsys):
    messages = [
        HumanMessage(content="Find AI Engineer jobs in Berlin."),
        _tool_call_message(),
        ToolMessage(
            content="Found 1 opportunity for 'AI Engineer Berlin':\n1. AI Engineer — N26",
            name="search_jobs",
            tool_call_id="call_1",
        ),
        AIMessage(content="Here is one role at N26."),
    ]
    monkeypatch.setattr(
        demo_agent, "invoke_agent", lambda msgs: {"messages": messages}
    )

    exit_code = demo_agent.main(["Find AI Engineer jobs in Berlin."])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "USER REQUEST" in out
    assert "1. HumanMessage" in out
    assert "2. AIMessage -> tool call" in out
    assert "3. ToolMessage -> tool result" in out
    assert "4. AIMessage -> final response" in out
    assert "FINAL RESPONSE" in out
    assert out.strip().endswith("Here is one role at N26.")


def test_run_demo_extracts_gemini_style_list_content(monkeypatch, capsys):
    final_message = AIMessage(content=[{"type": "text", "text": "Gemini final answer."}])
    messages = [HumanMessage(content="hi"), final_message]
    monkeypatch.setattr(demo_agent, "invoke_agent", lambda msgs: {"messages": messages})

    demo_agent.main(["hi"])

    assert "Gemini final answer." in capsys.readouterr().out


def test_main_requires_a_prompt(capsys):
    exit_code = demo_agent.main([])

    assert exit_code == 1
    assert "Usage" in capsys.readouterr().err


def test_main_handles_application_errors_cleanly(monkeypatch, capsys):
    def raise_error(msgs):
        raise RuntimeError("Career API request failed")

    monkeypatch.setattr(demo_agent, "invoke_agent", raise_error)

    exit_code = demo_agent.main(["Find AI Engineer jobs in Berlin."])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Traceback" not in captured.err
    assert "Career API request failed" in captured.err
