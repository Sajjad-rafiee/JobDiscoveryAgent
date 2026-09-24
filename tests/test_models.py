from datetime import date, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from models.job import JobPosting, JobSearchResult
from tests.backend_samples import search_result_json, search_result_with_nulls


def test_search_result_parses_backend_schema():
    result = JobSearchResult.from_api_response([search_result_json()])

    assert result.demo is False
    [job] = result.results
    assert job.id == UUID("3f2b9c1e-8a4d-4e7b-9c2a-1d5e6f7a8b9c")
    assert job.title == "Backend Engineer"
    assert job.type == "job"
    assert job.url == "https://boards.example.com/jobs/1"
    assert job.deadline == date(2026, 10, 31)
    assert job.posted_at == datetime(2026, 9, 1, 12, 0)
    assert job.organization_id == UUID("0b8e4a2c-1f3d-4c5e-8a7b-9d0e1f2a3b4c")
    assert job.organization_name == "N26"
    assert job.external_id == "1"
    assert job.source == "greenhouse"
    assert job.created_at == datetime(2026, 9, 2, 8, 30)
    assert job.score == pytest.approx(0.87)


def test_search_result_preserves_order():
    payload = [search_result_json(title="First"), search_result_json(title="Second")]

    result = JobSearchResult.from_api_response(payload)

    assert [job.title for job in result.results] == ["First", "Second"]


def test_empty_search_response_is_valid():
    assert JobSearchResult.from_api_response([]).results == ()


def test_nullable_fields_accept_null_and_stay_null():
    [job] = JobSearchResult.from_api_response([search_result_with_nulls()]).results

    assert job.description is None
    assert job.deadline is None
    assert job.posted_at is None


def test_unknown_extra_fields_are_ignored():
    [job] = JobSearchResult.from_api_response(
        [search_result_json(eligibility={"degree": "BSc"})]
    ).results

    assert job.title == "Backend Engineer"


@pytest.mark.parametrize(
    "payload",
    [
        {"results": []},
        "not a list",
        None,
        ["not an object"],
    ],
)
def test_invalid_response_shape_is_rejected(payload):
    with pytest.raises(ValidationError):
        JobSearchResult.from_api_response(payload)


@pytest.mark.parametrize(
    "overrides",
    [
        {"id": "not-a-uuid"},
        {"title": None},
        {"title": 123},
        {"organization_name": None},
        {"deadline": "next week"},
        {"created_at": None},
        {"score": "high"},
    ],
)
def test_invalid_field_values_are_rejected(overrides):
    with pytest.raises(ValidationError):
        JobSearchResult.from_api_response([search_result_json(**overrides)])


@pytest.mark.parametrize(
    "missing", ["id", "title", "type", "url", "organization_name", "source", "score"]
)
def test_required_fields_are_enforced(missing):
    item = search_result_json()
    del item[missing]

    with pytest.raises(ValidationError):
        JobSearchResult.from_api_response([item])


def test_models_are_immutable():
    [job] = JobSearchResult.from_api_response([search_result_json()]).results

    with pytest.raises(ValidationError):
        job.title = "Other"


def test_job_posting_has_no_invented_fields():
    assert not {"company", "location", "salary", "remote"} & set(JobPosting.model_fields)
