import uuid
from datetime import UTC, datetime
from typing import Protocol, Self

import httpx
from pydantic import ValidationError

from models.job import JobPosting, JobSearchResult
from utils.config import CareerAPISettings, ConfigError

# CareerOpportunityEngine's `GET /opportunities/search` accepts limit 1..50,
# default 10.
DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 50


class CareerAPIError(Exception):
    pass


class SearchClient(Protocol):
    """The job-search capability shared by the demo and HTTP clients."""

    def search_jobs(self, query: str) -> JobSearchResult: ...

    def close(self) -> None: ...

    def __enter__(self) -> Self: ...

    def __exit__(self, *exc_info: object) -> None: ...


class CareerSearchClient:
    """HTTP client for CareerOpportunityEngine's semantic search endpoint.

    Sends `GET <search_path>?q=<query>&limit=<limit>` (the backend route is
    `/opportunities/search`) and validates the JSON response. It is read-only:
    the backend's search endpoint is the only one it calls.
    """

    def __init__(
        self,
        base_url: str,
        search_path: str,
        client: httpx.Client | None = None,
        timeout: float = 10.0,
        limit: int = DEFAULT_SEARCH_LIMIT,
    ) -> None:
        if not 1 <= limit <= MAX_SEARCH_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_SEARCH_LIMIT}, got {limit}")
        self._search_path = search_path
        self._limit = limit
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout)

    def search_jobs(self, query: str) -> JobSearchResult:
        params = {"q": query, "limit": self._limit}

        try:
            response = self._client.get(self._search_path, params=params)
        except httpx.TransportError as exc:
            raise CareerAPIError(f"Career API transport error: {exc}") from exc

        if response.status_code >= 400:
            raise CareerAPIError(
                f"Career API request failed with status {response.status_code}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise CareerAPIError("Career API returned invalid JSON") from exc

        try:
            return JobSearchResult.from_api_response(payload)
        except ValidationError as exc:
            raise CareerAPIError(
                f"Career API returned an invalid response: {exc.error_count()} validation error(s)"
            ) from exc

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


_DEMO_ORGANIZATIONS = ("ExampleTech", "ExampleLabs")
_DEMO_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


class DemoCareerSearchClient:
    """Deterministic offline implementation of the search_jobs capability.

    For development without a running CareerOpportunityEngine. Performs no
    network I/O; every result is explicitly marked with `demo=True` so callers
    never mistake it for real backend data.
    """

    def search_jobs(self, query: str) -> JobSearchResult:
        return JobSearchResult(
            demo=True,
            results=tuple(
                JobPosting(
                    id=uuid.uuid5(uuid.NAMESPACE_URL, f"demo-job/{organization}/{query}"),
                    title=query,
                    type="job",
                    url=f"https://example.com/demo/{index}",
                    organization_id=uuid.uuid5(uuid.NAMESPACE_URL, f"demo-org/{organization}"),
                    organization_name=organization,
                    external_id=f"demo-{index}",
                    source="demo",
                    created_at=_DEMO_CREATED_AT,
                    score=round(0.9 - 0.1 * index, 2),
                )
                for index, organization in enumerate(_DEMO_ORGANIZATIONS)
            ),
        )

    def close(self) -> None:
        pass

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def create_search_client(settings: CareerAPISettings) -> SearchClient:
    """Return the search client for the configured Career API mode.

    The caller owns the returned client and must close it (it is a context
    manager), since the HTTP client holds a connection pool.
    """
    if settings.mode == "http":
        if not settings.base_url or not settings.search_path:
            raise ConfigError(
                "HTTP Career API mode requires CAREER_API_BASE_URL and CAREER_API_SEARCH_PATH"
            )
        return CareerSearchClient(base_url=settings.base_url, search_path=settings.search_path)

    return DemoCareerSearchClient()
