import pytest
from langchain_core.messages import ToolMessage

from api.client import CareerAPIError, CareerSearchClient, DemoCareerSearchClient
from models.job import JobSearchResult
from tests.backend_samples import search_result_json, search_result_with_nulls
from tools import TOOLS
from tools import job_search as job_search_module
from tools.job_search import (
    EMPTY_QUERY_MESSAGE,
    SEARCH_FAILED_MESSAGE,
    build_search_query,
    search_jobs,
)


class FakeClient:
    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error
        self.called_with = None
        self.closed = False

    def search_jobs(self, query):
        self.called_with = query
        if self._error is not None:
            raise self._error
        return self._result

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()


def _use_client(monkeypatch, client):
    monkeypatch.setattr(job_search_module, "get_search_client", lambda: client)


def _result(*items):
    return JobSearchResult.from_api_response(list(items))


def _as_tool_call(args):
    return {"type": "tool_call", "name": "search_jobs", "args": args, "id": "call_1"}


def test_tools_registry_contains_search_jobs():
    assert TOOLS == (search_jobs,)


def test_search_jobs_exposes_expected_schema():
    schema = search_jobs.args_schema.model_json_schema()

    assert set(schema["properties"]) == {"query", "location"}
    assert schema["required"] == ["query"]


def test_get_search_client_defaults_to_demo_client():
    assert isinstance(job_search_module.get_search_client(), DemoCareerSearchClient)


def test_get_search_client_selects_http_client(monkeypatch):
    monkeypatch.setenv("CAREER_API_MODE", "http")
    monkeypatch.setenv("CAREER_API_BASE_URL", "http://test-api")
    monkeypatch.setenv("CAREER_API_SEARCH_PATH", "/opportunities/search")

    with job_search_module.get_search_client() as client:
        assert isinstance(client, CareerSearchClient)


@pytest.mark.parametrize(
    ("query", "location", "expected"),
    [
        ("AI Engineer", "Berlin", "AI Engineer Berlin"),
        ("AI Engineer", None, "AI Engineer"),
        ("  AI Engineer ", "  Berlin  ", "AI Engineer Berlin"),
        ("AI Engineer", "   ", "AI Engineer"),
        ("", None, ""),
    ],
)
def test_build_search_query(query, location, expected):
    assert build_search_query(query, location) == expected


def test_location_is_folded_into_the_single_search_text(monkeypatch):
    fake_client = FakeClient(_result())
    _use_client(monkeypatch, fake_client)

    result = search_jobs.invoke({"query": "AI Engineer", "location": "Berlin"})

    assert fake_client.called_with == "AI Engineer Berlin"
    assert "not filtered by location" in result


def test_search_jobs_delegates_to_client_and_formats_real_fields(monkeypatch):
    fake_client = FakeClient(_result(search_result_json()))
    _use_client(monkeypatch, fake_client)

    result = search_jobs.invoke({"query": "Backend Engineer"})

    assert fake_client.called_with == "Backend Engineer"
    assert fake_client.closed
    assert result == (
        "Found 1 opportunity for 'Backend Engineer':\n"
        "1. Backend Engineer — N26\n"
        "   Type: job | Source: greenhouse | Relevance score: 0.87\n"
        "   Posted: 2026-09-01 | Deadline: 2026-10-31\n"
        "   URL: https://boards.example.com/jobs/1\n"
        "   Description: Build & run APIs."
    )
    assert "not filtered by location" not in result


def test_missing_optional_fields_are_reported_not_invented(monkeypatch):
    _use_client(monkeypatch, FakeClient(_result(search_result_with_nulls())))

    result = search_jobs.invoke({"query": "Backend Engineer"})

    assert "Posted: not provided | Deadline: not provided" in result
    assert "Description:" not in result


def test_long_descriptions_are_truncated(monkeypatch):
    _use_client(monkeypatch, FakeClient(_result(search_result_json(description="word " * 200))))

    result = search_jobs.invoke({"query": "Backend Engineer"})

    description_line = next(line for line in result.splitlines() if "Description:" in line)
    assert description_line.endswith("…")
    assert len(description_line) < 250


def test_demo_results_are_marked(monkeypatch):
    _use_client(monkeypatch, DemoCareerSearchClient())

    result = search_jobs.invoke({"query": "AI Engineer"})

    assert result.startswith("Found 2 opportunities for 'AI Engineer' (demo data):")
    assert "ExampleTech" in result
    assert "ExampleLabs" in result


def test_default_mode_uses_demo_client_without_network():
    result = search_jobs.invoke({"query": "AI Engineer", "location": "Berlin"})

    assert "(demo data)" in result
    assert "AI Engineer Berlin" in result


def test_empty_results_are_readable(monkeypatch):
    _use_client(monkeypatch, FakeClient(_result()))

    result = search_jobs.invoke({"query": "Nonexistent Role"})

    assert result == "No opportunities found for 'Nonexistent Role'."


def test_empty_query_is_reported_without_calling_the_backend(monkeypatch):
    fake_client = FakeClient(_result())
    _use_client(monkeypatch, fake_client)

    message = search_jobs.invoke(_as_tool_call({"query": "   "}))

    assert isinstance(message, ToolMessage)
    assert message.status == "error"
    assert message.content == EMPTY_QUERY_MESSAGE
    assert fake_client.called_with is None


def test_career_api_error_becomes_readable_tool_error(monkeypatch):
    fake_client = FakeClient(
        error=CareerAPIError("Career API transport error: http://internal-host/secret")
    )
    _use_client(monkeypatch, fake_client)

    message = search_jobs.invoke(_as_tool_call({"query": "AI Engineer"}))

    assert isinstance(message, ToolMessage)
    assert message.status == "error"
    assert message.content == SEARCH_FAILED_MESSAGE
    assert "internal-host" not in message.content
    assert fake_client.closed


def test_unexpected_errors_are_not_hidden(monkeypatch):
    _use_client(monkeypatch, FakeClient(error=RuntimeError("programming bug")))

    with pytest.raises(RuntimeError, match="programming bug"):
        search_jobs.invoke({"query": "AI Engineer"})
