import httpx
import pytest

from api.client import CareerAPIError, CareerSearchClient


def _client_with_handler(handler) -> CareerSearchClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(base_url="http://test-api", transport=transport)
    return CareerSearchClient(
        base_url="http://test-api", search_path="/test-search", client=http_client
    )


def test_search_jobs_sends_expected_request_and_parses_response():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json={"results": [{"id": "1", "title": "AI Engineer"}]})

    client = _client_with_handler(handler)
    result = client.search_jobs("AI Engineer", "Berlin")

    assert captured["method"] == "GET"
    assert captured["path"] == "/test-search"
    assert captured["params"] == {"query": "AI Engineer", "location": "Berlin"}
    assert result == {"results": [{"id": "1", "title": "AI Engineer"}]}


def test_search_jobs_omits_location_when_not_provided():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json={"results": []})

    client = _client_with_handler(handler)
    client.search_jobs("AI Engineer")

    assert "location" not in captured["params"]


def test_search_jobs_raises_career_api_error_on_http_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "not found"})

    client = _client_with_handler(handler)

    with pytest.raises(CareerAPIError):
        client.search_jobs("AI Engineer")


def test_search_jobs_raises_career_api_error_on_invalid_json():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json")

    client = _client_with_handler(handler)

    with pytest.raises(CareerAPIError):
        client.search_jobs("AI Engineer")


def test_search_jobs_raises_career_api_error_on_transport_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    client = _client_with_handler(handler)

    with pytest.raises(CareerAPIError):
        client.search_jobs("AI Engineer")
