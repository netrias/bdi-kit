"""SSM credential loading. Fail fast if any secret is missing.

Changes when secret sources or environment variable mappings change.
"""

from __future__ import annotations

import os

from deploy.console import log_error, log_info
from deploy.subprocess_helpers import run_command

_SSM_PREFIX = "/harmonization-pipeline"

_SECRETS: list[tuple[str, str]] = [
    ("openai-api-key", "TF_VAR_openai_api_key"),
    ("zero-shot-db-user", "TF_VAR_db_user"),
    ("zero-shot-db-password", "TF_VAR_db_password"),
]


def ensure_secrets(env: str, region: str) -> None:
    """Load all required secrets from SSM and export as TF_VAR_* env vars."""
    missing: list[str] = []

    for ssm_name, env_var in _SECRETS:
        param_path = f"{_SSM_PREFIX}/{env}/{ssm_name}"
        value = _load_from_ssm(param_path, region)
        if not value:
            missing.append(param_path)
            continue
        os.environ[env_var] = value
        log_info(f"Loaded {param_path} -> {env_var}")

    if missing:
        log_error(f"Missing SSM parameters: {missing}")
        raise RuntimeError(f"Missing required SSM parameters: {missing}")


def _load_from_ssm(parameter_name: str, region: str) -> str | None:
    try:
        result = run_command(
            [
                "aws", "ssm", "get-parameter",
                "--name", parameter_name,
                "--with-decryption",
                "--query", "Parameter.Value",
                "--output", "text",
                "--region", region,
            ],
            check=True,
        )
        return result.stdout.strip() or None
    except RuntimeError:
        return None
