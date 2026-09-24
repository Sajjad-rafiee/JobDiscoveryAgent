"""Observability/demo wrapper around agent.runtime.invoke_agent().

Prints a readable trace of one agent run — the user request, every message in
the resulting LangGraph state, and the final response. This is a portfolio/
demo tool: it does not implement any agent behavior itself, it only inspects
and formats the state that invoke_agent() already returns.

Usage:
    uv run python scripts/demo_agent.py "Find AI Engineer jobs in Berlin."
"""

import re
import sys

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.cli import extract_text
from agent.runtime import invoke_agent

_TITLE_LINE = re.compile(r"^\d+\.\s*(.+)$", re.MULTILINE)
_COUNT_LINE = re.compile(r"^Found (\d+) ")

_EXAMPLE_TITLE_LIMIT = 3


def _print_tool_call(ai_message: AIMessage) -> None:
    for call in ai_message.tool_calls:
        args = call.get("args", {})
        print(f"Tool: {call['name']}")
        print(f"Query: {args.get('query', '')}")
        print(f"Location: {args.get('location') or '(none)'}")


def _print_tool_result(tool_message: ToolMessage) -> None:
    content = str(tool_message.content)
    status = getattr(tool_message, "status", "success")
    print(f"Tool: {tool_message.name or 'search_jobs'}")
    print(f"Status: {status}")

    if status == "error":
        # Already a sanitized, model-facing message (see tools/job_search.py);
        # never derived from the raw exception, so it's safe to print as-is.
        print(f"Message: {content}")
        return

    count_match = _COUNT_LINE.match(content)
    count = int(count_match.group(1)) if count_match else 0
    titles = _TITLE_LINE.findall(content)[:_EXAMPLE_TITLE_LIMIT]

    print(f"Results: {count}")
    if titles:
        print("Example titles:")
        for title in titles:
            print(f"- {title}")


def run_demo(prompt: str) -> None:
    print("USER REQUEST")
    print(prompt)
    print()
    print("AGENT EXECUTION")
    print()

    result = invoke_agent([{"role": "user", "content": prompt}])
    messages = result["messages"]

    for step, message in enumerate(messages, start=1):
        if isinstance(message, HumanMessage):
            print(f"{step}. HumanMessage")
            print(message.content)
        elif isinstance(message, ToolMessage):
            print(f"{step}. ToolMessage -> tool result")
            _print_tool_result(message)
        elif isinstance(message, AIMessage) and message.tool_calls:
            print(f"{step}. AIMessage -> tool call")
            _print_tool_call(message)
        elif isinstance(message, AIMessage):
            print(f"{step}. AIMessage -> final response")
        else:
            print(f"{step}. {type(message).__name__}")
        print()

    print("FINAL RESPONSE")
    print(extract_text(messages[-1]))


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print('Usage: uv run python scripts/demo_agent.py "<prompt>"', file=sys.stderr)
        return 1

    try:
        run_demo(argv[0])
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
