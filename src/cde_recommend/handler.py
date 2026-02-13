"""Lambda entry point — imperative shell that parses, orchestrates, and formats."""

import asyncio
import json
import logging
from typing import Any

from cde_recommend.batch import match_columns_batch
from cde_recommend.db import load_cdes
from cde_recommend.openai_client import get_client
from cde_recommend.types import ColumnInput, ColumnResult, MatchRequest

logger = logging.getLogger(__name__)


def handler(event: dict, context: Any) -> dict[str, Any]:
    try:
        request = _parse_request(event)
    except (ValueError, TypeError) as e:
        return _error_response(400, str(e))

    try:
        all_cdes, _, resolved_number = load_cdes(
            request.data_commons_key, request.version_label, request.version_number
        )
    except (KeyError, ValueError) as e:
        return _error_response(404, str(e))

    if not all_cdes:
        return _error_response(404, "No CDEs found for that data model / version.")

    client = get_client()

    results, _ = asyncio.run(
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

    return _build_response(results)


# --- Private helpers ---


def _parse_request(event: dict) -> MatchRequest:
    """Accept netrias_client contract: target_schema, target_version, data dict."""
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

    dm_key = body.get("target_schema")
    if not dm_key or not isinstance(dm_key, str):
        raise ValueError("Missing required field 'target_schema' (string).")

    raw_data = body.get("data")
    if not raw_data or not isinstance(raw_data, dict):
        raise ValueError("Missing required field 'data' (non-empty dict).")

    columns = [
        ColumnInput(column_name=k, column_values=v)
        for k, v in raw_data.items()
    ]

    version_label, version_number = _parse_version(body.get("target_version"))
    return MatchRequest(
        data_commons_key=dm_key,
        columns=columns,
        version_label=version_label,
        version_number=version_number,
        top_k=int(body.get("top_k", 5)),
    )


def _parse_version(raw: object) -> tuple[str | None, int | None]:
    """'latest' and None both mean 'use default'; digit strings are version_number."""
    if raw is None or raw == "latest":
        return None, None
    if isinstance(raw, int):
        return None, raw
    if isinstance(raw, str):
        if raw.isdigit():
            return None, int(raw)
        return raw, None
    return None, None


def _build_response(results: list[ColumnResult]) -> dict[str, Any]:
    """Return netrias_client contract: results dict with target/similarity/target_cde_id."""
    return _success_response({
        "results": {
            r.column_name: [
                {
                    "target": m.cde_key,
                    "similarity": m.confidence,
                    "target_cde_id": m.cde_id,
                }
                for m in r.matches
            ]
            for r in results
        },
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
