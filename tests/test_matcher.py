import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from cde_recommend.matcher import _resolve_indices, match_column
from cde_recommend.types import CDE, CDEMatch, ColumnProfile, PotentialMatchIndex


@pytest.fixture
def column_profile() -> ColumnProfile:
    return ColumnProfile(
        column_name="sex",
        dtype="categorical",
        n_rows=100,
        n_non_null=95,
        null_frac=0.05,
        n_unique_estimate=3,
        sample_values=["Male", "Female", "Unknown"],
    )


@pytest.fixture
def mock_client() -> AsyncMock:
    client = AsyncMock()
    response = MagicMock()
    response.output_text = json.dumps({
        "closest_matches": [
            {"candidate_index": 0, "rank": 1, "confidence": 0.95},
            {"candidate_index": 2, "rank": 2, "confidence": 0.7},
        ]
    })
    response.usage = MagicMock(input_tokens=1000, output_tokens=50, total_tokens=1050)
    client.responses.create = AsyncMock(return_value=response)
    return client


# --- _resolve_indices ---


def test_resolve_indices_maps_correctly(sample_cdes: list[CDE]):
    # Given: indices pointing to positions 0 and 2 in the CDE list
    indices = [
        PotentialMatchIndex(candidate_index=0, rank=1, confidence=0.95),
        PotentialMatchIndex(candidate_index=2, rank=2, confidence=0.7),
    ]

    # When: resolved against the CDE list
    result = _resolve_indices(indices, sample_cdes, "test_col", limit=5)

    # Then: indices map to the correct CDEs with preserved rank/confidence
    assert len(result) == 2
    assert result[0] == CDEMatch(cde_id=1, cde_key="gender", rank=1, confidence=0.95)
    assert result[1] == CDEMatch(cde_id=3, cde_key="ethnicity", rank=2, confidence=0.7)


def test_resolve_indices_handles_no_match_sentinel(sample_cdes: list[CDE]):
    # Given: the no-match sentinel index (-1)
    indices = [PotentialMatchIndex(candidate_index=-1, rank=0, confidence=0.0)]

    # When: resolved
    result = _resolve_indices(indices, sample_cdes, "test_col", limit=5)

    # Then: produces a No_Matches_Found marker
    assert len(result) == 1
    assert result[0].cde_id is None
    assert result[0].cde_key == "No_Matches_Found"


def test_invalid_indices_are_filtered_out(sample_cdes: list[CDE]):
    # Given: one valid, one out-of-range, one valid index
    indices = [
        PotentialMatchIndex(candidate_index=0, rank=1, confidence=0.9),
        PotentialMatchIndex(candidate_index=99, rank=2, confidence=0.5),  # out of range
        PotentialMatchIndex(candidate_index=2, rank=3, confidence=0.7),
    ]

    # When: resolved
    result = _resolve_indices(indices, sample_cdes, "test_col", limit=5)

    # Then: out-of-range index is silently dropped
    assert len(result) == 2
    assert result[0].cde_key == "gender"
    assert result[1].cde_key == "ethnicity"


def test_resolve_indices_respects_limit(sample_cdes: list[CDE]):
    # Given: 3 valid indices but a limit of 2
    indices = [
        PotentialMatchIndex(candidate_index=0, rank=1, confidence=0.9),
        PotentialMatchIndex(candidate_index=1, rank=2, confidence=0.7),
        PotentialMatchIndex(candidate_index=2, rank=3, confidence=0.5),
    ]

    # When: resolved with limit=2
    result = _resolve_indices(indices, sample_cdes, "test_col", limit=2)

    # Then: only 2 results returned
    assert len(result) == 2


# --- match_column (async, mocked OpenAI) ---


@pytest.mark.asyncio
async def test_match_column_returns_ranked_results(
    column_profile: ColumnProfile,
    sample_cdes: list[CDE],
    mock_client: AsyncMock,
):
    # Given: a categorical column profile and a mock OpenAI client returning 2 matches
    semaphore = asyncio.Semaphore(10)

    # When: match_column is called
    result, usage = await match_column(
        profile=column_profile,
        all_cdes=sample_cdes,
        client=mock_client,
        semaphore=semaphore,
        developer_message="test developer message",
        model="test-model",
        final_k=5,
    )

    # Then: results contain the correct column name, matches, and token usage
    assert result.column_name == "sex"
    assert len(result.matches) == 2
    assert result.matches[0].cde_key == "gender"
    assert result.matches[0].rank == 1
    assert usage.total_tokens == 1050


@pytest.mark.asyncio
async def test_match_column_handles_no_matches(
    column_profile: ColumnProfile,
    sample_cdes: list[CDE],
):
    # Given: an OpenAI client that returns the no-match sentinel
    client = AsyncMock()
    response = MagicMock()
    response.output_text = json.dumps({
        "closest_matches": [{"candidate_index": -1, "rank": 0, "confidence": 0.0}]
    })
    response.usage = MagicMock(input_tokens=500, output_tokens=20, total_tokens=520)
    client.responses.create = AsyncMock(return_value=response)
    semaphore = asyncio.Semaphore(10)

    # When: match_column is called
    result, usage = await match_column(
        profile=column_profile,
        all_cdes=sample_cdes,
        client=client,
        semaphore=semaphore,
        developer_message="test",
        model="test-model",
        final_k=5,
    )

    # Then: a single No_Matches_Found result is returned
    assert len(result.matches) == 1
    assert result.matches[0].cde_key == "No_Matches_Found"
