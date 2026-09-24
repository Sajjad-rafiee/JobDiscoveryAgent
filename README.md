# JobDiscoveryAgent

JobDiscoveryAgent is a LangGraph-based AI agent for discovering relevant job
opportunities. The LLM decides when to invoke the `search_jobs` tool, which
queries [CareerOpportunityEngine](https://github.com/Sajjad-rafiee/CareerOpportunityEngine)
through its HTTP API. The agent generates responses grounded only in the
returned job data — it never invents postings.

## Architecture

```text
User
  ↓
JobDiscoveryAgent CLI
  ↓
invoke_agent()
  ↓
LangGraph
  ↓
Gemini / OpenAI
  ↓
search_jobs
  ↓
CareerOpportunityEngine
  ↓
HTTP API
  ↓
Job search
  ↓
ToolMessage
  ↓
LLM
  ↓
Final grounded response
```

**JobDiscoveryAgent** is the AI agent/orchestration layer. It handles user
interaction, LLM reasoning, tool selection, and final response generation.

**CareerOpportunityEngine** is the separate backend responsible for job
ingestion, storage, embeddings, and search. JobDiscoveryAgent communicates
with it through HTTP — it holds no job data and performs no database/vector
search of its own.

### Example

When the user asks:

> Find AI Engineer jobs in Berlin.

the LLM can invoke:

```text
search_jobs(query="AI Engineer", location="Berlin")
```

The tool folds the location into the backend search text and calls:

```text
GET /opportunities/search?q=AI+Engineer+Berlin&limit=10
```

CareerOpportunityEngine performs the actual job search and returns the
matching opportunities. The result is passed back to the LLM, which produces
the final grounded answer.

## Running it

```bash
uv sync
cp .env.example .env
```

Configure `MODEL_PROVIDER` and the corresponding provider key in `.env`. For
live job search (instead of offline demo data), also configure:

```text
CAREER_API_MODE=http
CAREER_API_BASE_URL=http://localhost:8000
CAREER_API_SEARCH_PATH=/opportunities/search
```

Then run:

```bash
uv run python -m agent.cli "Find AI Engineer jobs in Berlin."
```

Or interactively:

```bash
uv run python -m agent.cli
```

## Testing

```bash
uv run pytest
```

Runs the offline test suite — no network access or API keys required.

```bash
uv run pytest -m integration
```

Runs integration tests against a running CareerOpportunityEngine backend.

## Live Agent Demo

```bash
uv run python scripts/demo_agent.py "Find AI Engineer jobs in Berlin."
```

Execution flow:

```text
User
→ LLM
→ search_jobs
→ CareerOpportunityEngine
→ ToolMessage
→ LLM
→ final grounded answer
```

The agent has been verified end-to-end against the real CareerOpportunityEngine
backend. See [the captured demo run](docs/demo/agent-run.md) for an example
using real backend data.

## Project Status

JobDiscoveryAgent currently supports:

- LangGraph-based agent orchestration
- Gemini and OpenAI chat model providers
- tool calling through `search_jobs`
- CareerOpportunityEngine HTTP integration
- CLI interaction
- unit and integration tests
- real end-to-end verification

This is a portfolio/demo project, not a production service.

## Related Project

[CareerOpportunityEngine](https://github.com/Sajjad-rafiee/CareerOpportunityEngine)
is the backend job-ingestion and search service used by JobDiscoveryAgent.

## License

MIT License. See [LICENSE](LICENSE).
