"""Running the warehouse and reading its test report.

The dbt project in ./warehouse/ builds the same models two ways, selected by
the `scenario` variable:

    broken  the customer dimension keeps every historical CRM row
    fixed   the customer dimension keeps only the current row per customer

Everything else is identical, which is the point: the bug is one missing
filter in one model, and it is invisible in the numbers it produces.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent / "warehouse"
DB_PATH = PROJECT_DIR / "target" / "warehouse.duckdb"


@dataclass(frozen=True)
class TestReport:
    """The result of one `dbt test` run, reduced to what a gate needs."""

    total: int
    failed: list[str]
    messages: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        # Zero tests is not a pass. A suite that selects nothing is the most
        # common way a data pipeline reports green while checking nothing.
        return self.total > 0 and not self.failed

    def summary(self) -> str:
        if self.total == 0:
            return "no tests ran, so nothing is known about this warehouse"
        if not self.failed:
            return f"{self.total} of {self.total} data tests passed"
        return f"{len(self.failed)} of {self.total} data tests failed: " + ", ".join(self.failed)


def _short_name(unique_id: str) -> str:
    """dbt ids look like test.<package>.<test_name>.<checksum>."""
    parts = unique_id.split(".")
    name = parts[2] if len(parts) > 2 else unique_id
    return name


def parse_run_results(path: Path) -> TestReport:
    """Read dbt's machine-readable run_results.json.

    Raises FileNotFoundError if the file is absent: a missing report means the
    tests did not run, which must never be mistaken for a pass.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    results = payload.get("results", [])
    failed, messages = [], {}
    for row in results:
        if row.get("status") in ("fail", "error"):
            name = _short_name(row.get("unique_id", "unknown"))
            failed.append(name)
            if row.get("message"):
                messages[name] = row["message"]
    return TestReport(total=len(results), failed=sorted(failed), messages=messages)


def dbt(*args: str, scenario: str, check: bool = True) -> subprocess.CompletedProcess:
    """Invoke dbt against the bundled project with the given scenario."""
    env = dict(
        os.environ,
        DBT_PROFILES_DIR=str(PROJECT_DIR),
        DBT_WAREHOUSE_DB=str(DB_PATH),
    )
    cmd = [
        sys.executable, "-m", "dbt.cli.main", *args,
        "--project-dir", str(PROJECT_DIR),
        "--vars", json.dumps({"scenario": scenario}),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if check and proc.returncode != 0:
        raise RuntimeError(f"dbt {' '.join(args)} failed:\n{proc.stdout}\n{proc.stderr}")
    return proc


def build(scenario: str) -> None:
    """Seed and build every model for one scenario."""
    dbt("seed", "--full-refresh", scenario=scenario)
    dbt("run", "--full-refresh", scenario=scenario)


def test(scenario: str) -> TestReport:
    """Run the data tests and return the report (a red suite is not an error)."""
    dbt("test", scenario=scenario, check=False)
    return parse_run_results(PROJECT_DIR / "target" / "run_results.json")
