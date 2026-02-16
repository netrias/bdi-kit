import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cde_recommend.batch import match_columns_batch
from cde_recommend.types import CDE, CDEMatch, ColumnInput, ColumnResult


@pytest.fixture
def mock_openai_client() -> AsyncMock:
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


@pytest.fixture
def columns() -> list[ColumnInput]:
    return [
        ColumnInput(column_name="sex", column_values=["Male", "Female", "Unknown"] * 10),
        ColumnInput(column_name="race", column_values=["White", "Black", "Asian"] * 10),
    ]


@pytest.mark.asyncio
@patch("cde_recommend.batch.get_cached_results", return_value={})
@patch("cde_recommend.batch.store_results")
async def test_batch_processes_multiple_columns(
    mock_store: MagicMock,
    mock_cache_get: MagicMock,
    columns: list[ColumnInput],
    sample_cdes: list[CDE],
    mock_openai_client: AsyncMock,
):
    # Given: two columns with no cached results

    # When: batch processes both
    results, usage = await match_columns_batch(
        columns=columns,
        all_cdes=sample_cdes,
        client=mock_openai_client,
        dm_key="ccdi",
        version_number=1,
    )

    # Then: both columns have results with positive token usage
    assert len(results) == 2
    assert results[0].column_name == "sex"
    assert results[1].column_name == "race"
    assert usage.total_tokens > 0
    mock_store.assert_called_once()


@pytest.mark.asyncio
@patch("cde_recommend.batch.get_cached_results", return_value={})
@patch("cde_recommend.batch.store_results")
async def test_batch_handles_partial_failure_gracefully(
    mock_store: MagicMock,
    mock_cache_get: MagicMock,
    sample_cdes: list[CDE],
):
    # Given: two columns where the second OpenAI call raises
    client = AsyncMock()
    success_resp = MagicMock()
    success_resp.output_text = json.dumps({
        "closest_matches": [{"candidate_index": 0, "rank": 1, "confidence": 0.9}]
    })
    success_resp.usage = MagicMock(input_tokens=500, output_tokens=25, total_tokens=525)

    call_count = 0

    async def side_effect(**kwargs: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("OpenAI API error")
        return success_resp

    client.responses.create = AsyncMock(side_effect=side_effect)
    columns = [
        ColumnInput(column_name="sex", column_values=["Male", "Female"] * 10),
        ColumnInput(column_name="bad_col", column_values=["x", "y"]),
    ]

    # When: batch processes both
    results, usage = await match_columns_batch(
        columns=columns,
        all_cdes=sample_cdes,
        client=client,
        dm_key="ccdi",
        version_number=1,
    )

    # Then: the successful column is still present
    col_names = [r.column_name for r in results]
    assert "sex" in col_names


@pytest.mark.asyncio
@patch("cde_recommend.batch.store_results")
async def test_batch_skips_openai_for_cached_columns(
    mock_store: MagicMock,
    sample_cdes: list[CDE],
    mock_openai_client: AsyncMock,
):
    # Given: "sex" column has a cached result, "race" does not
    cached_result = ColumnResult(
        column_name="sex",
        matches=[CDEMatch(cde_id=1, cde_key="gender", rank=1, confidence=0.95)],
    )
    columns = [
        ColumnInput(column_name="sex", column_values=["Male", "Female"] * 10),
        ColumnInput(column_name="race", column_values=["White", "Black", "Asian"] * 10),
    ]
    from cde_recommend.cache import compute_cache_key

    sex_key = compute_cache_key("ccdi", 1, "sex", ["Male", "Female"] * 10)

    # When: batch processes both
    with patch(
        "cde_recommend.batch.get_cached_results",
        return_value={sex_key: cached_result},
    ):
        results, usage = await match_columns_batch(
            columns=columns,
            all_cdes=sample_cdes,
            client=mock_openai_client,
            dm_key="ccdi",
            version_number=1,
        )

    # Then: sex uses cached result and only race triggers an OpenAI call
    assert len(results) == 2
    sex_result = next(r for r in results if r.column_name == "sex")
    assert sex_result.matches[0].cde_key == "gender"
    assert mock_openai_client.responses.create.call_count == 1


@pytest.mark.asyncio
@patch("cde_recommend.batch.get_cached_results", return_value={})
@patch("cde_recommend.batch.store_results")
async def test_batch_stores_new_results_in_cache(
    mock_store: MagicMock,
    mock_cache_get: MagicMock,
    sample_cdes: list[CDE],
    mock_openai_client: AsyncMock,
):
    # Given: one uncached column
    columns = [
        ColumnInput(column_name="sex", column_values=["Male", "Female"] * 10),
    ]

    # When: batch processes it
    results, _ = await match_columns_batch(
        columns=columns,
        all_cdes=sample_cdes,
        client=mock_openai_client,
        dm_key="ccdi",
        version_number=1,
    )

    # Then: store_results is called with the new result
    mock_store.assert_called_once()
    stored_entries = mock_store.call_args[0][0]
    assert len(stored_entries) == 1
    cache_key, col_result = stored_entries[0]
    assert col_result.column_name == "sex"


@pytest.mark.asyncio
@patch("cde_recommend.batch.get_cached_results", return_value={})
@patch("cde_recommend.batch.store_results")
async def test_batch_skips_numeric_columns(
    mock_store: MagicMock,
    mock_cache_get: MagicMock,
    sample_cdes: list[CDE],
    mock_openai_client: AsyncMock,
):
    """
    Given: One categorical column and one numeric column
      AND: No cached results exist
    When: match_columns_batch processes both
    Then: Numeric column gets No_Matches_Found without an LLM call
      AND: Categorical column is still sent to the LLM
    """
    columns = [
        ColumnInput(column_name="sex", column_values=["Male", "Female", "Unknown"] * 10),
        ColumnInput(column_name="age_at_diagnosis", column_values=["25.0", "30.5", "45.2"]),
    ]

    results, usage = await match_columns_batch(
        columns=columns,
        all_cdes=sample_cdes,
        client=mock_openai_client,
        dm_key="ccdi",
        version_number=1,
    )

    # Both columns should have results
    assert len(results) == 2
    result_map = {r.column_name: r for r in results}

    # Numeric column: No_Matches_Found, no LLM call
    age_result = result_map["age_at_diagnosis"]
    assert age_result.matches[0].cde_key == "No_Matches_Found"
    assert age_result.matches[0].confidence == 0.0

    # Categorical column: real LLM match
    sex_result = result_map["sex"]
    assert sex_result.matches[0].cde_key != "No_Matches_Found"

    # Only 1 OpenAI call (for "sex", not "age_at_diagnosis")
    assert mock_openai_client.responses.create.call_count == 1


@pytest.mark.asyncio
@patch("cde_recommend.batch.get_cached_results", return_value={})
@patch("cde_recommend.batch.store_results")
async def test_batch_skips_id_like_columns(
    mock_store: MagicMock,
    mock_cache_get: MagicMock,
    sample_cdes: list[CDE],
    mock_openai_client: AsyncMock,
):
    """
    Given: One categorical column and one id_like column
      AND: No cached results exist
    When: match_columns_batch processes both
    Then: id_like column gets No_Matches_Found without an LLM call
      AND: Categorical column is still sent to the LLM
    """
    columns = [
        ColumnInput(column_name="sex", column_values=["Male", "Female", "Unknown"] * 10),
        ColumnInput(
            column_name="sample_id",
            column_values=[f"SAM-{i:04d}" for i in range(100)],
        ),
    ]

    results, usage = await match_columns_batch(
        columns=columns,
        all_cdes=sample_cdes,
        client=mock_openai_client,
        dm_key="ccdi",
        version_number=1,
    )

    # Both columns should have results
    assert len(results) == 2
    result_map = {r.column_name: r for r in results}

    # id_like column: No_Matches_Found, no LLM call
    id_result = result_map["sample_id"]
    assert id_result.matches[0].cde_key == "No_Matches_Found"
    assert id_result.matches[0].confidence == 0.0

    # Categorical column: real LLM match
    sex_result = result_map["sex"]
    assert sex_result.matches[0].cde_key != "No_Matches_Found"

    # Only 1 OpenAI call (for "sex", not "sample_id")
    assert mock_openai_client.responses.create.call_count == 1
