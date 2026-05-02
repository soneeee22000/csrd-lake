"""dbt wrapper that loads .env before invoking dbt.

Lets `uv run python scripts/dbt_run.py seed` Just Work without manually
exporting SNOWFLAKE_* env vars on the shell. Forwards all CLI args to dbt
and runs from the dbt_project/ directory.

Usage:
    python scripts/dbt_run.py seed --target dev
    python scripts/dbt_run.py run --target duckdb
    python scripts/dbt_run.py test --target dev

DBT_TARGET env var (loaded from .env or shell) sets the default target.
Path expansion is applied to SNOWFLAKE_PRIVATE_KEY_PATH so `~/...` works.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / ".env")

    # dbt's snowflake adapter wants an absolute path for private_key_path.
    if "SNOWFLAKE_PRIVATE_KEY_PATH" in os.environ:
        os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"] = os.path.expanduser(
            os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]
        )

    # We chdir into dbt_project/, so profiles.yml is in the cwd.
    # Override any DBT_PROFILES_DIR from .env (e.g. './dbt_project') that
    # would resolve relative to the new cwd and double-nest.
    os.environ["DBT_PROFILES_DIR"] = str(repo_root / "dbt_project")

    dbt_exe = repo_root / ".venv" / "Scripts" / "dbt.exe"
    if not dbt_exe.exists():
        # POSIX layout
        dbt_exe = repo_root / ".venv" / "bin" / "dbt"

    proc = subprocess.run(
        [str(dbt_exe), *sys.argv[1:]],
        cwd=repo_root / "dbt_project",
        env=os.environ,
    )
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
