# CareerAgent — Live Agent Run

Captured from a real run:

```bash
uv run python scripts/demo_agent.py "Find AI Engineer jobs in Berlin."
```

against the real Gemini API and a locally running CareerOpportunityEngine
backend (`http://localhost:8000`). Nothing below is fabricated — it is the
tool's actual output, trimmed for length.

## Request

Find AI Engineer jobs in Berlin.

## Execution Flow

```text
User
→ invoke_agent()
→ LangGraph
→ Gemini
→ search_jobs
→ CareerOpportunityEngine
→ ToolMessage
→ Gemini
→ final response
```

## Tool Call

```text
Tool: search_jobs
Query: AI Engineer
Location: Berlin
```

## Backend Request

```text
GET /opportunities/search

q=AI Engineer Berlin
limit=10
```

(`search_jobs` folds `location` into the single semantic-search text `q`;
CareerOpportunityEngine has no separate location filter.)

## Real Results

```text
Status: success
Results: 10
Example titles:
- AI & Automation Manager — N26
- Marketing Operations Manager — N26
- Senior Technical Product Manager — GenAI & Agentic Systems — N26
```

## Final Response

Here are the most relevant AI- and engineering-related opportunities found for your search in Berlin:

1. **AI & Automation Manager** — **N26**
   - **Summary:** Lead the "AI Operator & Tooling Strategy" for N26 Marketing within the Growth Operations team.
   - **Link:** [Apply / View Job](https://n26.com/en-eu/careers/positions/7845575?gh_jid=7845575)

2. **Senior Technical Product Manager — GenAI & Agentic Systems** — **N26**
   - **Summary:** Drive the development of AI and agentic solutions within the Intelligent Operations Platforms (IOP) segment.
   - **Link:** [Apply / View Job](https://n26.com/en-eu/careers/positions/8196495?gh_jid=8196495)

3. **Senior Product Manager — Operations Automation & Enablement (OAE)** — **N26**
   - **Summary:** Focus on building intelligence and automated systems behind banking operations.
   - **Link:** [Apply / View Job](https://n26.com/en-eu/careers/positions/7996996?gh_jid=7996996)

4. **Backend Engineer — Cards & Digital Wallets** — **N26**
   - **Summary:** Software engineering role working on secure, scalable payment and digital wallet systems.
   - **Link:** [Apply / View Job](https://n26.com/en-eu/careers/positions/8169118?gh_jid=8169118)

5. **Senior Backend Engineer — Engagement** — **N26**
   - **Summary:** Core backend engineering role within the Grow & Engage domain.
   - **Link:** [Apply / View Job](https://n26.com/en-eu/careers/positions/8171135?gh_jid=8171135)

*(Note: While an exact "AI Engineer" title was not present in the current openings, these roles feature GenAI initiatives, automation strategy, and core backend engineering.)*

## Other verified prompts

Run for verification (not reproduced in full here — the agent behaved
correctly in both, including honestly reporting no exact match rather than
inventing one):

- "Find LLM Engineer jobs in Hamburg." → 10 results returned by the backend;
  no exact "LLM Engineer" title existed, and the agent said so instead of
  hallucinating one, offering related backend roles instead.
- "Find Computer Vision Engineer jobs in Berlin." → 10 results returned; no
  match existed, and the agent said so directly rather than presenting
  unrelated roles as if they matched.

## Verification

- Gemini E2E: passed
- CareerOpportunityEngine: passed
- Integration tests: 4 passed
- Full test suite: 137 passed
