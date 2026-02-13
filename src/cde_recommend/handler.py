"""Lambda entry point — imperative shell that parses, orchestrates, and formats."""

import asyncio
import json
import logging
from typing import Any

from cde_recommend.batch import match_columns_batch
from cde_recommend.db import load_cdes
from cde_recommend.openai_client import get_client
from cde_recommend.types import ColumnInput, ColumnResult, MatchRequest, UsageStats

logger = logging.getLogger(__name__)


def handler(event: dict, context: Any) -> dict[str, Any]:
    try:
        request = _parse_request(event)
    except (ValueError, TypeError) as e:
        return _error_response(400, str(e))

    try:
        all_cdes, resolved_label, resolved_number = load_cdes(
            request.data_commons_key, request.version_label, request.version_number
        )
    except KeyError as e:
        return _error_response(404, str(e))

    if not all_cdes:
        return _error_response(404, "No CDEs found for that data model / version.")

    client = get_client()

    results, usage = asyncio.run(
        match_columns_batch(
            columns=request.columns,
            all_cdes=all_cdes,
            client=client,
            dm_key=request.data_commons_key,
            version_number=resolved_number,
            model=request.model,
            concurrency=request.concurrency,
            top_k=request.top_k,
            max_pv_samples=request.max_pv_samples,
            chunk_threshold=request.chunk_threshold,
            cde_chunk_size=request.cde_chunk_size,
            per_chunk_k=request.per_chunk_k,
        )
    )

    mode = "single_call" if len(all_cdes) <= request.chunk_threshold else "chunked"
    return _build_response(request, resolved_label, resolved_number, all_cdes, results, usage, mode)


# --- Private helpers ---


def _parse_request(event: dict) -> MatchRequest:
    raw = event.get("body", "")
    body: dict
    if isinstance(raw, str) and raw:
        body = json.loads(raw)
    elif isinstance(raw, dict):
        body = raw
    else:
        raise ValueError("Request body must be a JSON object.")

    if not isinstance(body, dict):
        raise ValueError("Request body must be a JSON object.")

    dm_key = body.get("data_commons_key")
    if not dm_key or not isinstance(dm_key, str):
        raise ValueError("Missing required field 'data_commons_key' (string).")

    raw_columns = body.get("columns")
    if not raw_columns or not isinstance(raw_columns, list):
        raise ValueError("Missing required field 'columns' (non-empty list).")

    columns: list[ColumnInput] = []
    for i, col in enumerate(raw_columns):
        if not isinstance(col, dict):
            raise ValueError(f"columns[{i}] must be an object.")
        name = col.get("column_name")
        values = col.get("column_values")
        if not name or not isinstance(name, str):
            raise ValueError(f"columns[{i}].column_name is required (string).")
        if not isinstance(values, list):
            raise ValueError(f"columns[{i}].column_values is required (list).")
        columns.append(ColumnInput(column_name=name, column_values=values))

    return MatchRequest(
        data_commons_key=dm_key,
        columns=columns,
        version_label=body.get("version_label"),
        version_number=body.get("version_number"),
        model=body.get("model", "gpt-5-mini"),
        top_k=int(body.get("top_k", 5)),
        concurrency=int(body.get("concurrency", 50)),
        max_pv_samples=int(body.get("max_pv_samples", 12)),
        chunk_threshold=int(body.get("chunk_threshold", 500)),
        cde_chunk_size=int(body.get("cde_chunk_size", 50)),
        per_chunk_k=int(body.get("per_chunk_k", 3)),
    )


def _build_response(
    request: MatchRequest,
    version_label: str,
    version_number: int | None,
    all_cdes: list,
    results: list[ColumnResult],
    usage: UsageStats,
    mode: str,
) -> dict[str, Any]:
    return _success_response({
        "data_commons_key": request.data_commons_key,
        "version_label": version_label,
        "version_number": version_number,
        "candidate_cde_count": len(all_cdes),
        "params": {
            "model": request.model,
            "top_k": request.top_k,
            "concurrency": request.concurrency,
            "mode": mode,
        },
        "results": [
            {
                "column_name": r.column_name,
                "matches": [
                    {"cde_id": m.cde_id, "cde_key": m.cde_key, "rank": m.rank}
                    for m in r.matches
                ],
            }
            for r in results
        ],
        "usage": usage.to_dict(),
    })


def _success_response(body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }


def _error_response(status: int, message: str) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps({"error": message}),
    }
