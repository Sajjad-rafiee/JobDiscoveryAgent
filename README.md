# CareerAgent

A LangGraph-based AI job-search agent. It decides on its own when to search
for jobs and answers grounded only in real backend data — it never invents
postings.

## Architecture

```text
User → CareerAgent CLI → invoke_agent() → LangGraph → Gemini/OpenAI
     → search_jobs tool → CareerOpportunityEngine (HTTP API) → real results
     → ToolMessage → LLM → final grounded response
```

**CareerAgent** (this repo) is the AI orchestration layer: user interaction,
LLM reasoning, deciding when to call `search_jobs`, and formatting the final
response.

**[CareerOpportunityEngine](https://github.com/Sajjad-rafiee/CareerOpportunityEngine)**
is the separate backend: it collects, stores, embeds, and searches job
postings, exposing them over `GET /opportunities/search`.

The LLM decides when to invoke the `search_jobs` tool, which calls
CareerOpportunityEngine through its HTTP API — CareerAgent holds no job data
and has no search logic of its own.

## Running it

```bash
uv sync
cp .env.example .env   # MODEL_PROVIDER (gemini/openai) + that provider's key;
                        # CAREER_API_MODE=demo works offline with no backend
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
backend — a full captured run (real data, nothing fabricated) is in
[`docs/demo/agent-run.md`](docs/demo/agent-run.md).

## Project status

Gemini and OpenAI are both supported as interchangeable chat model providers.
Tool calling, the CareerOpportunityEngine integration, and the CLI have each
been verified against real backends, not just mocks. This is a portfolio/demo
project, not a production service.
