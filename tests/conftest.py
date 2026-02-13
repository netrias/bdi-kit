import pytest

from cde_recommend.types import CDE, CDEMatch, ColumnResult


@pytest.fixture
def sample_cdes() -> list[CDE]:
    return [
        CDE(cde_id=1, cde_key="gender", pv_values=("Male", "Female", "Unknown")),
        CDE(cde_id=2, cde_key="age_at_diagnosis", pv_values=()),
        CDE(cde_id=3, cde_key="ethnicity", pv_values=("Hispanic", "Non-Hispanic", "Unknown")),
        CDE(cde_id=4, cde_key="race", pv_values=("White", "Black", "Asian", "Other")),
        CDE(cde_id=5, cde_key="vital_status", pv_values=("Alive", "Dead", "Unknown")),
    ]


@pytest.fixture
def sample_column_result() -> ColumnResult:
    return ColumnResult(
        column_name="sex",
        matches=[
            CDEMatch(cde_id=1, cde_key="gender", rank=1),
            CDEMatch(cde_id=3, cde_key="ethnicity", rank=2),
        ],
    )
