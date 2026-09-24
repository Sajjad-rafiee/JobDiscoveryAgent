"""Sample CareerOpportunityEngine payloads for offline tests.

Shapes follow the backend's `OpportunitySearchResult` schema
(`app/schemas/opportunity.py`): `OpportunityResponse` fields plus `score`,
serialized as FastAPI does (UUIDs and dates as strings).
"""


def search_result_json(**overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "id": "3f2b9c1e-8a4d-4e7b-9c2a-1d5e6f7a8b9c",
        "title": "Backend Engineer",
        "description": "&lt;p&gt;Build &amp;amp; run APIs.&lt;/p&gt;",
        "type": "job",
        "url": "https://boards.example.com/jobs/1",
        "deadline": "2026-10-31",
        "posted_at": "2026-09-01T12:00:00",
        "organization_id": "0b8e4a2c-1f3d-4c5e-8a7b-9d0e1f2a3b4c",
        "organization_name": "N26",
        "external_id": "1",
        "source": "greenhouse",
        "created_at": "2026-09-02T08:30:00",
        "score": 0.87,
    }
    item.update(overrides)
    return item


def search_result_with_nulls(**overrides: object) -> dict[str, object]:
    return search_result_json(description=None, deadline=None, posted_at=None, **overrides)
