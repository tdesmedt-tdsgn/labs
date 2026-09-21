#!/usr/bin/env python3
"""One end-to-end pass: build the warehouse twice, ask it the same question.

Round 1 builds the warehouse with one filter missing, runs the data tests,
and asks for 2023 revenue anyway.
Round 2 restores the filter and asks the identical question.

The assistant is byte-for-byte the same in both rounds and its SQL is correct
in both rounds. Only the warehouse changed.

Exits 0 only if the broken warehouse was caught by its tests, the number it
would have served was wrong, and the fixed one passes and answers correctly.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import duckdb

from src.assistant import ask
from src.gate import WarehouseNotTrusted, serve
from src.warehouse import DB_PATH, build, test

QUESTION = "What was our total revenue in 2023?"

# Ground truth, computed from the seed CSVs without touching the warehouse:
# every completed 2023 order, counted exactly once.
def ground_truth() -> float:
    seeds = Path(__file__).resolve().parent / "warehouse" / "seeds" / "orders.csv"
    with seeds.open(encoding="utf-8") as fh:
        return round(sum(
            float(row["amount_eur"])
            for row in csv.DictReader(fh)
            if row["status"] == "completed" and row["order_date"].startswith("2023")
        ), 2)


def rule(title: str) -> None:
    print(f"\n{'=' * 68}\n{title}\n{'=' * 68}")


def main() -> int:
    truth = ground_truth()
    print(f"ground truth, straight from the seed files: EUR {truth:,.2f}")
    print(f"question asked in both rounds: {QUESTION!r}")

    # ---------------------------------------------------------------- round 1
    rule("ROUND 1 - the customer dimension is missing its is_current filter")
    build("broken")
    report = test("broken")
    print(f"dbt test: {report.summary()}")
    for name in report.failed:
        first_line = report.messages.get(name, "").strip().splitlines()[:1]
        print(f"  - {name}: {first_line[0] if first_line else 'failed'}")

    assert not report.ok, "the broken warehouse must not pass its tests"
    assert "assert_revenue_reconciles" in report.failed, report.failed

    # What the gate does.
    try:
        serve(lambda: None, report)
        raise AssertionError("the gate served an answer off a red warehouse")
    except WarehouseNotTrusted as exc:
        print(f"\ngate: {exc}")

    # What happens without a gate: ask anyway.
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        answer = ask(QUESTION, con)
    drift = answer.value - truth
    print("\nwithout the gate, the assistant answers anyway:")
    print(f"  SQL       {answer.sql.splitlines()[0]} ...")
    print(f"  answer    {answer.sentence()}")
    print(f"  truth     EUR {truth:,.2f}")
    print(f"  overstated by EUR {drift:,.2f}  ({drift / truth:.2%})")
    print("  no error, no warning, no null. Just a wrong number with two decimals.")

    assert drift > 0, "expected the fan-out to overstate revenue"
    broken_value, broken_drift = answer.value, drift

    # ---------------------------------------------------------------- round 2
    rule("ROUND 2 - the same models, with the one-line filter restored")
    build("fixed")
    report = test("fixed")
    print(f"dbt test: {report.summary()}")
    assert report.ok, f"the fixed warehouse must pass: {report.failed}"

    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        answer = serve(lambda: ask(QUESTION, con), report)
    print(f"\ngate: green warehouse, answer served")
    print(f"  answer    {answer.sentence()}")
    print(f"  truth     EUR {truth:,.2f}")
    assert abs(answer.value - truth) < 0.01, (answer.value, truth)

    rule("RESULT")
    print(f"broken warehouse answered   EUR {broken_value:,.2f}"
          f"   ({broken_drift / truth:+.2%})")
    print(f"fixed warehouse answered    EUR {answer.value:,.2f}   (exact)")
    print("the assistant, its prompt and its SQL were identical in both rounds")
    print("\ne2e.py: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
