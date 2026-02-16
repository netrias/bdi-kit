"""Terraform operations and S3/DynamoDB backend bootstrap.

Changes when backend infrastructure or terraform workflow changes.
"""

from __future__ import annotations

from pathlib import Path

from deploy.console import log_info
from deploy.subprocess_helpers import run_command


def bootstrap_backend(project_name: str, env: str, region: str) -> None:
    """Create S3 bucket + DynamoDB lock table if they don't exist."""
    bucket = _bucket_name(project_name, env)
    table = _lock_table_name(project_name, env)
    _ensure_s3_bucket(bucket, region)
    _ensure_dynamodb_table(table, region)


def backend_config_flags(project_name: str, env: str, region: str) -> list[str]:
    return [
        f"-backend-config=bucket={_bucket_name(project_name, env)}",
        f"-backend-config=dynamodb_table={_lock_table_name(project_name, env)}",
        f"-backend-config=region={region}",
    ]


def init(infra_dir: Path, env: str, project_name: str, region: str) -> None:
    flags = backend_config_flags(project_name, env, region)
    log_info("Running tofu init...")
    result = run_command(
        ["tofu", "init", "-reconfigure", *flags],
        cwd=infra_dir,
        capture_output=False,
    )
    if result.returncode != 0:
        raise RuntimeError("tofu init failed")


def plan(infra_dir: Path, env: str) -> None:
    log_info(f"Running tofu plan with {env}.tfvars...")
    run_command(
        ["tofu", "plan", f"-var-file={env}.tfvars"],
        cwd=infra_dir,
        capture_output=False,
    )


def apply(infra_dir: Path, env: str) -> None:
    log_info(f"Running tofu apply with {env}.tfvars...")
    run_command(
        ["tofu", "apply", "-auto-approve", f"-var-file={env}.tfvars"],
        cwd=infra_dir,
        capture_output=False,
    )


def _ensure_s3_bucket(bucket: str, region: str) -> None:
    try:
        run_command(
            ["aws", "s3api", "head-bucket", "--bucket", bucket, "--region", region],
        )
        log_info(f"S3 bucket already exists: {bucket}")
    except RuntimeError:
        log_info(f"Creating S3 bucket: {bucket}")
        run_command(
            [
                "aws", "s3api", "create-bucket",
                "--bucket", bucket,
                "--region", region,
                "--create-bucket-configuration",
                f"LocationConstraint={region}",
            ],
        )
        run_command(
            [
                "aws", "s3api", "put-bucket-versioning",
                "--bucket", bucket,
                "--versioning-configuration", "Status=Enabled",
            ],
        )


def _ensure_dynamodb_table(table: str, region: str) -> None:
    try:
        run_command(
            [
                "aws", "dynamodb", "describe-table",
                "--table-name", table,
                "--region", region,
            ],
        )
        log_info(f"DynamoDB lock table already exists: {table}")
    except RuntimeError:
        log_info(f"Creating DynamoDB lock table: {table}")
        run_command(
            [
                "aws", "dynamodb", "create-table",
                "--table-name", table,
                "--attribute-definitions", "AttributeName=LockID,AttributeType=S",
                "--key-schema", "AttributeName=LockID,KeyType=HASH",
                "--billing-mode", "PAY_PER_REQUEST",
                "--region", region,
            ],
        )
        log_info("Waiting for lock table to become active...")
        run_command(
            [
                "aws", "dynamodb", "wait", "table-exists",
                "--table-name", table,
                "--region", region,
            ],
        )


def _bucket_name(project_name: str, env: str) -> str:
    return f"{project_name}-tfstate-{env}"


def _lock_table_name(project_name: str, env: str) -> str:
    return f"{project_name}-tflock-{env}"
