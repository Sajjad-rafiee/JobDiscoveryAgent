import httpx
import pytest

from api.client import (
    DEFAULT_SEARCH_LIMIT,
    CareerAPIError,
    CareerSearchClient,
    DemoCareerSearchClient,
    create_search_client,
)
from models.job import JobSearchResult
from tests.backend_samples import search_result_json, search_result_with_nulls
from utils.config import CareerAPISettings, ConfigError

SEARCH_PATH = "/opportunities/search"


def _client_with_handler(handler, **kwargs) -> CareerSearchClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(base_url="http://test-api", transport=transport)
    return CareerSearchClient(
        base_url="http://test-api", search_path=SEARCH_PATH, client=http_client, **kwargs
    )


def _json_handler(payload, status_code=200):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload)

    return handler


def test_search_calls_opportunities_search_with_q_and_limit():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json=[])

    _client_with_handler(handler).search_jobs("AI Engineer Berlin")

    assert captured["method"] == "GET"
    assert captured["path"] == "/opportunities/search"
    assert captured["params"] == {"q": "AI Engineer Berlin", "limit": str(DEFAULT_SEARCH_LIMIT)}


def test_default_limit_matches_backend_default():
    assert DEFAULT_SEARCH_LIMIT == 10


def test_custom_limit_is_sent():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["limit"] = request.url.params["limit"]
        return httpx.Response(200, json=[])

    _client_with_handler(handler, limit=50).search_jobs("AI Engineer")

    assert captured["limit"] == "50"


@pytest.mark.parametrize("limit", [0, 51])
def test_limit_outside_backend_range_is_rejected(limit):
    with pytest.raises(ValueError):
        CareerSearchClient(base_url="http://test-api", search_path=SEARCH_PATH, limit=limit)


def test_real_schema_response_becomes_job_search_result():
    client = _client_with_handler(
        _json_handler([search_result_json(), search_result_json(title="Data Engineer")])
    )

    result = client.search_jobs("engineer")

    assert isinstance(result, JobSearchResult)
    assert result.demo is False
    assert [job.title for job in result.results] == ["Backend Engineer", "Data Engineer"]
    assert result.results[0].organization_name == "N26"


def test_null_optional_fields_are_accepted():
    client = _client_with_handler(_json_handler([search_result_with_nulls()]))

    [job] = client.search_jobs("engineer").results

    assert (job.description, job.deadline, job.posted_at) == (None, None, None)


def test_empty_result_list_is_a_successful_search():
    client = _client_with_handler(_json_handler([]))

    assert client.search_jobs("engineer").results == ()


@pytest.mark.parametrize(
    "payload",
    [
        {"results": []},
        {"detail": "error"},
        [search_result_json(score="high")],
        [search_result_json(id="not-a-uuid")],
        [search_result_json(title=None)],
        ["not an object"],
    ],
)
def test_schema_validation_failure_raises_career_api_error(payload):
    client = _client_with_handler(_json_handler(payload))

    with pytest.raises(CareerAPIError):
        client.search_jobs("engineer")


def test_missing_required_field_raises_career_api_error():
    item = search_result_json()
    del item["organization_name"]
    client = _client_with_handler(_json_handler([item]))

    with pytest.raises(CareerAPIError):
        client.search_jobs("engineer")


@pytest.mark.parametrize("status_code", [404, 422, 500])
def test_http_failure_raises_career_api_error(status_code):
    client = _client_with_handler(_json_handler({"detail": "failed"}, status_code))

    with pytest.raises(CareerAPIError):
        client.search_jobs("engineer")


def test_invalid_json_raises_career_api_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json")

    with pytest.raises(CareerAPIError):
        _client_with_handler(handler).search_jobs("engineer")


def test_transport_failure_raises_career_api_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    with pytest.raises(CareerAPIError):
        _client_with_handler(handler).search_jobs("engineer")


def test_context_manager_closes_http_client():
    client = _client_with_handler(_json_handler([]))

    with client:
        pass

    assert client._client.is_closed


def test_demo_client_returns_typed_demo_result():
    with DemoCareerSearchClient() as client:
        result = client.search_jobs("AI Engineer")

    assert isinstance(result, JobSearchResult)
    assert result.demo is True
    assert [job.organization_name for job in result.results] == ["ExampleTech", "ExampleLabs"]
    assert all(job.title == "AI Engineer" for job in result.results)


def test_demo_client_is_deterministic():
    client = DemoCareerSearchClient()

    assert client.search_jobs("AI Engineer") == client.search_jobs("AI Engineer")


def test_create_search_client_selects_demo_client():
    client = create_search_client(CareerAPISettings(mode="demo"))

    assert isinstance(client, DemoCareerSearchClient)


def test_create_search_client_selects_http_client():
    settings = CareerAPISettings(mode="http", base_url="http://test-api", search_path=SEARCH_PATH)

    with create_search_client(settings) as client:
        assert isinstance(client, CareerSearchClient)


def test_create_search_client_rejects_incomplete_http_settings():
    with pytest.raises(ConfigError):
        create_search_client(CareerAPISettings(mode="http", base_url="http://test-api"))
