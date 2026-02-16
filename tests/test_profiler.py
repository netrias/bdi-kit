from hypothesis import given, settings
from hypothesis import strategies as st

from cde_recommend.profiler import _clean_value, _infer_type, profile_column, serialize_column
from cde_recommend.types import ColumnProfile

# --- _infer_type ---


def test_infer_type_numeric():
    # Given: values that are all parseable as floats
    values = ["1.0", "2.5", "3", "100", "0.01", "-5"]

    # Then: inferred type is numeric
    assert _infer_type(values) == "numeric"


def test_infer_type_categorical():
    # Given: low-cardinality repeated string values
    values = ["Male", "Female", "Male", "Female", "Unknown", "Male"]

    # Then: inferred type is categorical
    assert _infer_type(values) == "categorical"


def test_infer_type_id_like():
    # Given: high-cardinality alphanumeric identifiers
    values = [f"ID-{i:04d}" for i in range(100)]

    # Then: inferred type is id_like
    assert _infer_type(values) == "id_like"


def test_infer_type_free_text():
    # Given: high-cardinality long strings
    values = [f"This is a long sentence number {i} with lots of words" for i in range(100)]

    # Then: inferred type is free_text
    assert _infer_type(values) == "free_text"


def test_infer_type_empty():
    # Given: no values
    # Then: falls back to "mixed"
    assert _infer_type([]) == "mixed"


# --- _clean_value ---


def test_clean_value_strips_whitespace_and_newlines():
    # Given: a string with leading/trailing whitespace and embedded newlines
    # When: cleaned
    # Then: whitespace is collapsed to single spaces
    assert _clean_value("  hello\nworld\t ") == "hello world"


def test_clean_value_truncates_long_strings():
    # Given: a string longer than the 120-char max
    long_str = "x" * 200
    result = _clean_value(long_str)

    # Then: truncated to 120 chars + ellipsis
    assert result is not None
    assert len(result) == 121
    assert result.endswith("\u2026")


def test_clean_value_returns_none_for_empty():
    # Given: empty, whitespace-only, or None values
    # Then: all return None
    assert _clean_value("") is None
    assert _clean_value("   ") is None
    assert _clean_value(None) is None


# --- profile_column ---


def test_profile_column_returns_column_profile_with_correct_stats():
    # Given: a mix of valid values, None, and empty string
    raw = ["Male", "Female", None, "Male", "Unknown", ""]

    # When: profiled
    profile = profile_column("sex", raw)

    # Then: stats reflect the non-null values
    assert isinstance(profile, ColumnProfile)
    assert profile.column_name == "sex"
    assert profile.dtype == "categorical"
    assert profile.n_rows == 6
    assert profile.n_non_null == 4  # None and "" excluded
    assert 0.0 < profile.null_frac < 1.0
    assert profile.n_unique_estimate == 3
    assert len(profile.sample_values) <= 12


def test_profile_column_all_nulls():
    # Given: only None values
    profile = profile_column("empty", [None, None, None])

    # Then: null_frac is 1.0 and no samples
    assert profile.n_non_null == 0
    assert profile.null_frac == 1.0
    assert profile.sample_values == []


def test_profile_column_deterministic_with_seed():
    # Given: the same input and seed
    raw = [f"val_{i}" for i in range(100)]

    # When: profiled twice
    p1 = profile_column("col", raw, seed=42)
    p2 = profile_column("col", raw, seed=42)

    # Then: sample values are identical
    assert p1.sample_values == p2.sample_values


# --- serialize_column ---


def test_serialize_column():
    # Given: a numeric column profile
    profile = ColumnProfile(
        column_name="age",
        dtype="numeric",
        n_rows=100,
        n_non_null=95,
        null_frac=0.05,
        n_unique_estimate=50,
        sample_values=["25", "30", "45"],
    )

    # When: serialized
    result = serialize_column(profile)

    # Then: output includes column name, type, and sample values
    assert "Column: age" in result
    assert "Type: numeric" in result
    assert "['25', '30', '45']" in result


# --- Property-based tests ---


@given(st.text(min_size=1).filter(lambda s: s.strip()))
@settings(max_examples=200)
def test_clean_value_never_returns_empty_for_nonempty_stripped_input(s: str):
    """Non-empty stripped strings always produce a non-None, non-empty result."""
    result = _clean_value(s)
    if s.strip():
        assert result is not None
        assert len(result) > 0
