import pytest

from models.job import JobPosting, JobSearchResult, JobValidationError


def test_job_posting_from_valid_dict():
    posting = JobPosting.from_dict(
        {"title": "AI Engineer", "company": "ExampleTech", "location": "Berlin"}
    )

    assert posting == JobPosting(title="AI Engineer", company="ExampleTech", location="Berlin")


def test_job_posting_ignores_unknown_fields():
    posting = JobPosting.from_dict(
        {"title": "AI Engineer", "company": "ExampleTech", "location": "Berlin", "id": "1"}
    )

    assert posting.title == "AI Engineer"


def test_search_result_from_valid_dict():
    result = JobSearchResult.from_dict(
        {
            "results": [
                {"title": "AI Engineer", "company": "ExampleTech", "location": "Berlin"},
                {"title": "AI Engineer", "company": "ExampleLabs", "location": "Berlin"},
            ]
        }
    )

    assert [job.company for job in result.results] == ["ExampleTech", "ExampleLabs"]
    assert result.demo is False


def test_search_result_reads_demo_flag():
    result = JobSearchResult.from_dict({"results": [], "demo": True})

    assert result.results == ()
    assert result.demo is True


@pytest.mark.parametrize(
    "payload",
    [
        [],
        "not an object",
        {},
        {"results": "not a list"},
        {"results": None},
        {"results": ["not an object"]},
        {"results": [], "demo": "yes"},
    ],
)
def test_search_result_rejects_invalid_shape(payload):
    with pytest.raises(JobValidationError):
        JobSearchResult.from_dict(payload)


@pytest.mark.parametrize(
    "item",
    [
        {"company": "ExampleTech", "location": "Berlin"},
        {"title": 1, "company": "ExampleTech", "location": "Berlin"},
        {"title": "AI Engineer", "company": None, "location": "Berlin"},
        {"title": "AI Engineer", "company": "ExampleTech", "location": ["Berlin"]},
    ],
)
def test_job_posting_rejects_missing_or_invalid_fields(item):
    with pytest.raises(JobValidationError):
        JobPosting.from_dict(item)


def test_models_reject_invalid_direct_construction():
    with pytest.raises(JobValidationError):
        JobPosting(title="AI Engineer", company="ExampleTech", location=None)

    with pytest.raises(JobValidationError):
        JobSearchResult(results=[{"title": "AI Engineer"}])


def test_models_are_immutable():
    posting = JobPosting(title="AI Engineer", company="ExampleTech", location="Berlin")

    with pytest.raises(AttributeError):
        posting.title = "Other"
