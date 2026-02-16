"""Pure functions for column profiling and serialization.

Changes when profiling heuristics change.
"""

import random
import re
from collections import Counter
from collections.abc import Sequence

from cde_recommend.types import ColumnProfile

_MAX_STATS_SAMPLE = 5000
_MAX_TYPE_SAMPLE = 200
_NUMERIC_THRESHOLD = 0.9
_UNIQUENESS_THRESHOLD = 0.9
_ALNUM_THRESHOLD = 0.8
_CATEGORICAL_UNIQUENESS_THRESHOLD = 0.3
_CATEGORICAL_AVG_LEN_THRESHOLD = 25


def profile_column(
    name: str,
    raw_values: Sequence[object],
    *,
    seed: int = 0,
    max_samples: int = 12,
) -> ColumnProfile:
    cleaned = [v for v in (_clean_value(x) for x in raw_values) if v is not None]
    n_rows = len(raw_values)
    n_non_null = len(cleaned)
    null_frac = 1.0 - (n_non_null / max(1, n_rows))

    stats_sample = cleaned[:_MAX_STATS_SAMPLE]
    n_unique_estimate = len(set(stats_sample))
    dtype = _infer_type(stats_sample)

    sample_values = _sample_values(stats_sample, dtype, max_samples, seed)

    return ColumnProfile(
        column_name=name,
        dtype=dtype,
        n_rows=n_rows,
        n_non_null=n_non_null,
        null_frac=null_frac,
        n_unique_estimate=n_unique_estimate,
        sample_values=sample_values,
    )


def serialize_column(profile: ColumnProfile) -> str:
    return (
        f"Column: {profile.column_name}, "
        f"Type: {profile.dtype}, "
        f"Sample values: {profile.sample_values}"
    )


# --- Private helpers ---


def _clean_value(v: object, max_len: int = 120) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    s = s.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    if len(s) > max_len:
        s = s[:max_len] + "\u2026"
    return s


def _infer_type(values: list[str]) -> str:
    if not values:
        return "mixed"

    sample = values[:_MAX_TYPE_SAMPLE]
    sample_len = len(sample)

    if _is_numeric(sample, sample_len):
        return "numeric"
    if _is_id_like(values, sample, sample_len):
        return "id_like"
    return _categorical_or_free_text(values, sample, sample_len)


def _is_numeric(sample: list[str], sample_len: int) -> bool:
    num = 0
    for s in sample:
        try:
            float(s)
            num += 1
        except ValueError:
            pass
    return num / max(1, sample_len) > _NUMERIC_THRESHOLD


def _is_id_like(values: list[str], sample: list[str], sample_len: int) -> bool:
    uniq_ratio = len(set(values)) / max(1, len(values))
    if uniq_ratio <= _UNIQUENESS_THRESHOLD:
        return False
    alnum_count = sum(
        1 for s in sample if re.fullmatch(r"[A-Za-z0-9._\-:/]+", s) is not None
    )
    return alnum_count / max(1, sample_len) > _ALNUM_THRESHOLD


def _categorical_or_free_text(values: list[str], sample: list[str], sample_len: int) -> str:
    uniq_ratio = len(set(values)) / max(1, len(values))
    avg_len = sum(len(s) for s in sample) / max(1, sample_len)
    if uniq_ratio < _CATEGORICAL_UNIQUENESS_THRESHOLD or avg_len < _CATEGORICAL_AVG_LEN_THRESHOLD:
        return "categorical"
    return "free_text"


def _sample_values(cleaned: list[str], dtype: str, max_samples: int, seed: int) -> list[str]:
    if not cleaned:
        return []

    rng = random.Random(seed)

    if dtype in ("categorical", "mixed"):
        raw = _sample_categorical(cleaned, max_samples, rng)
    else:
        pool = list(cleaned)
        rng.shuffle(pool)
        raw = pool[:max_samples]

    return _dedupe_preserve_order(raw, max_samples)


def _sample_categorical(cleaned: list[str], max_samples: int, rng: random.Random) -> list[str]:
    # Top-frequency ensures the LLM sees dominant values; tail adds rare label coverage.

    counts = Counter(cleaned[:_MAX_STATS_SAMPLE])
    top = [v for v, _ in counts.most_common(5)]
    tail = list(set(cleaned[:_MAX_STATS_SAMPLE]) - set(top))
    rng.shuffle(tail)
    return top + tail[: max(0, max_samples - len(top))]


def _dedupe_preserve_order(values: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        if v not in seen:
            seen.add(v)
            out.append(v)
        if len(out) >= limit:
            break
    return out
