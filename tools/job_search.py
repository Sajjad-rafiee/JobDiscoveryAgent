from langchain_core.tools import tool

from api.client import DemoCareerSearchClient

_client = DemoCareerSearchClient()


def get_search_client():
    return _client


def _format_results(payload: dict[str, object], query: str, location: str | None) -> str:
    location_label = location or "anywhere"
    demo_marker = " (demo data)" if payload.get("demo") else ""
    results = payload.get("results") or []

    if not results:
        return f"No jobs found for query='{query}', location='{location_label}'{demo_marker}."

    lines = [f"Found jobs for query='{query}', location='{location_label}'{demo_marker}:"]
    for index, item in enumerate(results, start=1):
        title = item.get("title", query)
        company = item.get("company", "Unknown")
        item_location = item.get("location", location_label)
        lines.append(f"{index}. {title} — {company} — {item_location}")
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
    payload = get_search_client().search_jobs(query, location)
    return _format_results(payload, query, location)
