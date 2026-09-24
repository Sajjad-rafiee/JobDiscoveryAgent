from agent import cli as cli_module
from agent.cli import main, run_interactive, run_once


class FakeAIMessage:
    def __init__(self, content):
        self.content = content


def _fake_result(content):
    return {"messages": [FakeAIMessage(content)]}


def test_cli_module_imports():
    assert callable(main)
    assert callable(run_once)
    assert callable(run_interactive)


def test_run_once_calls_invoke_agent_with_user_message(monkeypatch):
    captured = {}

    def fake_invoke_agent(messages):
        captured["messages"] = messages
        return _fake_result("Hello there.")

    monkeypatch.setattr(cli_module, "invoke_agent", fake_invoke_agent)

    result = run_once("Find AI Engineer jobs in Berlin.")

    assert captured["messages"] == [
        {"role": "user", "content": "Find AI Engineer jobs in Berlin."}
    ]
    assert result == "Hello there."


def test_run_once_extracts_text_from_gemini_style_content(monkeypatch):
    monkeypatch.setattr(
        cli_module,
        "invoke_agent",
        lambda messages: _fake_result([{"type": "text", "text": "Gemini-style answer."}]),
    )

    assert run_once("hi") == "Gemini-style answer."


def test_one_shot_mode_prints_response(monkeypatch, capsys):
    monkeypatch.setattr(cli_module, "invoke_agent", lambda messages: _fake_result("The answer."))

    exit_code = main(["Find AI Engineer jobs in Berlin."])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "The answer."


def test_interactive_mode_accepts_multiple_prompts(monkeypatch, capsys):
    responses = iter(["First answer.", "Second answer."])
    calls = []

    def fake_invoke_agent(messages):
        calls.append(messages)
        return _fake_result(next(responses))

    monkeypatch.setattr(cli_module, "invoke_agent", fake_invoke_agent)
    inputs = iter(
        ["Find AI Engineer jobs in Berlin.", "Find LLM Engineer jobs in Hamburg.", "exit"]
    )
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    run_interactive()

    assert len(calls) == 2
    out = capsys.readouterr().out
    assert "First answer." in out
    assert "Second answer." in out
    assert "Goodbye!" in out


def test_exit_terminates_interactive_mode(monkeypatch, capsys):
    monkeypatch.setattr(cli_module, "invoke_agent", lambda messages: _fake_result("unused"))
    inputs = iter(["exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    run_interactive()

    assert "Goodbye!" in capsys.readouterr().out


def test_quit_terminates_interactive_mode_case_insensitively(monkeypatch, capsys):
    monkeypatch.setattr(cli_module, "invoke_agent", lambda messages: _fake_result("unused"))
    inputs = iter(["QUIT"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    run_interactive()

    assert "Goodbye!" in capsys.readouterr().out


def test_empty_input_does_not_invoke_the_agent(monkeypatch):
    calls = []
    monkeypatch.setattr(
        cli_module, "invoke_agent", lambda messages: calls.append(messages) or _fake_result("x")
    )
    inputs = iter(["", "   ", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    run_interactive()

    assert calls == []


def test_one_shot_mode_handles_application_errors_cleanly(monkeypatch, capsys):
    def raise_error(messages):
        raise RuntimeError("Career API request failed")

    monkeypatch.setattr(cli_module, "invoke_agent", raise_error)

    exit_code = main(["Find AI Engineer jobs in Berlin."])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Traceback" not in captured.err
    assert "Career API request failed" in captured.err


def test_interactive_mode_handles_application_errors_cleanly(monkeypatch, capsys):
    monkeypatch.setattr(
        cli_module,
        "invoke_agent",
        lambda messages: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    inputs = iter(["Find jobs.", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    run_interactive()

    captured = capsys.readouterr()
    assert "Traceback" not in captured.err
    assert "boom" in captured.err
    assert "Goodbye!" in captured.out
