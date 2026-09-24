from typing import Protocol, Self

import httpx

from models.job import JobPosting, JobSearchResult, JobValidationError
from utils.config import CareerAPISettings, ConfigError


class CareerAPIError(Exception):
    pass


class SearchClient(Protocol):
    """The job-search capability shared by the demo and HTTP clients."""

    def search_jobs(self, query: str, location: str | None = None) -> JobSearchResult: ...

    def close(self) -> None: ...

    def __enter__(self) -> Self: ...

    def __exit__(self, *exc_info: object) -> None: ...


class CareerSearchClient:
    """HTTP-based Career API client.

    The real Career backend does not exist yet, so `base_url` and
    `search_path` are supplied by the caller rather than assumed here — this
    class is only selected when `CAREER_API_MODE=http` is configured, and
    gives the future real integration a stable boundary to plug into.
    """

    def __init__(
        self,
        base_url: str,
        search_path: str,
        client: httpx.Client | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._search_path = search_path
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout)

    def search_jobs(self, query: str, location: str | None = None) -> JobSearchResult:
        params: dict[str, str] = {"query": query}
        if location is not None:
            params["location"] = location

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
            return JobSearchResult.from_dict(payload)
        except JobValidationError as exc:
            raise CareerAPIError(f"Career API returned an invalid response: {exc}") from exc

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class DemoCareerSearchClient:
    """Deterministic local/demo implementation of the search_jobs capability.

    Used while the real Career backend contract is unavailable. Performs no
    network I/O; every result is explicitly marked with `demo=True` so
    callers never mistake it for real backend data.
    """

    def search_jobs(self, query: str, location: str | None = None) -> JobSearchResult:
        location_label = location or "anywhere"
        return JobSearchResult(
            demo=True,
            results=(
                JobPosting(title=query, company="ExampleTech", location=location_label),
                JobPosting(title=query, company="ExampleLabs", location=location_label),
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
