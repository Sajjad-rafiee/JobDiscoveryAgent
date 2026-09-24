from dataclasses import dataclass

_POSTING_FIELDS = ("title", "company", "location")


class JobValidationError(ValueError):
    """Raised when job-search data does not have the expected shape."""


@dataclass(frozen=True)
class JobPosting:
    title: str
    company: str
    location: str

    def __post_init__(self) -> None:
        for name in _POSTING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, str):
                raise JobValidationError(
                    f"'{name}' must be a string, got {type(value).__name__}"
                )

    @classmethod
    def from_dict(cls, data: object) -> "JobPosting":
        if not isinstance(data, dict):
            raise JobValidationError(
                f"job posting must be an object, got {type(data).__name__}"
            )

        missing = [name for name in _POSTING_FIELDS if name not in data]
        if missing:
            raise JobValidationError(
                f"job posting is missing required fields: {', '.join(missing)}"
            )

        return cls(title=data["title"], company=data["company"], location=data["location"])


@dataclass(frozen=True)
class JobSearchResult:
    results: tuple[JobPosting, ...] = ()
    demo: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.results, tuple):
            raise JobValidationError(
                f"'results' must be a tuple, got {type(self.results).__name__}"
            )
        for index, item in enumerate(self.results):
            if not isinstance(item, JobPosting):
                raise JobValidationError(
                    f"results[{index}] must be a JobPosting, got {type(item).__name__}"
                )
        if not isinstance(self.demo, bool):
            raise JobValidationError(f"'demo' must be a boolean, got {type(self.demo).__name__}")

    @classmethod
    def from_dict(cls, data: object) -> "JobSearchResult":
        if not isinstance(data, dict):
            raise JobValidationError(
                f"search result must be an object, got {type(data).__name__}"
            )

        if "results" not in data:
            raise JobValidationError("search result is missing required field: results")

        raw_results = data["results"]
        if not isinstance(raw_results, list):
            raise JobValidationError(
                f"'results' must be a list, got {type(raw_results).__name__}"
            )

        postings = []
        for index, item in enumerate(raw_results):
            try:
                postings.append(JobPosting.from_dict(item))
            except JobValidationError as exc:
                raise JobValidationError(f"results[{index}]: {exc}") from exc

        return cls(results=tuple(postings), demo=data.get("demo", False))
