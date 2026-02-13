from hypothesis import given, settings
from hypothesis import strategies as st

from cde_recommend.profiler import _clean_value, _infer_type, profile_column, serialize_column
from cde_recommend.types import ColumnProfile

# --- _infer_type ---


def test_infer_type_numeric():
    values = ["1.0", "2.5", "3", "100", "0.01", "-5"]
    assert _infer_type(values) == "numeric"


def test_infer_type_categorical():
    values = ["Male", "Female", "Male", "Female", "Unknown", "Male"]
    assert _infer_type(values) == "categorical"


def test_infer_type_id_like():
    values = [f"ID-{i:04d}" for i in range(100)]
    assert _infer_type(values) == "id_like"


def test_infer_type_free_text():
    values = [f"This is a long sentence number {i} with lots of words" for i in range(100)]
    assert _infer_type(values) == "free_text"


def test_infer_type_empty():
    assert _infer_type([]) == "mixed"


# --- _clean_value ---


def test_clean_value_strips_whitespace_and_newlines():
    assert _clean_value("  hello\nworld\t ") == "hello world"


def test_clean_value_truncates_long_strings():
    long_str = "x" * 200
    result = _clean_value(long_str)
    assert result is not None
    assert len(result) == 121  # 120 + ellipsis
    assert result.endswith("\u2026")


def test_clean_value_returns_none_for_empty():
    assert _clean_value("") is None
    assert _clean_value("   ") is None
    assert _clean_value(None) is None


# --- profile_column ---


def test_profile_column_returns_column_profile_with_correct_stats():
    raw = ["Male", "Female", None, "Male", "Unknown", ""]
    profile = profile_column("sex", raw)

    assert isinstance(profile, ColumnProfile)
    assert profile.column_name == "sex"
    assert profile.dtype == "categorical"
    assert profile.n_rows == 6
    assert profile.n_non_null == 4  # None and "" excluded
    assert 0.0 < profile.null_frac < 1.0
    assert profile.n_unique_estimate == 3
    assert len(profile.sample_values) <= 12


def test_profile_column_all_nulls():
    profile = profile_column("empty", [None, None, None])
    assert profile.n_non_null == 0
    assert profile.null_frac == 1.0
    assert profile.sample_values == []


def test_profile_column_deterministic_with_seed():
    raw = [f"val_{i}" for i in range(100)]
    p1 = profile_column("col", raw, seed=42)
    p2 = profile_column("col", raw, seed=42)
    assert p1.sample_values == p2.sample_values


# --- serialize_column ---


def test_serialize_column():
    profile = ColumnProfile(
        column_name="age",
        dtype="numeric",
        n_rows=100,
        n_non_null=95,
        null_frac=0.05,
        n_unique_estimate=50,
        sample_values=["25", "30", "45"],
    )
    result = serialize_column(profile)
    assert "Column: age" in result
    assert "Type: numeric" in result
    assert "['25', '30', '45']" in result


# --- Property-based tests ---


@given(st.text(min_size=1).filter(lambda s: s.strip()))
@settings(max_examples=200)
def test_clean_value_never_returns_empty_for_nonempty_stripped_input(s: str):
    result = _clean_value(s)
    # If the stripped input is non-empty, result should be non-None
    if s.strip():
        assert result is not None
        assert len(result) > 0
