from langchain_core.tools import tool


@tool
def search_jobs(query: str, location: str | None = None) -> str:
    """Search for job postings matching a role or skill, optionally in a location.

    Use this when the user wants to find, search, or look up job openings.
    `query` is the role or skill to search for (e.g. "AI Engineer" or
    "backend developer"). `location` is optional; pass a city or region if
    the user mentions one, otherwise omit it.

    This currently returns static demo data, not a real job board.
    """
    location_label = location or "anywhere"
    return (
        f"Found demo jobs for query='{query}', location='{location_label}':\n"
        f"1. {query} — ExampleTech — {location_label}\n"
        f"2. {query} — ExampleLabs — {location_label}"
    )
