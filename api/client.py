import httpx


class CareerAPIError(Exception):
    pass


class CareerSearchClient:
    """HTTP-based Career API client.

    The real Career backend does not exist yet, so `base_url` and
    `search_path` are supplied by the caller rather than assumed here — this
    class currently only exists to be exercised by its own tests via an
    injected transport, and to give the future real integration a stable
    boundary to plug into.
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

    def search_jobs(self, query: str, location: str | None = None) -> dict[str, object]:
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
            return response.json()
        except ValueError as exc:
            raise CareerAPIError("Career API returned invalid JSON") from exc

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "CareerSearchClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class DemoCareerSearchClient:
    """Deterministic local/demo implementation of the search_jobs capability.

    Used while the real Career backend contract is unavailable. Performs no
    network I/O; every response is explicitly marked with `"demo": True` so
    callers never mistake it for real backend data.
    """

    def search_jobs(self, query: str, location: str | None = None) -> dict[str, object]:
        location_label = location or "anywhere"
        return {
            "demo": True,
            "results": [
                {"title": query, "company": "ExampleTech", "location": location_label},
                {"title": query, "company": "ExampleLabs", "location": location_label},
            ],
        }
