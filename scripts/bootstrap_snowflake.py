"""Bootstrap a Snowflake account with the CSRD-Lake schema and load the 34
already-extracted ESRS metrics from `data/extracted/*.json`.

Validates the Snowflake target end-to-end without re-running (and re-paying
for) the LLM batch. The metrics are already on disk as ESRSMetric JSON
archives from the local DuckDB extraction run.

Usage:
    uv run python scripts/bootstrap_snowflake.py
    uv run python scripts/bootstrap_snowflake.py --truncate

Idempotent: schemas + table use IF NOT EXISTS; --truncate wipes raw before
loading for a deterministic snapshot.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import structlog
from dotenv import load_dotenv

from csrd_lake.extraction.schemas import ESRSMetric
from csrd_lake.warehouse.loader import TARGET_TABLE, load_metrics

logger = structlog.get_logger(__name__)

DDL_PATH = Path("src/csrd_lake/warehouse/ddl.sql")
EXTRACTED_DIR = Path("data/extracted")


def _normalize_account(raw: str) -> str:
    """Strip common copy-paste artefacts from a Snowflake account identifier.

    The Python connector accepts the bare identifier (e.g. `xy12345.eu-west-1.aws`)
    OR the full hostname; it does NOT accept the URL with protocol. We strip
    protocol, trailing slash, and the .snowflakecomputing.com suffix so
    pasting the browser URL Just Works.
    """
    s = raw.strip()
    for prefix in ("https://", "http://"):
        if s.lower().startswith(prefix):
            s = s[len(prefix) :]
    s = s.rstrip("/")
    suffix = ".snowflakecomputing.com"
    if s.lower().endswith(suffix):
        s = s[: -len(suffix)]
    return s


def _load_private_key(path_str: str):
    """Load a PKCS#8 private key from disk for Snowflake key-pair auth."""
    from cryptography.hazmat.primitives import serialization

    path = Path(os.path.expanduser(path_str))
    if not path.exists():
        raise FileNotFoundError(
            f"Private key not found at {path}. "
            f"Generate with `uv run python scripts/generate_snowflake_keypair.py`."
        )
    pem = path.read_bytes()
    private_key = serialization.load_pem_private_key(pem, password=None)
    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _connect():
    """Open a live Snowflake connection. Uses key-pair auth if
    SNOWFLAKE_PRIVATE_KEY_PATH is set (preferred — bypasses MFA),
    otherwise falls back to password auth.
    """
    import snowflake.connector

    required = (
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_WAREHOUSE",
        "SNOWFLAKE_DATABASE",
    )
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        raise RuntimeError(f"Missing env vars: {missing}")

    account = _normalize_account(os.environ["SNOWFLAKE_ACCOUNT"])
    private_key_path = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH")
    auth_method = "key-pair" if private_key_path else "password"

    print(f"  account:   {account}")
    print(f"  user:      {os.environ['SNOWFLAKE_USER']}")
    print(f"  warehouse: {os.environ['SNOWFLAKE_WAREHOUSE']}")
    print(f"  database:  {os.environ['SNOWFLAKE_DATABASE']}")
    print(f"  auth:      {auth_method}")

    common = {
        "account": account,
        "user": os.environ["SNOWFLAKE_USER"],
        "role": os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        "warehouse": os.environ["SNOWFLAKE_WAREHOUSE"],
        "database": os.environ["SNOWFLAKE_DATABASE"],
        "client_session_keep_alive": False,
        "login_timeout": 10,
    }
    if private_key_path:
        common["private_key"] = _load_private_key(private_key_path)
    else:
        common["password"] = os.environ["SNOWFLAKE_PASSWORD"]

    return snowflake.connector.connect(**common)


def _split_ddl_statements(ddl: str) -> list[str]:
    """Split a multi-statement SQL file into individual statements.

    Strips line comments, empty lines, and trailing whitespace. Snowflake's
    Python connector executes one statement per call.
    """
    cleaned: list[str] = []
    for raw_line in ddl.splitlines():
        stripped = raw_line.split("--", 1)[0].rstrip()
        if stripped.strip():
            cleaned.append(stripped)
    joined = "\n".join(cleaned)
    return [s.strip() for s in joined.split(";") if s.strip()]


def _ensure_database(conn) -> None:
    """`CREATE DATABASE IF NOT EXISTS <db>` then USE it."""
    db = os.environ["SNOWFLAKE_DATABASE"]
    cur = conn.cursor()
    try:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {db}")
        cur.execute(f"USE DATABASE {db}")
        print(f"OK using database {db}")
    finally:
        cur.close()


def _run_ddl(conn) -> None:
    ddl = DDL_PATH.read_text(encoding="utf-8")
    statements = _split_ddl_statements(ddl)
    cur = conn.cursor()
    try:
        for sql in statements:
            cur.execute(sql)
        print(f"OK ran {len(statements)} DDL statement(s)")
    finally:
        cur.close()


def _load_metrics_from_archives(conn) -> int:
    """Read every data/extracted/*.json, validate as ESRSMetric, bulk-insert."""
    archive_paths = sorted(EXTRACTED_DIR.glob("*.json"))
    if not archive_paths:
        raise RuntimeError(
            f"No archives found under {EXTRACTED_DIR}/. "
            f"Run `uv run python -m csrd_lake.extraction.batch` first."
        )

    all_metrics: list[ESRSMetric] = []
    for path in archive_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        all_metrics.extend(ESRSMetric.model_validate(item) for item in payload)
        print(f"  loaded {len(payload):>3} metrics from {path.name}")

    inserted = load_metrics(all_metrics, conn=conn)
    return inserted


def _truncate_raw(conn) -> None:
    cur = conn.cursor()
    try:
        cur.execute(f"TRUNCATE TABLE IF EXISTS {TARGET_TABLE}")
        print(f"OK truncated {TARGET_TABLE}")
    finally:
        cur.close()


def _summarize(conn) -> None:
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT COUNT(*) FROM {TARGET_TABLE}")
        n = cur.fetchone()[0]
        print(f"\n→ {TARGET_TABLE}: {n} rows in Snowflake")
        cur.execute(f"SELECT company_ticker, COUNT(*) FROM {TARGET_TABLE} GROUP BY 1 ORDER BY 1")
        for ticker, count in cur.fetchall():
            print(f"   {ticker}: {count}")
    finally:
        cur.close()


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Truncate raw.disclosure_extracted before loading.",
    )
    parser.add_argument(
        "--skip-load",
        action="store_true",
        help="Run DDL only; do not load metrics.",
    )
    args = parser.parse_args()

    try:
        conn = _connect()
    except Exception as exc:
        print(f"ERROR connecting to Snowflake: {exc}", file=sys.stderr)
        return 1

    try:
        _ensure_database(conn)
        _run_ddl(conn)
        if args.truncate:
            _truncate_raw(conn)
        if not args.skip_load:
            inserted = _load_metrics_from_archives(conn)
            print(f"OK inserted {inserted} rows into {TARGET_TABLE}")
        _summarize(conn)
    finally:
        conn.close()

    print(
        "\n→ Snowflake bootstrap complete. Next: cd dbt_project && DBT_TARGET=dev uv run dbt seed && uv run dbt run"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
