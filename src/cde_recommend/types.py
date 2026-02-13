"""Domain types for CDE recommendation. Changes when the data model or API contract changes."""

from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field


@dataclass(frozen=True)
class CDE:
    cde_id: int
    cde_key: str
    pv_values: tuple[str, ...]


@dataclass(frozen=True)
class ColumnProfile:
    column_name: str
    dtype: str
    n_rows: int
    n_non_null: int
    null_frac: float
    n_unique_estimate: int
    sample_values: list[str]


@dataclass(frozen=True)
class CDEMatch:
    cde_id: int | None
    cde_key: str
    rank: int
    confidence: float


@dataclass(frozen=True)
class ColumnResult:
    column_name: str
    matches: list[CDEMatch]


@dataclass(frozen=True)
class ColumnInput:
    column_name: str
    column_values: list[str]


@dataclass(frozen=True)
class MatchRequest:
    data_commons_key: str
    columns: list[ColumnInput]
    version_label: str | None = None
    version_number: int | None = None
    model: str = "gpt-5-mini"
    top_k: int = 5
    concurrency: int = 50
    max_pv_samples: int = 12
    chunk_threshold: int = 500
    cde_chunk_size: int = 50
    per_chunk_k: int = 3


@dataclass
class UsageStats:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def add(self, other: "UsageStats") -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.total_tokens += other.total_tokens

    def to_dict(self) -> dict[str, int]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }


# --- Pydantic models for OpenAI structured output ---


class PotentialMatchIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_index: int = Field(
        ge=-1, description="0-based index into candidate list; -1 => No_Matches_Found"
    )
    rank: int = Field(ge=0, le=10, description="0 if no good matches; otherwise 1..K")
    confidence: float = Field(ge=0.0, le=1.0, description="0.0 (no match) to 1.0 (exact match)")


class ClosestMatchesIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    closest_matches: list[PotentialMatchIndex] = Field(default_factory=list)


# --- Response types ---


@dataclass(frozen=True)
class MatchResponse:
    data_commons_key: str
    version_label: str
    version_number: int | None
    candidate_cde_count: int
    params: dict[str, object]
    results: list[ColumnResult]
    usage: UsageStats
    errors: list[dict[str, str]] = field(default_factory=list)
