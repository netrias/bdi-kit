"""Lambda ZIP builder with cross-platform compilation for Linux x86_64."""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path

from deploy.console import log_info
from deploy.subprocess_helpers import run_command

_RUNTIME_DEPS = [
    "openai>=1.60",
    "psycopg-binary>=3.2",
    "psycopg>=3.2",
    "pydantic>=2.10",
    "boto3>=1.35",
]


def build_lambda_zip(repo_root: Path) -> Path:
    """Build build/lambda.zip with Linux-compatible dependencies + source code."""
    build_dir = repo_root / "build"
    build_dir.mkdir(exist_ok=True)
    zip_path = build_dir / "lambda.zip"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Install runtime deps cross-compiled for Lambda (Linux x86_64)
        log_info("Installing runtime dependencies for Linux x86_64...")
        run_command(
            [
                "uv", "pip", "install",
                "--target", str(tmp_path),
                "--python-platform", "x86_64-unknown-linux-gnu",
                "--python-version", "3.12",
                "--only-binary", ":all:",
                *_RUNTIME_DEPS,
            ],
        )

        # Copy source package at ZIP root (NOT under src/)
        src_pkg = repo_root / "src" / "cde_recommend"
        dst_pkg = tmp_path / "cde_recommend"
        shutil.copytree(src_pkg, dst_pkg)
        log_info(f"Copied {src_pkg} -> {dst_pkg}")

        # Build ZIP
        log_info(f"Creating {zip_path}...")
        _zip_directory(tmp_path, zip_path)

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    log_info(f"Lambda package: {zip_path} ({size_mb:.1f} MB)")
    return zip_path


def _zip_directory(source_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(source_dir.rglob("*")):
            if file_path.is_file():
                arcname = file_path.relative_to(source_dir)
                zf.write(file_path, arcname)
