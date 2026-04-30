"""Structural tests for the Airflow DAG.

Avoids importing airflow (which is a heavy optional dep) by parsing the DAG
file as Python AST and asserting on its shape. This catches:

- Syntax errors
- Missing key decorators (`@dag`, `@task`, `@task_group`)
- Missing imports of pure-logic modules (drift between DAG and `csrd_lake.*`)
- Missing task IDs or task groups
- DAG-level config (schedule, tags, retries)

Real Airflow DAG-parse + run tests execute inside the Airflow Docker
Compose container in CI (separate workflow), where airflow IS installed.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

DAG_FILE = Path(__file__).resolve().parents[1] / "airflow" / "dags" / "csrd_lake.py"


@pytest.fixture(scope="module")
def dag_source() -> str:
    return DAG_FILE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def dag_ast(dag_source: str) -> ast.Module:
    return ast.parse(dag_source)


# ── File presence ─────────────────────────────────────────────────────


def test_dag_file_exists() -> None:
    assert DAG_FILE.exists(), f"DAG file missing at {DAG_FILE}"


def test_dag_file_is_valid_python(dag_source: str) -> None:
    """Compile the DAG source — catches any Python syntax error."""
    compile(dag_source, str(DAG_FILE), "exec")


# ── Required imports ──────────────────────────────────────────────────


def _imported_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
    return names


def test_imports_pure_logic_modules(dag_ast: ast.Module) -> None:
    """The DAG must import from each pure-logic module the build relies on."""
    names = _imported_names(dag_ast)
    expected = {
        "extract_esrs_metrics",
        "ESRSMetric",
        "ESRSTopic",
        "download_pdf",
        "load_manifest",
        "CompanyEntry",
        "load_metrics",
    }
    missing = expected - names
    assert not missing, f"DAG missing imports: {missing}"


def test_imports_airflow_decorators(dag_ast: ast.Module) -> None:
    names = _imported_names(dag_ast)
    expected = {"dag", "task", "task_group"}
    missing = expected - names
    assert not missing, f"DAG missing airflow decorators: {missing}"


def test_imports_snowflake_hook(dag_ast: ast.Module) -> None:
    """Connection management goes through SnowflakeHook, not raw connector."""
    names = _imported_names(dag_ast)
    assert "SnowflakeHook" in names


def test_imports_anthropic_and_mistral(dag_ast: ast.Module) -> None:
    names = _imported_names(dag_ast)
    assert "Anthropic" in names
    assert "Mistral" in names


# ── DAG-level structure ───────────────────────────────────────────────


def _decorator_names(tree: ast.Module) -> list[str]:
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call):
                    func = dec.func
                else:
                    func = dec
                if isinstance(func, ast.Name):
                    out.append(func.id)
                elif isinstance(func, ast.Attribute):
                    out.append(func.attr)
    return out


def test_dag_decorator_used(dag_ast: ast.Module) -> None:
    decorators = _decorator_names(dag_ast)
    assert "dag" in decorators, "Top-level @dag decorator missing"


def test_three_task_groups_present(dag_ast: ast.Module) -> None:
    decorators = _decorator_names(dag_ast)
    # @task_group for ingest / extract / load
    assert decorators.count("task_group") >= 3, (
        f"Expected ≥3 @task_group decorators, found {decorators.count('task_group')}"
    )


def test_task_decorators_present(dag_ast: ast.Module) -> None:
    decorators = _decorator_names(dag_ast)
    # At least 4 @task: list_companies, download_one, extract_one, load_one
    assert decorators.count("task") >= 4, (
        f"Expected ≥4 @task decorators, found {decorators.count('task')}"
    )


# ── DAG metadata strings (regression guards on conventions) ───────────


def test_dag_id_is_csrd_lake(dag_source: str) -> None:
    assert 'dag_id="csrd_lake"' in dag_source


def test_tags_include_canonical_set(dag_source: str) -> None:
    """Recruiter scrolling Airflow UI sees these tags first — keep them stable."""
    for tag in ("csrd-lake", "esrs", "ingestion", "extraction"):
        assert f'"{tag}"' in dag_source, f"DAG tag '{tag}' missing"


def test_dag_has_retries_default(dag_source: str) -> None:
    assert '"retries"' in dag_source


def test_dag_has_doc_md(dag_source: str) -> None:
    """doc_md=__doc__ surfaces the file docstring in the Airflow UI."""
    assert "doc_md=__doc__" in dag_source


# ── Anti-regression: forbidden patterns ───────────────────────────────


def test_no_print_statements(dag_source: str) -> None:
    """Use structlog, not print — but DAGs may need to print for Airflow log capture."""
    # Allow print only inside a task body; assert no module-level print.
    # Simpler check: no bare `print(` outside a string.
    lines = [
        line
        for line in dag_source.splitlines()
        if "print(" in line and not line.strip().startswith("#")
    ]
    # Permit print inside doc strings or as part of a substring check
    real_prints = [
        line for line in lines if not ('"""' in line or "'''" in line or '"' + "print(" in line)
    ]
    assert not real_prints, f"Unexpected print() calls: {real_prints}"


def test_no_hardcoded_api_keys(dag_source: str) -> None:
    """Sanity scan — no `sk-`, `Bearer`, or obvious credential strings."""
    forbidden = ["sk-ant-", "sk-proj-", "Bearer "]
    for needle in forbidden:
        assert needle not in dag_source, f"Possible leaked credential: '{needle}'"


def test_does_not_reintroduce_killed_claims(dag_source: str) -> None:
    """The 'replaces MSCI subscription' framing was killed by /moat-check."""
    forbidden_phrases = [
        "replaces MSCI",
        "replaces a €40",
        "replaces a €80",
        "MSCI subscription",
        "Sustainalytics subscription",
    ]
    for phrase in forbidden_phrases:
        assert phrase.lower() not in dag_source.lower(), (
            f"DAG accidentally references killed claim: '{phrase}'"
        )
