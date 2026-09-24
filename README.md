# CareerAgent

A LangGraph job-search agent. It decides on its own when to call the
`search_jobs` tool, which queries
[CareerOpportunityEngine](https://github.com/Sajjad-rafiee/CareerOpportunityEngine)
for real postings, and answers grounded only in what the tool returns.
Supports Gemini (default) and OpenAI as interchangeable chat model providers.

## Running it

```bash
uv sync
cp .env.example .env   # fill in a Gemini or OpenAI key
uv run python -m agent.cli "Find AI Engineer jobs in Berlin."
```

Or interactively: `uv run python -m agent.cli`.

## Testing

```bash
uv run pytest                 # offline, no network or API keys needed
uv run pytest -m integration  # needs a running CareerOpportunityEngine backend
```

## Live Agent Demo

Example:

```bash
uv run python scripts/demo_agent.py "Find AI Engineer jobs in Berlin."
```

Execution flow:

```text
User
→ Gemini
→ search_jobs
→ CareerOpportunityEngine
→ ToolMessage
→ Gemini
→ final answer
```

The agent has been verified end-to-end against the real CareerOpportunityEngine
backend. A full captured run is in
[`docs/demo/agent-run.md`](docs/demo/agent-run.md).
