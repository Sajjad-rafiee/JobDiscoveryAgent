"""Thin CLI over agent.runtime.invoke_agent(). No agent logic lives here."""

import argparse
import sys

from agent.runtime import invoke_agent

EXIT_COMMANDS = {"exit", "quit"}


def _extract_text(message) -> str:
    """Return the final assistant message as plain text.

    `message.content` is a plain string for OpenAI and a list of content
    blocks (e.g. `[{"type": "text", "text": "..."}]`) for Gemini; this
    normalizes either shape for display.
    """
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block if isinstance(block, str) else block.get("text", "")
            for block in content
            if isinstance(block, str) or block.get("type") == "text"
        )
    return str(content)


def run_once(prompt: str) -> str:
    """Run one fresh conversation turn and return the assistant's reply text."""
    result = invoke_agent([{"role": "user", "content": prompt}])
    return _extract_text(result["messages"][-1])


def run_interactive() -> None:
    """Read prompts from stdin until 'exit'/'quit'. Each turn starts fresh."""
    print("CareerAgent CLI")
    print("Type 'exit' or 'quit' to leave.")
    print()

    while True:
        try:
            user_input = input("You: ")
        except EOFError:
            print()
            return

        prompt = user_input.strip()
        if not prompt:
            continue
        if prompt.lower() in EXIT_COMMANDS:
            print("Goodbye!")
            return

        try:
            response = run_once(prompt)
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            continue

        print(f"Agent: {response}")
        print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m agent.cli",
        description="CareerAgent CLI: a thin interface over invoke_agent().",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
        help="Run once with this prompt and print the response. Omit for interactive mode.",
    )
    args = parser.parse_args(argv)

    if args.prompt:
        try:
            print(run_once(args.prompt))
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        return 0

    run_interactive()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
