from tools.job_search import search_jobs


def test_search_jobs_exposes_expected_schema():
    schema = search_jobs.args_schema.model_json_schema()
    properties = schema["properties"]

    assert "query" in properties
    assert "location" in properties


def test_search_jobs_executes_deterministically():
    result = search_jobs.invoke({"query": "AI Engineer", "location": "Berlin"})

    assert "AI Engineer" in result
    assert "Berlin" in result
