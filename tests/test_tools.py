from tools import job_search as job_search_module
from tools.job_search import search_jobs


class FakeClient:
    def __init__(self, payload):
        self._payload = payload
        self.called_with = None

    def search_jobs(self, query, location=None):
        self.called_with = (query, location)
        return self._payload


def test_search_jobs_exposes_expected_schema():
    schema = search_jobs.args_schema.model_json_schema()
    properties = schema["properties"]

    assert "query" in properties
    assert "location" in properties


def test_search_jobs_delegates_to_client(monkeypatch):
    fake_client = FakeClient(
        {
            "demo": True,
            "results": [
                {"title": "AI Engineer", "company": "ExampleTech", "location": "Berlin"}
            ],
        }
    )
    monkeypatch.setattr(job_search_module, "get_search_client", lambda: fake_client)

    result = search_jobs.invoke({"query": "AI Engineer", "location": "Berlin"})

    assert fake_client.called_with == ("AI Engineer", "Berlin")
    assert "AI Engineer" in result
    assert "ExampleTech" in result
    assert "Berlin" in result


def test_search_jobs_handles_empty_results(monkeypatch):
    fake_client = FakeClient({"demo": True, "results": []})
    monkeypatch.setattr(job_search_module, "get_search_client", lambda: fake_client)

    result = search_jobs.invoke({"query": "Nonexistent Role"})

    assert "No jobs found" in result


def test_search_jobs_executes_deterministically_with_default_demo_client():
    result = search_jobs.invoke({"query": "AI Engineer", "location": "Berlin"})

    assert "AI Engineer" in result
    assert "Berlin" in result
