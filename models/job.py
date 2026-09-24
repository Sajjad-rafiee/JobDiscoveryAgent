"""Job-search domain models, mirroring CareerOpportunityEngine's search response.

The backend's `GET /opportunities/search` returns `list[OpportunitySearchResult]`
(`app/schemas/opportunity.py` in CareerOpportunityEngine); `JobPosting` follows
that schema field for field. Unknown extra fields are ignored so the backend can
add fields without breaking CareerAgent.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, TypeAdapter


class JobPosting(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    id: UUID
    title: str
    description: str | None = None
    type: str
    url: str
    deadline: date | None = None
    posted_at: datetime | None = None
    organization_id: UUID
    organization_name: str
    external_id: str
    source: str
    created_at: datetime
    # Cosine similarity to the search query; higher is closer.
    score: float


_SEARCH_RESPONSE = TypeAdapter(list[JobPosting])


class JobSearchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    results: tuple[JobPosting, ...] = ()
    demo: bool = False

    @classmethod
    def from_api_response(cls, payload: object) -> "JobSearchResult":
        """Validate a decoded `/opportunities/search` JSON body.

        Raises `pydantic.ValidationError` if the body is not a list of
        search results matching the backend schema.
        """
        return cls(results=tuple(_SEARCH_RESPONSE.validate_python(payload)))
