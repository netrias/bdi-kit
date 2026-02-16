from cde_recommend.serialization import (
    build_developer_message,
    build_user_message,
    serialize_cde_candidates,
)
from cde_recommend.types import CDE


def test_serialize_cde_truncates_pvs_with_more_indicator():
    # Given: a CDE with 20 PV values and a max_pv_samples of 5
    cde = CDE(cde_id=1, cde_key="status", pv_values=tuple(f"val_{i}" for i in range(20)))

    # When: serialized
    result = serialize_cde_candidates([cde], max_pv_samples=5)

    # Then: truncation indicator and full count are shown
    assert len(result) == 1
    assert "...(+15 more)" in result[0]
    assert "PV_count=20" in result[0]


def test_serialize_cde_no_truncation_when_within_limit():
    # Given: a CDE with fewer PVs than the limit
    cde = CDE(cde_id=1, cde_key="gender", pv_values=("Male", "Female"))

    # When: serialized with max_pv_samples=12
    result = serialize_cde_candidates([cde], max_pv_samples=12)

    # Then: no truncation indicator
    assert len(result) == 1
    assert "...(+" not in result[0]
    assert "PV_count=2" in result[0]


def test_build_developer_message_includes_all_candidate_indices():
    # Given: 3 serialized CDE candidates
    candidates = [
        "CDE: gender (id=1), PV_count=3, PV_samples=['Male', 'Female', 'Unknown']",
        "CDE: age (id=2), PV_count=0, PV_samples=[]",
        "CDE: ethnicity (id=3), PV_count=3, PV_samples=['Hispanic', 'Non-Hispanic', 'Unknown']",
    ]

    # When: developer message is built
    msg = build_developer_message(candidates, top_k=5)

    # Then: each candidate is prefixed with its zero-based index
    assert "0: CDE: gender" in msg
    assert "1: CDE: age" in msg
    assert "2: CDE: ethnicity" in msg
    assert "up to 5 closest matches" in msg


def test_build_developer_message_contains_matching_rules():
    # Given: any candidate list
    msg = build_developer_message(["CDE: test (id=1), PV_count=0, PV_samples=[]"], top_k=3)

    # Then: no-match sentinel rules and output format are specified
    assert "candidate_index -1" in msg
    assert "rank 0" in msg
    assert "confidence 0.0" in msg
    assert "strict JSON" in msg


def test_build_user_message_contains_source_column():
    # Given: a serialized column profile string
    msg = build_user_message("Column: sex, Type: categorical, Sample values: ['M', 'F']")

    # Then: message wraps it with SOURCE label
    assert "SOURCE:" in msg
    assert "Column: sex" in msg
