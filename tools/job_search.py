import logging

from langchain_core.tools import ToolException, tool

from api.client import CareerAPIError, SearchClient, create_search_client
from models.job import JobSearchResult
from utils.config import load_career_api_settings

logger = logging.getLogger(__name__)

SEARCH_FAILED_MESSAGE = (
    "Job search failed: the Career API request could not be completed. "
    "No job results are available for this search."
)


def get_search_client() -> SearchClient:
    """Create a new search client for one tool invocation; the caller closes it."""
    return create_search_client(load_career_api_settings())


def _format_results(result: JobSearchResult, query: str, location: str | None) -> str:
    location_label = location or "anywhere"
    demo_marker = " (demo data)" if result.demo else ""

    if not result.results:
        return f"No jobs found for query='{query}', location='{location_label}'{demo_marker}."

    lines = [f"Found jobs for query='{query}', location='{location_label}'{demo_marker}:"]
    for index, job in enumerate(result.results, start=1):
        lines.append(f"{index}. {job.title} — {job.company} — {job.location}")
    return "\n".join(lines)


@tool
def search_jobs(query: str, location: str | None = None) -> str:
    """Search for job postings matching a role or skill, optionally in a location.

    Use this when the user wants to find, search, or look up job openings.
    `query` is the role or skill to search for (e.g. "AI Engineer" or
    "backend developer"). `location` is optional; pass a city or region if
    the user mentions one, otherwise omit it.

    This currently returns static demo data, not a real job board.
    """
    try:
        with get_search_client() as client:
            result = client.search_jobs(query, location)
    except CareerAPIError as exc:
        # The details may contain backend URLs, so they are logged rather than
        # shown to the model, which only learns that the search failed.
        logger.warning("Career API job search failed: %s", exc)
        raise ToolException(SEARCH_FAILED_MESSAGE) from exc

    return _format_results(result, query, location)


# A known Career API failure becomes an error ToolMessage the model can read;
# any other exception still propagates and fails the run.
search_jobs.handle_tool_error = True
