"""Single-column matching: route to single-call or chunked based on CDE count."""

import asyncio
import logging

from openai import AsyncOpenAI

from cde_recommend.openai_client import call_rank_indices
from cde_recommend.profiler import serialize_column
from cde_recommend.serialization import (
    build_developer_message,
    build_user_message,
    serialize_cde_candidates,
)
from cde_recommend.types import (
    CDE,
    CDEMatch,
    ColumnProfile,
    ColumnResult,
    PotentialMatchIndex,
    UsageStats,
)

logger = logging.getLogger(__name__)


async def match_column(
    profile: ColumnProfile,
    all_cdes: list[CDE],
    *,
    client: AsyncOpenAI,
    semaphore: asyncio.Semaphore,
    developer_message: str,
    model: str = "gpt-5-mini",
    final_k: int = 5,
    chunk_threshold: int = 500,
    cde_chunk_size: int = 50,
    per_chunk_k: int = 3,
    max_pv_samples: int = 12,
) -> tuple[ColumnResult, UsageStats]:
    """Routes to single-call (default for <=chunk_threshold CDEs) or chunked fallback."""
    source_serialized = serialize_column(profile)
    user_message = build_user_message(source_serialized)

    if len(all_cdes) <= chunk_threshold:
        return await _match_single_call(
            profile=profile,
            all_cdes=all_cdes,
            client=client,
            semaphore=semaphore,
            developer_message=developer_message,
            user_message=user_message,
            model=model,
            final_k=final_k,
        )
    return await _match_chunked(
        profile=profile,
        all_cdes=all_cdes,
        client=client,
        semaphore=semaphore,
        user_message=user_message,
        model=model,
        final_k=final_k,
        cde_chunk_size=cde_chunk_size,
        per_chunk_k=per_chunk_k,
        max_pv_samples=max_pv_samples,
    )


async def _match_single_call(
    *,
    profile: ColumnProfile,
    all_cdes: list[CDE],
    client: AsyncOpenAI,
    semaphore: asyncio.Semaphore,
    developer_message: str,
    user_message: str,
    model: str,
    final_k: int,
) -> tuple[ColumnResult, UsageStats]:
    """All CDEs in one prompt — default for sets <=500."""
    async with semaphore:
        idx_matches, usage = await call_rank_indices(
            client=client,
            model=model,
            developer_message=developer_message,
            user_message=user_message,
        )

    matches = _resolve_indices(idx_matches, all_cdes, profile.column_name, final_k)
    return ColumnResult(column_name=profile.column_name, matches=matches), usage


async def _match_chunked(
    *,
    profile: ColumnProfile,
    all_cdes: list[CDE],
    client: AsyncOpenAI,
    semaphore: asyncio.Semaphore,
    user_message: str,
    model: str,
    final_k: int,
    cde_chunk_size: int,
    per_chunk_k: int,
    max_pv_samples: int,
) -> tuple[ColumnResult, UsageStats]:
    """Chunk -> shortlist -> aggregate -> final rank. Fallback for >500 CDEs."""
    chunks = [all_cdes[i : i + cde_chunk_size] for i in range(0, len(all_cdes), cde_chunk_size)]
    total_usage = UsageStats()

    async def _bounded_chunk(chunk: list[CDE]) -> list[CDE]:
        async with semaphore:
            cand_serialized = serialize_cde_candidates(chunk, max_pv_samples=max_pv_samples)
            chunk_dev_msg = build_developer_message(cand_serialized, per_chunk_k)
            idx_matches, usage = await call_rank_indices(
                client=client,
                model=model,
                developer_message=chunk_dev_msg,
                user_message=user_message,
            )
        total_usage.add(usage)

        picked: list[CDE] = []
        for m in idx_matches:
            if m.candidate_index == -1:
                continue
            if 0 <= m.candidate_index < len(chunk):
                picked.append(chunk[m.candidate_index])
            else:
                logger.warning(
                    "Invalid chunk index %d (max %d) for column %s",
                    m.candidate_index,
                    len(chunk) - 1,
                    profile.column_name,
                )
        return picked

    tasks = [asyncio.create_task(_bounded_chunk(c)) for c in chunks]
    chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Aggregate and dedupe shortlisted CDEs
    seen: set[int] = set()
    aggregated: list[CDE] = []
    for result in chunk_results:
        if isinstance(result, BaseException):
            logger.exception(
                "Chunk matching failed for column %s",
                profile.column_name,
                exc_info=result,
            )
            continue
        for c in result:
            if c.cde_id not in seen:
                seen.add(c.cde_id)
                aggregated.append(c)

    if not aggregated:
        no_match = CDEMatch(cde_id=None, cde_key="No_Matches_Found", rank=0, confidence=0.0)
        return ColumnResult(column_name=profile.column_name, matches=[no_match]), total_usage

    # Final ranking over aggregated shortlist
    final_cand = serialize_cde_candidates(aggregated, max_pv_samples=max_pv_samples)
    final_dev_msg = build_developer_message(final_cand, final_k)

    async with semaphore:
        idx_matches, usage = await call_rank_indices(
            client=client,
            model=model,
            developer_message=final_dev_msg,
            user_message=user_message,
        )
    total_usage.add(usage)

    matches = _resolve_indices(idx_matches, aggregated, profile.column_name, final_k)
    return ColumnResult(column_name=profile.column_name, matches=matches), total_usage


def _resolve_indices(
    index_matches: list[PotentialMatchIndex],
    cdes: list[CDE],
    column_name: str,
    limit: int,
) -> list[CDEMatch]:
    resolved: list[CDEMatch] = []
    n = len(cdes)

    for m in index_matches:
        if m.candidate_index == -1:
            resolved.append(CDEMatch(
                cde_id=None, cde_key="No_Matches_Found", rank=m.rank, confidence=m.confidence,
            ))
        elif 0 <= m.candidate_index < n:
            c = cdes[m.candidate_index]
            resolved.append(
                CDEMatch(cde_id=c.cde_id, cde_key=c.cde_key, rank=m.rank, confidence=m.confidence)
            )
        else:
            logger.warning(
                "Invalid index %d (max %d) for column %s",
                m.candidate_index,
                n - 1,
                column_name,
            )

    return resolved[:limit]
