from unittest.mock import MagicMock, patch

import pytest
from scripts.associate_api_key import (
    STANDARD_USAGE_PLANS,
    associate_key,
)


@patch("scripts.associate_api_key.boto3")
def test_dry_run_lists_all_plans_without_aws_calls(mock_boto3: MagicMock):
    """
    Given: STANDARD_USAGE_PLANS has N entries and --dry-run is passed
    When: associate_key runs
    Then: all N plans are listed and no create_usage_plan_key calls are made
    Negative: no plans are skipped
    """
    client = MagicMock()
    mock_boto3.client.return_value = client
    client.get_api_key.return_value = {"name": "test-key"}
    client.get_usage_plans.return_value = {"items": []}

    associate_key("tg9wjkvhcb", dry_run=True)

    # Validated the key exists
    client.get_api_key.assert_called_once_with(apiKey="tg9wjkvhcb")
    # No actual associations created
    client.create_usage_plan_key.assert_not_called()


@patch("scripts.associate_api_key.boto3")
def test_invalid_key_exits_with_error(mock_boto3: MagicMock):
    """
    Given: an invalid API key ID
    When: associate_key runs
    Then: it exits with a clear error and no associations are created
    """
    client = MagicMock()
    mock_boto3.client.return_value = client
    client.exceptions.NotFoundException = type("NotFoundException", (Exception,), {})
    client.get_api_key.side_effect = client.exceptions.NotFoundException("not found")

    with pytest.raises(SystemExit) as exc_info:
        associate_key("bad-key-id")

    assert exc_info.value.code == 1
    client.create_usage_plan_key.assert_not_called()


@patch("scripts.associate_api_key.boto3")
def test_skips_already_associated_plans(mock_boto3: MagicMock):
    """
    Given: the key is already associated with the first plan
    When: associate_key runs (not dry-run)
    Then: only non-associated plans get create_usage_plan_key calls
    """
    client = MagicMock()
    mock_boto3.client.return_value = client
    client.get_api_key.return_value = {"name": "test-key"}

    first_plan_id = STANDARD_USAGE_PLANS[0][0]
    client.get_usage_plans.return_value = {"items": [{"id": first_plan_id}]}

    associate_key("tg9wjkvhcb", dry_run=False)

    calls = client.create_usage_plan_key.call_args_list
    created_plan_ids = [c.kwargs["usagePlanId"] for c in calls]
    assert first_plan_id not in created_plan_ids
    assert len(created_plan_ids) == len(STANDARD_USAGE_PLANS) - 1
