import json
from unittest.mock import MagicMock, patch

from cde_recommend.handler import handler
from cde_recommend.types import CDE, CDEMatch, ColumnResult, UsageStats


def test_handler_400_missing_target_schema():
    # Given: a request body missing the target_schema field
    event = {"body": json.dumps({"data": {"x": ["a"]}})}

    # When: handler is called
    resp = handler(event, None)

    # Then: 400 with error mentioning target_schema
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "target_schema" in body["error"]


def test_handler_400_empty_data():
    # Given: a request with an empty data dict
    event = {"body": json.dumps({"target_schema": "ccdi", "data": {}})}

    # When: handler is called
    resp = handler(event, None)

    # Then: 400 with error mentioning data
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "data" in body["error"]


def test_handler_400_invalid_body():
    # Given: unparseable JSON in the body
    event = {"body": "not json at all {{{"}

    # When: handler is called
    resp = handler(event, None)

    # Then: 400
    assert resp["statusCode"] == 400


@patch("cde_recommend.handler.load_cdes")
def test_handler_404_unknown_data_model(mock_load: MagicMock):
    # Given: load_cdes raises KeyError for an unknown data model
    mock_load.side_effect = KeyError("Unknown data model key or version")
    event = {
        "body": json.dumps({
            "target_schema": "nonexistent",
            "data": {"x": ["a"]},
        })
    }

    # When: handler is called
    resp = handler(event, None)

    # Then: 404
    assert resp["statusCode"] == 404


@patch("cde_recommend.handler.load_cdes")
def test_handler_404_no_cdes(mock_load: MagicMock):
    # Given: load_cdes returns an empty CDE list
    mock_load.return_value = ([], "label", 1)
    event = {
        "body": json.dumps({
            "target_schema": "ccdi",
            "data": {"x": ["a"]},
        })
    }

    # When: handler is called
    resp = handler(event, None)

    # Then: 404
    assert resp["statusCode"] == 404


@patch("cde_recommend.handler.match_columns_batch")
@patch("cde_recommend.handler.get_client")
@patch("cde_recommend.handler.load_cdes")
def test_handler_excludes_high_cardinality_cdes(
    mock_load: MagicMock,
    mock_get_client: MagicMock,
    mock_batch: MagicMock,
):
    # Given: a mix of low- and high-cardinality CDEs
    low_pv_cde = CDE(cde_id=1, cde_key="gender", pv_values=("Male", "Female"))
    high_pv_cde = CDE(
        cde_id=2,
        cde_key="treatment_agent",
        pv_values=tuple(f"drug_{i}" for i in range(200)),
    )
    # high_pv_cde has NOT been filtered yet
    assert len(high_pv_cde.pv_values) > 100

    mock_load.return_value = ([low_pv_cde, high_pv_cde], "auto-v1", 1)
    mock_get_client.return_value = MagicMock()

    async def fake_batch(**kwargs: object) -> tuple[list[ColumnResult], UsageStats]:
        match = CDEMatch(cde_id=1, cde_key="gender", rank=1, confidence=0.95)
        return (
            [ColumnResult(column_name="sex", matches=[match])],
            UsageStats(input_tokens=0, output_tokens=0, total_tokens=0),
        )

    mock_batch.side_effect = fake_batch

    event = {"body": json.dumps({
        "target_schema": "ccdi", "target_version": 1, "data": {"sex": ["M"]},
    })}

    # When
    resp = handler(event, None)

    # Then: only the low-cardinality CDE is passed to match_columns_batch
    assert resp["statusCode"] == 200
    call_kwargs = mock_batch.call_args
    passed_cdes = call_kwargs.kwargs.get("all_cdes") or call_kwargs[1].get("all_cdes")
    assert passed_cdes == [low_pv_cde]


@patch("cde_recommend.handler.asyncio")
@patch("cde_recommend.handler.get_client")
@patch("cde_recommend.handler.load_cdes")
def test_handler_200_returns_client_contract(
    mock_load: MagicMock,
    mock_get_client: MagicMock,
    mock_asyncio: MagicMock,
):
    # Given: a valid request with CDEs and a mocked batch result
    sample_cdes = [
        CDE(cde_id=1, cde_key="gender", pv_values=("Male", "Female")),
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

    # When: handler is called
    resp = handler(event, None)

    # Then: 200 with the netrias_client contract format
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
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
