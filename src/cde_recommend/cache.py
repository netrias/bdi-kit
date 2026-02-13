"""DynamoDB result caching: check before OpenAI, store after.

Changes when cache strategy changes.
"""

import hashlib
import json
import logging
import os
import time

import boto3

from cde_recommend.types import CDEMatch, ColumnResult

logger = logging.getLogger(__name__)

_TABLE_NAME = "cde_recommendation_cache"
_TTL_DAYS = 30
_BATCH_READ_LIMIT = 100
_BATCH_WRITE_LIMIT = 25

_table_ref = None


def compute_cache_key(
    dm_key: str,
    version_number: int | None,
    column_name: str,
    column_values: list[str],
) -> str:
    """Deterministic SHA-256 hash of all inputs that affect matching output."""
    payload = json.dumps(
        {
            "dm_key": dm_key,
            "version_number": version_number,
            "column_name": column_name,
            "column_values": sorted(column_values),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def get_cached_results(keys: list[str]) -> dict[str, ColumnResult]:
    table_name = _get_table_name()
    dynamodb = _get_resource()
    results: dict[str, ColumnResult] = {}

    for i in range(0, len(keys), _BATCH_READ_LIMIT):
        batch_keys = keys[i : i + _BATCH_READ_LIMIT]
        request_items = {
            table_name: {"Keys": [{"cache_key": k} for k in batch_keys]}
        }
        try:
            resp = dynamodb.batch_get_item(RequestItems=request_items)  # type: ignore[attr-defined]
        except Exception:
            logger.exception("DynamoDB batch_get_item failed")
            continue

        for item in resp.get("Responses", {}).get(table_name, []):
            cache_key = item["cache_key"]
            result_data = json.loads(item["result"])
            results[cache_key] = _deserialize_column_result(result_data)

    return results


def store_results(entries: list[tuple[str, ColumnResult]]) -> None:
    table_name = _get_table_name()
    dynamodb = _get_resource()
    ttl = int(time.time()) + (_TTL_DAYS * 86400)

    for i in range(0, len(entries), _BATCH_WRITE_LIMIT):
        batch = entries[i : i + _BATCH_WRITE_LIMIT]
        request_items = {
            table_name: [
                {
                    "PutRequest": {
                        "Item": {
                            "cache_key": cache_key,
                            "result": json.dumps(_serialize_column_result(result)),
                            "created_at": int(time.time()),
                            "ttl": ttl,
                        }
                    }
                }
                for cache_key, result in batch
            ]
        }
        try:
            dynamodb.batch_write_item(RequestItems=request_items)  # type: ignore[attr-defined]
        except Exception:
            logger.exception("DynamoDB batch_write_item failed")


# --- Private helpers ---


def _get_table_name() -> str:
    return os.getenv("CACHE_TABLE_NAME", _TABLE_NAME)


def _get_resource():  # type: ignore[no-untyped-def]
    """boto3 service resources are dynamically typed."""
    return boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-2"))


def _serialize_column_result(result: ColumnResult) -> dict:
    return {
        "column_name": result.column_name,
        "matches": [
            {"cde_id": m.cde_id, "cde_key": m.cde_key, "rank": m.rank, "confidence": m.confidence}
            for m in result.matches
        ],
    }


def _deserialize_column_result(data: dict) -> ColumnResult:
    return ColumnResult(
        column_name=data["column_name"],
        matches=[
            CDEMatch(
                cde_id=m["cde_id"],
                cde_key=m["cde_key"],
                rank=m["rank"],
                confidence=m.get("confidence", 0.0),
            )
            for m in data["matches"]
        ],
    )
