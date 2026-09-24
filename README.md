# JobDiscoveryAgent

JobDiscoveryAgent is a LangGraph-based AI agent for discovering relevant job
opportunities. The LLM decides on its own when to invoke the `search_jobs`
tool, which queries CareerOpportunityEngine through its HTTP API, and answers
grounded only in what the tool returns — it never invents postings.

## Architecture

```text
User → JobDiscoveryAgent CLI → invoke_agent() → LangGraph → Gemini/OpenAI
     → search_jobs tool → CareerOpportunityEngine (HTTP API) → real results
     → ToolMessage → LLM → final grounded response
```

**JobDiscoveryAgent** (this repo) is the AI agent / orchestration layer: user
interaction, LLM reasoning, deciding when to call `search_jobs`, and
formatting the final response.

**[CareerOpportunityEngine](https://github.com/Sajjad-rafiee/CareerOpportunityEngine)**
is the separate backend: job ingestion, storage, embeddings, and search,
exposed over `GET /opportunities/search`.

The LLM decides when to invoke the `search_jobs` tool, which calls
CareerOpportunityEngine through its HTTP API — JobDiscoveryAgent holds no job
data and performs no database/vector search of its own; CareerOpportunityEngine
is not itself an LLM agent.

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
