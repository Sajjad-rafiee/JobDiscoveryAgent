import pytest
from langchain_core.messages import ToolMessage

from api.client import CareerAPIError, CareerSearchClient, DemoCareerSearchClient
from models.job import JobPosting, JobSearchResult
from tools import TOOLS
from tools import job_search as job_search_module
from tools.job_search import SEARCH_FAILED_MESSAGE, search_jobs


class FakeClient:
    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error
        self.called_with = None
        self.closed = False

    def search_jobs(self, query, location=None):
        self.called_with = (query, location)
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


def test_tools_registry_contains_search_jobs():
    assert TOOLS == (search_jobs,)


def test_search_jobs_exposes_expected_schema():
    schema = search_jobs.args_schema.model_json_schema()

    assert set(schema["properties"]) == {"query", "location"}
    assert schema["required"] == ["query"]


def test_get_search_client_defaults_to_demo_client():
    client = job_search_module.get_search_client()

    assert isinstance(client, DemoCareerSearchClient)


def test_get_search_client_selects_http_client(monkeypatch):
    monkeypatch.setenv("CAREER_API_MODE", "http")
    monkeypatch.setenv("CAREER_API_BASE_URL", "http://test-api")
    monkeypatch.setenv("CAREER_API_SEARCH_PATH", "/test-search")

    with job_search_module.get_search_client() as client:
        assert isinstance(client, CareerSearchClient)


def test_search_jobs_delegates_to_client_and_closes_it(monkeypatch):
    fake_client = FakeClient(
        JobSearchResult(
            results=(JobPosting(title="AI Engineer", company="ExampleTech", location="Berlin"),)
        )
    )
    _use_client(monkeypatch, fake_client)

    result = search_jobs.invoke({"query": "AI Engineer", "location": "Berlin"})

    assert fake_client.called_with == ("AI Engineer", "Berlin")
    assert fake_client.closed
    assert result == (
        "Found jobs for query='AI Engineer', location='Berlin':\n"
        "1. AI Engineer — ExampleTech — Berlin"
    )


def test_search_jobs_marks_demo_results(monkeypatch):
    _use_client(monkeypatch, DemoCareerSearchClient())

    result = search_jobs.invoke({"query": "AI Engineer", "location": "Berlin"})

    assert result == (
        "Found jobs for query='AI Engineer', location='Berlin' (demo data):\n"
        "1. AI Engineer — ExampleTech — Berlin\n"
        "2. AI Engineer — ExampleLabs — Berlin"
    )


def test_search_jobs_handles_empty_results(monkeypatch):
    _use_client(monkeypatch, FakeClient(JobSearchResult(results=())))

    result = search_jobs.invoke({"query": "Nonexistent Role"})

    assert result == "No jobs found for query='Nonexistent Role', location='anywhere'."


def test_search_jobs_executes_deterministically_with_default_demo_client():
    result = search_jobs.invoke({"query": "AI Engineer", "location": "Berlin"})

    assert "(demo data)" in result
    assert "AI Engineer" in result
    assert "Berlin" in result


def test_search_jobs_reports_career_api_error_without_details(monkeypatch):
    fake_client = FakeClient(
        error=CareerAPIError("Career API transport error: http://internal-host/secret")
    )
    _use_client(monkeypatch, fake_client)

    message = search_jobs.invoke(
        {
            "type": "tool_call",
            "name": "search_jobs",
            "args": {"query": "AI Engineer"},
            "id": "call_1",
        }
    )

    assert isinstance(message, ToolMessage)
    assert message.status == "error"
    assert message.content == SEARCH_FAILED_MESSAGE
    assert "internal-host" not in message.content
    assert fake_client.closed


def test_search_jobs_does_not_hide_unexpected_errors(monkeypatch):
    _use_client(monkeypatch, FakeClient(error=RuntimeError("programming bug")))

    with pytest.raises(RuntimeError, match="programming bug"):
        search_jobs.invoke({"query": "AI Engineer"})
