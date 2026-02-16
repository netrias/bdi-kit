"""Subprocess execution with consistent error handling.

Changes when command failure modes change.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

from deploy.console import log_error


def run_command(
    cmd: Sequence[str],
    cwd: Path | None = None,
    check: bool = True,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(  # noqa: S603
        [str(part) for part in cmd],
        cwd=str(cwd) if cwd else None,
        check=False,
        capture_output=capture_output,
        text=True,
    )
    if check and result.returncode != 0:
        command_display = " ".join(str(part) for part in cmd)
        cwd_display = str(cwd) if cwd else "N/A"
        error_output = result.stderr or result.stdout or ""
        error_message = (
            f"Command failed (cmd={command_display}, cwd={cwd_display}, "
            f"code={result.returncode}): {error_output.strip()}"
        )
        log_error(error_message)
        raise RuntimeError(error_message)
    return result
