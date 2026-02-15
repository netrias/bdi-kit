"""Multi-column batch orchestration with shared semaphore and three-layer caching."""

import asyncio
import logging

from openai import AsyncOpenAI

from cde_recommend.cache import compute_cache_key, get_cached_results, store_results
from cde_recommend.matcher import match_column
from cde_recommend.profiler import profile_column
from cde_recommend.serialization import build_developer_message, serialize_cde_candidates
from cde_recommend.types import CDE, CDEMatch, ColumnInput, ColumnResult, UsageStats

logger = logging.getLogger(__name__)


async def match_columns_batch(
    columns: list[ColumnInput],
    all_cdes: list[CDE],
    *,
    client: AsyncOpenAI,
    dm_key: str,
    version_number: int | None,
    model: str = "gpt-5-mini",
    concurrency: int = 50,
    top_k: int = 5,
    max_pv_samples: int = 12,
    chunk_threshold: int = 500,
    cde_chunk_size: int = 50,
    per_chunk_k: int = 3,
) -> tuple[list[ColumnResult], UsageStats]:
    total_usage = UsageStats()

    # Step 1: Check DynamoDB cache for all columns
    cache_keys = {
        col.column_name: compute_cache_key(
            dm_key, version_number, col.column_name, col.column_values
        )
        for col in columns
    }
    cached = get_cached_results(list(cache_keys.values()))

    # Map cache keys back to column names
    key_to_col = {v: k for k, v in cache_keys.items()}
    cached_by_name: dict[str, ColumnResult] = {}
    for k, result in cached.items():
        col_name = key_to_col.get(k)
        if col_name:
            cached_by_name[col_name] = result

    # Step 2: Build developer message ONCE for prompt caching
    cand_serialized = serialize_cde_candidates(all_cdes, max_pv_samples=max_pv_samples)
    developer_message = build_developer_message(cand_serialized, top_k)

    # Step 3: Fan out OpenAI calls for cache misses only
    semaphore = asyncio.Semaphore(concurrency)
    miss_columns = [col for col in columns if col.column_name not in cached_by_name]

    async def _process_column(col: ColumnInput) -> tuple[str, ColumnResult, UsageStats]:
        col_profile = profile_column(col.column_name, col.column_values)
        if col_profile.dtype == "numeric":
            return col.column_name, _no_match_result(col.column_name), UsageStats()
        result, usage = await match_column(
            profile=col_profile,
            all_cdes=all_cdes,
            client=client,
            semaphore=semaphore,
            developer_message=developer_message,
            model=model,
            final_k=top_k,
            chunk_threshold=chunk_threshold,
            cde_chunk_size=cde_chunk_size,
            per_chunk_k=per_chunk_k,
            max_pv_samples=max_pv_samples,
        )
        return col.column_name, result, usage

    tasks = [asyncio.create_task(_process_column(col)) for col in miss_columns]
    task_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Step 4: Collect results and store new ones in cache
    new_entries: list[tuple[str, ColumnResult]] = []
    results_by_name: dict[str, ColumnResult] = dict(cached_by_name)

    for i, result in enumerate(task_results):
        col = miss_columns[i]
        if isinstance(result, BaseException):
            logger.exception(
                "Matching failed for column %s", col.column_name, exc_info=result
            )
            continue
        col_name, col_result, usage = result
        total_usage.add(usage)
        results_by_name[col_name] = col_result
        new_entries.append((cache_keys[col_name], col_result))

    if new_entries:
        store_results(new_entries)

    # Preserve original column order
    final: list[ColumnResult] = []
    for col in columns:
        if col.column_name in results_by_name:
            final.append(results_by_name[col.column_name])

    return final, total_usage


def _no_match_result(column_name: str) -> ColumnResult:
    return ColumnResult(
        column_name=column_name,
        matches=[CDEMatch(cde_id=None, cde_key="No_Matches_Found", rank=0, confidence=0.0)],
    )
