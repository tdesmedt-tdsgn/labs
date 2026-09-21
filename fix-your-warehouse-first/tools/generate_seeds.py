"""Generate the synthetic seed data. Fully invented, fixed RNG seed.

Run it to regenerate the CSVs in warehouse/seeds/ (they are committed, so a
reader never has to):

    python3 tools/generate_seeds.py

The only structural fact that matters: the CRM export carries slowly-changing
customer rows, so a handful of customers appear more than once and exactly one
of their rows has is_current = 1. That is the whole bug surface.
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEEDS = Path(__file__).resolve().parent.parent / "warehouse" / "seeds"
REGIONS = ["north", "south", "east", "west"]
N_CUSTOMERS = 60
N_ORDERS = 520
# Customers whose region changed once (two CRM rows) or twice (three rows).
N_MOVED_ONCE = 8
N_MOVED_TWICE = 1


def main() -> None:
    rng = random.Random(20230417)
    SEEDS.mkdir(parents=True, exist_ok=True)

    ids = list(range(1001, 1001 + N_CUSTOMERS))
    moved = rng.sample(ids, N_MOVED_ONCE + N_MOVED_TWICE)
    history = {cid: (3 if i < N_MOVED_TWICE else 2) for i, cid in enumerate(moved)}

    customers = []
    for cid in ids:
        rows = history.get(cid, 1)
        regions = rng.sample(REGIONS, rows)
        start = date(2021, 1, 1) + timedelta(days=rng.randrange(0, 400))
        for i, region in enumerate(regions):
            customers.append({
                "customer_id": cid,
                "region": region,
                "valid_from": (start + timedelta(days=380 * i)).isoformat(),
                "is_current": 1 if i == rows - 1 else 0,
            })
    customers.sort(key=lambda r: (r["customer_id"], r["valid_from"]))

    statuses = ["completed"] * 17 + ["cancelled", "refunded", "pending"]
    orders = []
    for n in range(N_ORDERS):
        cid = rng.choice(ids)
        day = date(2022, 7, 1) + timedelta(days=rng.randrange(0, 730))
        orders.append({
            "order_id": 500_000 + n,
            "customer_id": cid,
            "order_date": day.isoformat(),
            "amount_eur": f"{rng.lognormvariate(6.6, 0.75):.2f}",
            "status": rng.choice(statuses),
        })
    orders.sort(key=lambda r: r["order_date"])

    _write(SEEDS / "customers.csv", customers)
    _write(SEEDS / "orders.csv", orders)
    print(f"wrote {len(customers)} customer rows for {N_CUSTOMERS} customers")
    print(f"wrote {len(orders)} orders")


def _write(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
