"""Main deploy orchestrator. Invoked as: uv run python -m deploy.deploy --env staging [--plan]"""

from __future__ import annotations

import sys
from pathlib import Path

from deploy.cli import parse_args
from deploy.console import log_error, log_info
from deploy.packaging import build_lambda_zip
from deploy.secrets import ensure_secrets
from deploy.terraform import apply, bootstrap_backend, init, plan

_PROJECT_NAME = "cde-recommend"
_AWS_REGION = "us-east-2"


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    infra_dir = repo_root / "infra"

    log_info(f"Deploying {_PROJECT_NAME} to {args.environment}")

    # Secrets must load first — ensure_secrets sets TF_VAR_* env vars that terraform reads
    log_info("Step 1/5: Loading secrets from SSM...")
    ensure_secrets(args.environment, _AWS_REGION)

    # 2. Package Lambda ZIP
    log_info("Step 2/5: Building Lambda package...")
    build_lambda_zip(repo_root)

    # 3. Bootstrap Terraform backend
    log_info("Step 3/5: Bootstrapping Terraform backend...")
    bootstrap_backend(_PROJECT_NAME, args.environment, _AWS_REGION)

    # 4. Terraform init
    log_info("Step 4/5: Initializing Terraform...")
    init(infra_dir, args.environment, _PROJECT_NAME, _AWS_REGION)

    # 5. Plan or Apply
    if args.plan_only:
        log_info("Step 5/5: Running Terraform plan...")
        plan(infra_dir, args.environment)
    else:
        log_info("Step 5/5: Applying Terraform changes...")
        apply(infra_dir, args.environment)

    log_info("Deploy complete!")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        log_error(str(e))
        sys.exit(1)
