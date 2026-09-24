import httpx
import pytest

from api.client import (
    CareerAPIError,
    CareerSearchClient,
    DemoCareerSearchClient,
    create_search_client,
)
from models.job import JobPosting, JobSearchResult
from utils.config import CareerAPISettings, ConfigError


def _client_with_handler(handler) -> CareerSearchClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(base_url="http://test-api", transport=transport)
    return CareerSearchClient(
        base_url="http://test-api", search_path="/test-search", client=http_client
    )


def _json_handler(payload):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return handler


def test_search_jobs_sends_expected_request_and_parses_response():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            json={
                "results": [
                    {"id": "1", "title": "AI Engineer", "company": "ExampleTech", "location": "Berlin"}
                ]
            },
        )

    client = _client_with_handler(handler)
    result = client.search_jobs("AI Engineer", "Berlin")

    assert captured["method"] == "GET"
    assert captured["path"] == "/test-search"
    assert captured["params"] == {"query": "AI Engineer", "location": "Berlin"}
    assert result == JobSearchResult(
        results=(JobPosting(title="AI Engineer", company="ExampleTech", location="Berlin"),),
        demo=False,
    )


def test_search_jobs_omits_location_when_not_provided():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json={"results": []})

    client = _client_with_handler(handler)
    client.search_jobs("AI Engineer")

    assert "location" not in captured["params"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"results": "not a list"},
        ["not", "an", "object"],
    ],
)
def test_search_jobs_raises_career_api_error_on_invalid_structure(payload):
    client = _client_with_handler(_json_handler(payload))

    with pytest.raises(CareerAPIError):
        client.search_jobs("AI Engineer")


@pytest.mark.parametrize(
    "item",
    [
        "not an object",
        {"title": "AI Engineer", "company": "ExampleTech"},
        {"title": "AI Engineer", "company": 42, "location": "Berlin"},
    ],
)
def test_search_jobs_raises_career_api_error_on_invalid_item(item):
    client = _client_with_handler(_json_handler({"results": [item]}))

    with pytest.raises(CareerAPIError):
        client.search_jobs("AI Engineer")


@pytest.mark.parametrize("status_code", [404, 500])
def test_search_jobs_raises_career_api_error_on_http_failure(status_code):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"error": "failed"})

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


def test_context_manager_closes_http_client():
    client = _client_with_handler(_json_handler({"results": []}))

    with client:
        pass

    assert client._client.is_closed


def test_demo_client_returns_typed_demo_result():
    with DemoCareerSearchClient() as client:
        result = client.search_jobs("AI Engineer", "Berlin")

    assert isinstance(result, JobSearchResult)
    assert result.demo is True
    assert [job.company for job in result.results] == ["ExampleTech", "ExampleLabs"]
    assert all(job.location == "Berlin" for job in result.results)


def test_create_search_client_selects_demo_client():
    client = create_search_client(CareerAPISettings(mode="demo"))

    assert isinstance(client, DemoCareerSearchClient)


def test_create_search_client_selects_http_client():
    settings = CareerAPISettings(
        mode="http", base_url="http://test-api", search_path="/test-search"
    )

    with create_search_client(settings) as client:
        assert isinstance(client, CareerSearchClient)


def test_create_search_client_rejects_incomplete_http_settings():
    with pytest.raises(ConfigError):
        create_search_client(CareerAPISettings(mode="http", base_url="http://test-api"))
