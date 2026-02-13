"""RDS connection and CDE loading with warm-start cache. Changes when the DB schema changes."""

import os
from typing import Any

import psycopg
from psycopg.rows import DictRow, dict_row

from cde_recommend.types import CDE

_cde_cache: dict[tuple[str, str], list[CDE]] = {}


def load_cdes(
    dm_key: str,
    version_label: str | None,
    version_number: int | None,
) -> tuple[list[CDE], str, int | None]:
    with _connect() as conn, conn.cursor() as cur:
        mv = _resolve_model_version(cur, dm_key, version_label, version_number)
        dmv_id = mv["data_model_version_id"]
        resolved_label: str = mv.get("version_label") or ""
        resolved_number: int | None = mv.get("version_number")
        version_key = resolved_label or (
            str(resolved_number) if resolved_number is not None else "unknown"
        )

        cache_key = (dm_key, version_key)
        if cache_key in _cde_cache:
            return _cde_cache[cache_key], (resolved_label or version_key), resolved_number

        cdes = _fetch_cdes_for_version(cur, dmv_id)
        _cde_cache[cache_key] = cdes
        return cdes, (resolved_label or version_key), resolved_number


# --- Private helpers ---


def _connect() -> psycopg.Connection[DictRow]:
    """psycopg stubs don't propagate row_factory to Connection type parameter."""
    user = os.getenv("DB_USER")
    pwd = os.getenv("DB_PASSWORD")
    if not user or not pwd:
        raise RuntimeError("Missing DB creds. Set DB_USER and DB_PASSWORD.")
    return psycopg.connect(  # type: ignore[return-value]
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.environ["DB_NAME"],
        user=user,
        password=pwd,
        sslmode=os.getenv("DB_SSLMODE", "require"),
        row_factory=dict_row,  # type: ignore[arg-type]
        connect_timeout=10,
    )


def _resolve_model_version(
    cur: psycopg.Cursor[DictRow],
    dm_key: str,
    version_label: str | None,
    version_number: int | None,
) -> dict[str, Any]:
    if version_label:
        cur.execute(
            """
            SELECT dc.id AS data_commons_id,
                   dmv.id AS data_model_version_id,
                   dmv.version_label,
                   dmv.version_number
            FROM data_commons dc
            JOIN data_model_version dmv ON dmv.data_commons_id = dc.id
            WHERE dc.key = %s AND dmv.version_label = %s
            """,
            (dm_key, version_label),
        )
    elif version_number is not None:
        cur.execute(
            """
            SELECT dc.id AS data_commons_id,
                   dmv.id AS data_model_version_id,
                   dmv.version_label,
                   dmv.version_number
            FROM data_commons dc
            JOIN data_model_version dmv ON dmv.data_commons_id = dc.id
            WHERE dc.key = %s AND dmv.version_number = %s
            """,
            (dm_key, int(version_number)),
        )
    else:
        cur.execute(
            """
            SELECT dc.id AS data_commons_id,
                   dmv.id AS data_model_version_id,
                   dmv.version_label,
                   dmv.version_number
            FROM data_commons dc
            JOIN data_model_version dmv ON dmv.data_commons_id = dc.id
            WHERE dc.key = %s
            ORDER BY dmv.is_default DESC, dmv.valid_from DESC NULLS LAST, dmv.id DESC
            LIMIT 1
            """,
            (dm_key,),
        )

    row = cur.fetchone()
    if not row:
        raise KeyError("Unknown data model key or version")
    return dict(row)


def _fetch_cdes_for_version(
    cur: psycopg.Cursor[DictRow], dmv_id: int
) -> list[CDE]:
    cur.execute(
        """
        SELECT
          c.id     AS cde_id,
          c.key    AS cde_key,
          pv.value AS permissible_value
        FROM cde_version_in_model cvim
        JOIN cde_version cv ON cv.id = cvim.cde_version_id
        JOIN cde c ON c.id = cv.cde_id
        LEFT JOIN permissible_value pv
          ON pv.cde_version_id = cv.id AND pv.is_active
        WHERE cvim.data_model_version_id = %s
        ORDER BY c.key, pv.sort_order NULLS LAST, pv.value
        """,
        (dmv_id,),
    )

    cde_map: dict[tuple[int, str], list[str]] = {}
    while True:
        rows = cur.fetchmany(5000)
        if not rows:
            break
        for r in rows:
            cid = int(r["cde_id"])
            ckey: str = r["cde_key"]
            pv = r["permissible_value"]
            cde_map.setdefault((cid, ckey), [])
            if pv is not None and str(pv).strip():
                cde_map[(cid, ckey)].append(str(pv))

    return [
        CDE(cde_id=cid, cde_key=ckey, pv_values=tuple(pvs))
        for (cid, ckey), pvs in cde_map.items()
    ]
