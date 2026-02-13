"""CLI argument parsing for deploy script."""

from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class DeployArgs:
    environment: str
    plan_only: bool


def parse_args() -> DeployArgs:
    parser = argparse.ArgumentParser(description="Deploy CDE recommendation Lambda")
    parser.add_argument(
        "--env",
        required=True,
        choices=["staging", "prod"],
        help="Target environment",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Run terraform plan instead of apply",
    )
    args = parser.parse_args()
    return DeployArgs(environment=args.env, plan_only=args.plan)
