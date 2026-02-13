import json
from unittest.mock import MagicMock, patch

from cde_recommend.handler import handler
from cde_recommend.types import CDE, CDEMatch, ColumnResult, UsageStats


def test_handler_400_missing_data_commons_key():
    event = {"body": json.dumps({"columns": [{"column_name": "x", "column_values": ["a"]}]})}
    resp = handler(event, None)
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "data_commons_key" in body["error"]


def test_handler_400_empty_columns():
    event = {"body": json.dumps({"data_commons_key": "ccdi", "columns": []})}
    resp = handler(event, None)
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "columns" in body["error"]


def test_handler_400_invalid_body():
    event = {"body": "not json at all {{{"}
    resp = handler(event, None)
    assert resp["statusCode"] == 400


@patch("cde_recommend.handler.load_cdes")
def test_handler_404_unknown_data_model(mock_load: MagicMock):
    mock_load.side_effect = KeyError("Unknown data model key or version")
    event = {
        "body": json.dumps({
            "data_commons_key": "nonexistent",
            "columns": [{"column_name": "x", "column_values": ["a"]}],
        })
    }
    resp = handler(event, None)
    assert resp["statusCode"] == 404


@patch("cde_recommend.handler.load_cdes")
def test_handler_404_no_cdes(mock_load: MagicMock):
    mock_load.return_value = ([], "label", 1)
    event = {
        "body": json.dumps({
            "data_commons_key": "ccdi",
            "columns": [{"column_name": "x", "column_values": ["a"]}],
        })
    }
    resp = handler(event, None)
    assert resp["statusCode"] == 404


@patch("cde_recommend.handler.asyncio")
@patch("cde_recommend.handler.get_client")
@patch("cde_recommend.handler.load_cdes")
def test_handler_200_with_batch_results(
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
            matches=[CDEMatch(cde_id=1, cde_key="gender", rank=1)],
        )
    ]
    mock_usage = UsageStats(input_tokens=1000, output_tokens=50, total_tokens=1050)
    mock_asyncio.run.return_value = (mock_results, mock_usage)

    event = {
        "body": json.dumps({
            "data_commons_key": "ccdi",
            "version_number": 1,
            "columns": [{"column_name": "sex", "column_values": ["Male", "Female"]}],
        })
    }
    resp = handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["data_commons_key"] == "ccdi"
    assert body["version_label"] == "auto-v1"
    assert body["version_number"] == 1
    assert body["candidate_cde_count"] == 2
    assert len(body["results"]) == 1
    assert body["results"][0]["column_name"] == "sex"
    assert body["results"][0]["matches"][0]["cde_key"] == "gender"
    assert body["usage"]["total_tokens"] == 1050
