"""Live checks against a running CareerOpportunityEngine backend.

Excluded from the default suite (`addopts = "-m 'not integration'"`). With the
backend running (see its README: `docker compose up --build`), run:

    uv run pytest -m integration

The backend URL comes from CAREER_API_BASE_URL (default http://localhost:8000).
It is read at import time because the autouse fixture in tests/conftest.py
clears CAREER_API_* variables before each test. The tests fail rather than skip
when the backend is unreachable, so a passing run always means a real backend
answered. They assume nothing about which postings the backend holds.
"""

import os

import httpx
import pytest

from api.client import DEFAULT_SEARCH_LIMIT, CareerSearchClient
from models.job import JobPosting, JobSearchResult
from tools import job_search as job_search_module
from tools.job_search import search_jobs

pytestmark = pytest.mark.integration

LIVE_BASE_URL = os.environ.get("CAREER_API_BASE_URL") or "http://localhost:8000"
SEARCH_PATH = "/opportunities/search"
SMALL_LIMIT = 5


def _tool_call(args):
    return {"type": "tool_call", "name": "search_jobs", "args": args, "id": "call_live"}


def test_search_endpoint_returns_http_200_with_a_list():
    response = httpx.get(
        f"{LIVE_BASE_URL}{SEARCH_PATH}",
        params={"q": "AI Engineer", "limit": SMALL_LIMIT},
        timeout=30.0,
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) <= SMALL_LIMIT


def test_live_response_converts_to_domain_model():
    with CareerSearchClient(
        base_url=LIVE_BASE_URL, search_path=SEARCH_PATH, timeout=30.0, limit=SMALL_LIMIT
    ) as client:
        result = client.search_jobs("AI Engineer")

    assert isinstance(result, JobSearchResult)
    assert result.demo is False
    assert len(result.results) <= SMALL_LIMIT
    assert all(isinstance(job, JobPosting) for job in result.results)
    scores = [job.score for job in result.results]
    assert scores == sorted(scores, reverse=True)


def test_search_jobs_tool_reaches_live_backend(monkeypatch):
    monkeypatch.setenv("CAREER_API_MODE", "http")
    monkeypatch.setenv("CAREER_API_BASE_URL", LIVE_BASE_URL)
    monkeypatch.setenv("CAREER_API_SEARCH_PATH", SEARCH_PATH)

    message = search_jobs.invoke(_tool_call({"query": "AI Engineer"}))

    assert message.status == "success", message.content
    assert "(demo data)" not in message.content
    assert message.content.startswith(("Found ", "No opportunities found"))


def test_location_reaches_backend_only_inside_q(monkeypatch):
    requests: list[httpx.Request] = []

    def recording_client():
        http_client = httpx.Client(
            base_url=LIVE_BASE_URL, timeout=30.0, event_hooks={"request": [requests.append]}
        )
        return CareerSearchClient(
            base_url=LIVE_BASE_URL, search_path=SEARCH_PATH, client=http_client
        )

    monkeypatch.setattr(job_search_module, "get_search_client", recording_client)

    message = search_jobs.invoke(_tool_call({"query": "AI Engineer", "location": "Berlin"}))

    assert message.status == "success", message.content
    [request] = requests
    assert request.url.path == SEARCH_PATH
    assert dict(request.url.params) == {
        "q": "AI Engineer Berlin",
        "limit": str(DEFAULT_SEARCH_LIMIT),
    }
    assert "location" not in request.url.params
    assert "not filtered by location" in message.content
