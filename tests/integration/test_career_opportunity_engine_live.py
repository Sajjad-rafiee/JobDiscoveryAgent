"""Live checks against a running CareerOpportunityEngine backend.

Excluded from the default suite (`addopts = "-m 'not integration'"`). With the
backend running (see its README: `docker compose up --build`), run:

    uv run pytest -m integration

The backend URL comes from CAREER_API_BASE_URL (default http://localhost:8000).
It is read at import time because the autouse fixture in tests/conftest.py
clears CAREER_API_* variables before each test. The tests fail rather than skip
when the backend is unreachable, so a passing run always means a real backend
answered.
"""

import os

import pytest

from api.client import CareerSearchClient
from models.job import JobPosting, JobSearchResult
from tools.job_search import search_jobs

pytestmark = pytest.mark.integration

LIVE_BASE_URL = os.environ.get("CAREER_API_BASE_URL") or "http://localhost:8000"
SEARCH_PATH = "/opportunities/search"


def test_search_endpoint_matches_expected_schema():
    with CareerSearchClient(base_url=LIVE_BASE_URL, search_path=SEARCH_PATH) as client:
        result = client.search_jobs("AI Engineer")

    assert isinstance(result, JobSearchResult)
    assert result.demo is False
    assert len(result.results) <= 10
    assert all(isinstance(job, JobPosting) for job in result.results)
    scores = [job.score for job in result.results]
    assert scores == sorted(scores, reverse=True)


def test_search_jobs_tool_reaches_live_backend(monkeypatch):
    monkeypatch.setenv("CAREER_API_MODE", "http")
    monkeypatch.setenv("CAREER_API_BASE_URL", LIVE_BASE_URL)
    monkeypatch.setenv("CAREER_API_SEARCH_PATH", SEARCH_PATH)

    message = search_jobs.invoke(
        {
            "type": "tool_call",
            "name": "search_jobs",
            "args": {"query": "AI Engineer"},
            "id": "call_live",
        }
    )

    assert message.status == "success", message.content
    assert "(demo data)" not in message.content
