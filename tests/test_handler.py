import json
from unittest.mock import MagicMock, patch

from cde_recommend.handler import handler
from cde_recommend.types import CDE, CDEMatch, ColumnResult, UsageStats


def test_handler_400_missing_target_schema():
    event = {"body": json.dumps({"data": {"x": ["a"]}})}
    resp = handler(event, None)
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "target_schema" in body["error"]


def test_handler_400_empty_data():
    event = {"body": json.dumps({"target_schema": "ccdi", "data": {}})}
    resp = handler(event, None)
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "data" in body["error"]


def test_handler_400_invalid_body():
    event = {"body": "not json at all {{{"}
    resp = handler(event, None)
    assert resp["statusCode"] == 400


@patch("cde_recommend.handler.load_cdes")
def test_handler_404_unknown_data_model(mock_load: MagicMock):
    mock_load.side_effect = KeyError("Unknown data model key or version")
    event = {
        "body": json.dumps({
            "target_schema": "nonexistent",
            "data": {"x": ["a"]},
        })
    }
    resp = handler(event, None)
    assert resp["statusCode"] == 404


@patch("cde_recommend.handler.load_cdes")
def test_handler_404_no_cdes(mock_load: MagicMock):
    mock_load.return_value = ([], "label", 1)
    event = {
        "body": json.dumps({
            "target_schema": "ccdi",
            "data": {"x": ["a"]},
        })
    }
    resp = handler(event, None)
    assert resp["statusCode"] == 404


@patch("cde_recommend.handler.asyncio")
@patch("cde_recommend.handler.get_client")
@patch("cde_recommend.handler.load_cdes")
def test_handler_200_returns_client_contract(
    mock_load: MagicMock,
    mock_get_client: MagicMock,
    mock_asyncio: MagicMock,
):
    sample_cdes = [
        CDE(cde_id=1, cde_key="gender", pv_values=("Male", "Female")),
        CDE(cde_id=2, cde_key="age", pv_values=()),
    ]
    mock_load.return_value = (sample_cdes, "auto-v1", 1)
    mock_get_client.return_value = MagicMock()

    mock_results = [
        ColumnResult(
            column_name="sex",
            matches=[CDEMatch(cde_id=1, cde_key="gender", rank=1, confidence=0.95)],
        )
    ]
    mock_usage = UsageStats(input_tokens=1000, output_tokens=50, total_tokens=1050)
    mock_asyncio.run.return_value = (mock_results, mock_usage)

    event = {
        "body": json.dumps({
            "target_schema": "ccdi",
            "target_version": 1,
            "data": {"sex": ["Male", "Female"]},
        })
    }
    resp = handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])

    # Response is just {"results": {...}}
    assert "results" in body
    assert "sex" in body["results"]

    match = body["results"]["sex"][0]
    assert match["target"] == "gender"
    assert match["similarity"] == 0.95
    assert match["target_cde_id"] == 1

    # Old envelope fields should NOT be present
    assert "data_commons_key" not in body
    assert "usage" not in body
    assert "params" not in body
