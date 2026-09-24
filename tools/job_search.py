import html
import logging
import re

from langchain_core.tools import ToolException, tool

from api.client import CareerAPIError, SearchClient, create_search_client
from models.job import JobPosting, JobSearchResult
from utils.config import load_career_api_settings

logger = logging.getLogger(__name__)

SEARCH_FAILED_MESSAGE = (
    "Job search failed: the Career API request could not be completed. "
    "No job results are available for this search."
)
EMPTY_QUERY_MESSAGE = "Job search failed: a non-empty search query is required."

_DESCRIPTION_SNIPPET_LENGTH = 200


def get_search_client() -> SearchClient:
    """Create a new search client for one tool invocation; the caller closes it."""
    return create_search_client(load_career_api_settings())


def build_search_query(query: str, location: str | None) -> str:
    """Map the tool's `query` + `location` onto the backend's single `q` text.

    CareerOpportunityEngine has no location filter, only semantic search over
    `q`, so a location is appended to the search text. That biases the ranking
    towards the location but does not guarantee results are in it.
    """
    parts = (query, location or "")
    return " ".join(part.strip() for part in parts if part.strip())


def _description_snippet(description: str) -> str:
    # Job-board descriptions arrive as HTML, often itself HTML-escaped
    # (e.g. "&lt;p&gt;"): unescape, strip tags, then decode remaining entities.
    text = html.unescape(re.sub(r"<[^>]+>", " ", html.unescape(description)))
    text = " ".join(text.split())
    if len(text) > _DESCRIPTION_SNIPPET_LENGTH:
        text = text[:_DESCRIPTION_SNIPPET_LENGTH].rstrip() + "…"
    return text


def _format_posting(index: int, job: JobPosting) -> list[str]:
    posted = job.posted_at.date().isoformat() if job.posted_at else "not provided"
    deadline = job.deadline.isoformat() if job.deadline else "not provided"
    lines = [
        f"{index}. {job.title} — {job.organization_name}",
        f"   Type: {job.type} | Source: {job.source} | Relevance score: {job.score:.2f}",
        f"   Posted: {posted} | Deadline: {deadline}",
        f"   URL: {job.url}",
    ]
    if job.description:
        snippet = _description_snippet(job.description)
        if snippet:
            lines.append(f"   Description: {snippet}")
    return lines


def _format_results(result: JobSearchResult, search_text: str, location: str | None) -> str:
    demo_marker = " (demo data)" if result.demo else ""
    subject = f"'{search_text}'{demo_marker}"
    location_note = (
        f"Note: location '{location.strip()}' was added to the search text; "
        "results are ranked by relevance, not filtered by location."
        if location and location.strip()
        else None
    )

    count = len(result.results)
    if not count:
        lines = [f"No opportunities found for {subject}."]
    else:
        noun = "opportunity" if count == 1 else "opportunities"
        lines = [f"Found {count} {noun} for {subject}:"]
        for index, job in enumerate(result.results, start=1):
            lines.extend(_format_posting(index, job))

    if location_note:
        lines.append(location_note)
    return "\n".join(lines)


@tool
def search_jobs(query: str, location: str | None = None) -> str:
    """Search for job postings matching a role or skill, optionally in a location.

    Use this when the user wants to find, search, or look up job openings.
    `query` is the role or skill to search for (e.g. "AI Engineer" or
    "backend developer"). `location` is optional; pass a city or region if
    the user mentions one, otherwise omit it. Results are ranked by semantic
    relevance; a location influences the ranking but is not a strict filter.
    """
    search_text = build_search_query(query, location)
    if not search_text:
        raise ToolException(EMPTY_QUERY_MESSAGE)

    try:
        with get_search_client() as client:
            result = client.search_jobs(search_text)
    except CareerAPIError as exc:
        # The details may contain backend URLs, so they are logged rather than
        # shown to the model, which only learns that the search failed.
        logger.warning("Career API job search failed: %s", exc)
        raise ToolException(SEARCH_FAILED_MESSAGE) from exc

    return _format_results(result, search_text, location)


# A known Career API failure becomes an error ToolMessage the model can read;
# any other exception still propagates and fails the run.
search_jobs.handle_tool_error = True
