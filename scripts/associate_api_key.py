"""Associate an API Gateway API key with all standard usage plans.

Axis of change: the set of usage plans that constitute "standard access".
"""

from __future__ import annotations

import argparse
import sys

import boto3

REGION = "us-east-2"

# REST API usage plans that constitute standard API access.
# Format: (usage_plan_id, human_label)
#
# Each plan is owned by a different Terraform workspace:
#   772ahq — bdi-kit/tokyo (datastore + harmonization-db)
#   h8daoc — cde-recommendation-lambda/kyoto (async Step Functions API)
#   ont5g8 — apiserver (Terraform Cloud)
#   zdtqrs — apivm (Terraform Cloud)
#
# After workstreams 2-3 deploy, add:
#   <TBD>  — bdi-kit/sarajevo (cde-recommend direct Lambda, `tofu output usage_plan_id`)
#   <TBD>  — harmonization_pipeline/manila (harmonization REST API, `tofu output usage_plan_id`)
STANDARD_USAGE_PLANS: list[tuple[str, str]] = [
    ("772ahq", "datastore + harmonization-db"),
    ("h8daoc", "cde-recommendation-staging (async)"),
    ("ont5g8", "apiserver"),
    ("zdtqrs", "apivm"),
]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Associate an API Gateway key with standard usage plans."
    )
    parser.add_argument("key_id", help="API Gateway API key ID (e.g. tg9wjkvhcb)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without making changes",
    )
    return parser.parse_args(argv)


def _get_existing_plan_ids(client: boto3.client, key_id: str) -> set[str]:  # type: ignore[type-arg]
    """Return usage plan IDs the key is already associated with."""
    response = client.get_usage_plans(keyId=key_id)
    return {plan["id"] for plan in response.get("items", [])}


def _validate_key_exists(client: boto3.client, key_id: str) -> str:  # type: ignore[type-arg]
    """Return the key name, or exit if the key doesn't exist."""
    try:
        info = client.get_api_key(apiKey=key_id)
    except client.exceptions.NotFoundException:
        print(f"Error: API key '{key_id}' not found in {REGION}", file=sys.stderr)
        sys.exit(1)
    return info["name"]


def associate_key(key_id: str, dry_run: bool = False) -> None:
    client = boto3.client("apigateway", region_name=REGION)

    key_name = _validate_key_exists(client, key_id)
    print(f"Key: {key_id} ({key_name})")

    existing = _get_existing_plan_ids(client, key_id)

    for plan_id, label in STANDARD_USAGE_PLANS:
        if plan_id in existing:
            print(f"  [skip] {plan_id} ({label}) — already associated")
            continue

        if dry_run:
            print(f"  [dry-run] would associate with {plan_id} ({label})")
            continue

        client.create_usage_plan_key(
            usagePlanId=plan_id,
            keyId=key_id,
            keyType="API_KEY",
        )
        print(f"  [done] associated with {plan_id} ({label})")

    print("\nDone.")


def main() -> None:
    args = _parse_args()
    associate_key(args.key_id, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
